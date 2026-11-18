# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Install RDC's shared files into one project."""

import argparse
import codecs
import hashlib
import os
import re
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from stat import S_IMODE


FRAMEWORK = Path(__file__).resolve().parents[1] / "assets" / "compass"
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml"}
BEGIN = "<!-- COMPASS-PLUGIN:START -->"
END = "<!-- COMPASS-PLUGIN:END -->"
INSTRUCTION = (
    "依頼ごとに、作業を開始する前に必ず [`.compass/README.md`](.compass/README.md) を読み、"
    "案内されたワークフローの README と該当する Skill を参照する。"
)


def append_lines(text: str, block: str, newline: str) -> str:
    if text and not text.endswith(newline):
        text += newline
    if text and not text.endswith(newline * 2):
        text += newline
    return text + block + newline


def has_claude_import(text: str, directive: str) -> bool:
    # Claude skips imports shown in fenced examples and inline code.
    visible = re.sub(r"(?ms)^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?(?:^ {0,3}\1[ \t]*\r?$|\Z)", " ", text)
    visible = re.sub(r"(`+)[\s\S]*?\1", " ", visible)
    spellings = (directive, directive.replace("@./", "@", 1))
    return any(re.search(r"(?<!\S)" + re.escape(item) + r"(?=\s|$)", visible) for item in spellings)


def instruction_bytes(original: bytes, *, claude_import: str = "") -> bytes:
    bom, encoding = b"", "utf-8"
    for marker, codec in (
        (codecs.BOM_UTF8, "utf-8"), (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
    ):
        if original.startswith(marker):
            bom, encoding = marker, codec
            break
    text = original[len(bom):].decode(encoding)
    newline = "\r\n" if "\r\n" in text else "\n"
    block = claude_import or newline.join((BEGIN, INSTRUCTION, END))
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
            raise ValueError("指示ファイル内の既存の Compass マーカーを確認する")
        before, after = text[:text.index(BEGIN)], text[text.index(END) + len(END):]
        if claude_import and has_claude_import(before + newline + after, claude_import):
            block = ""
        text = before + block + after
    elif claude_import:
        if not has_claude_import(text, claude_import):
            text = append_lines(text, block, newline)
    elif INSTRUCTION not in text:
        text = append_lines(text, block, newline)
    return bom + text.encode(encoding)


def project_files(root: Path) -> dict[Path, bytes]:
    destination = root / ".compass"
    files = {}
    for source in sorted(FRAMEWORK.rglob("*")):
        if source.resolve() != source:
            raise ValueError(f"配布元のリンクを確認する。{source}")
        if source.is_dir():
            continue
        relative = source.relative_to(FRAMEWORK)
        name = relative.as_posix()
        if not source.is_file() or "\\" in name or ":" in name:
            raise ValueError(f"配布ファイル名を確認する。{name}")
        if relative.parts[0].casefold() == "records" and name != "records/README.md":
            raise ValueError(f"案件記録が配布物に含まれている。{name}")
        path = destination / relative
        if path.resolve() != path or path in files:
            raise ValueError(f"配布先がリンクまたは重複している。{path}")
        data = source.read_bytes()
        files[path] = data.replace(b"\r\n", b"\n") if source.suffix.lower() in TEXT_SUFFIXES else data
    if destination / "README.md" not in files or destination / "workflow/README.md" not in files:
        raise ValueError("配布物の README を確認する")
    return files


def read_existing(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    temporary = tempfile.NamedTemporaryFile(dir=path.parent, delete=False)
    name = Path(temporary.name)
    try:
        with temporary:
            temporary.write(data)
        name.chmod(mode)
        name.replace(path)
    finally:
        name.unlink(missing_ok=True)


def install(root: Path, update: bool) -> tuple[int, int]:
    files = project_files(root)
    changes: dict[Path, tuple[bytes | None, bytes]] = {}
    conflicts = []
    for path, data in files.items():
        original = read_existing(path)
        if original == data:
            continue
        if original is not None:
            if path.suffix.lower() in TEXT_SUFFIXES and original.replace(b"\r\n", b"\n") == data:
                continue
            if not update:
                conflicts.append(str(path.relative_to(root)))
                continue
        changes[path] = (original, data)
    if conflicts:
        raise ValueError("配布版と内容が異なる。更新する場合は --update を指定する。\n" + "\n".join(conflicts))

    agents = (root / "AGENTS.md").resolve()
    instructions = {agents: ""}
    for name in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
        candidate = root / name
        if candidate.is_file():
            path = candidate.resolve()
            if path != agents:
                instructions[path] = "@../AGENTS.md" if candidate.parent != root else "@./AGENTS.md"
            break
    for path, import_line in instructions.items():
        if not path.is_relative_to(root) or path.is_relative_to(root / ".compass"):
            raise ValueError(f"プロジェクトの指示ファイルのリンク先を確認する。{path}")
        original = read_existing(path)
        data = instruction_bytes(original or b"", claude_import=import_line)
        if data != original:
            changes[path] = (original, data)

    # Check all destinations before writing. Publish instructions after the framework files.
    applied = []
    try:
        for path, (original, data) in changes.items():
            if read_existing(path) != original:
                raise ValueError(f"セットアップ中に変更された。{path}")
            write_atomic(path, data)
            applied.append(path)
    except (OSError, ValueError):
        for path in reversed(applied):
            original, data = changes[path]
            if read_existing(path) == data:
                if original is None:
                    path.unlink()
                else:
                    write_atomic(path, original)
        raise
    return len(files), len(changes)


def main() -> int:
    parser = argparse.ArgumentParser(description="指定プロジェクトにRDCをセットアップする。")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="導入先のプロジェクトルート")
    parser.add_argument("--update", action="store_true", help="同名の共通ファイルを配布版に更新する")
    args = parser.parse_args()
    try:
        root = args.project.resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"プロジェクトのディレクトリを指定する。{root}")
        # Codex and Claude Code may initialize the same project at the same time.
        key = hashlib.sha256(os.fsencode(os.path.normcase(str(root)))).hexdigest()
        lock = Path(tempfile.gettempdir()) / f"rdc-setup-{key}.lock"
        with closing(sqlite3.connect(lock, timeout=30)) as guard:
            guard.execute("BEGIN IMMEDIATE")
            count, changed = install(root, args.update)
        print(f"{root} — 共通ファイル {count} 件、今回の変更 {changed} 件。参照先 .compass/README.md")
    except (OSError, ValueError, sqlite3.Error) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
