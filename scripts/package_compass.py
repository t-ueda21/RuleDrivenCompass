# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Build the project template and the installable Codex / Claude Code marketplace."""

import argparse
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "compass"
PAYLOAD = PLUGIN / "skills" / "compass-setup" / "assets" / "compass"
CATALOGS = (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json")


def source_files(directory: Path) -> list[Path]:
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--",
         directory.relative_to(ROOT).as_posix()],
        cwd=ROOT,
    )
    return sorted({ROOT / os.fsdecode(name) for name in paths.split(b"\0") if name})


def file_bytes(path: Path) -> bytes:
    if path.resolve() != path:
        raise ValueError(f"配布元のリンクを確認する。{path}")
    data = path.read_bytes()
    if path.suffix.lower() in {".md", ".py", ".json", ".yaml", ".yml"}:
        return data.replace(b"\r\n", b"\n")
    return data


def framework() -> dict[str, bytes]:
    source = ROOT / ".compass"
    files = {}
    for path in source_files(source):
        name = path.relative_to(source).as_posix()
        if name.startswith("records/") and name != "records/README.md":
            continue
        if path.is_file():
            files[name] = file_bytes(path)
    if "README.md" not in files or "workflow/README.md" not in files:
        raise ValueError("配布元の .compass を確認する")
    return files


def write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = NamedTemporaryFile(dir=path.parent, delete=False)
    temporary = Path(output.name)
    try:
        with output:
            output.write(data)
        temporary.chmod(0o644)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def sync_payload(files: dict[str, bytes], *, check: bool) -> None:
    if PAYLOAD.resolve() != PAYLOAD:
        raise ValueError(f"配布先のリンクを確認する。{PAYLOAD}")
    bundled = {}
    for path in PAYLOAD.rglob("*"):
        if path.resolve() != path:
            raise ValueError(f"配布先のリンクを確認する。{path}")
        if path.is_file():
            bundled[path.relative_to(PAYLOAD).as_posix()] = file_bytes(path)
    differences = sorted(name for name in files.keys() | bundled.keys() if files.get(name) != bundled.get(name))
    if not differences:
        return
    if check:
        raise ValueError("配布元と同梱ファイルに差分がある。\n" + "\n".join(differences))
    for name in bundled.keys() - files.keys():
        (PAYLOAD / name).unlink()
    # A new file may take the place of a directory from the previous release.
    directories = sorted((p for p in PAYLOAD.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True)
    for directory in directories:
        if not any(directory.iterdir()):
            directory.rmdir()
    for name in differences:
        if name in files:
            write_file(PAYLOAD / name, files[name])


def write_zip(path: Path, files: dict[str, bytes]) -> None:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in sorted(files.items()):
            entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content, compress_type=ZIP_DEFLATED)
    write_file(path, buffer.getvalue())


def check_zip(path: Path, files: dict[str, bytes]) -> None:
    with ZipFile(path) as archive:
        if sorted(archive.namelist()) != sorted(files):
            raise ValueError(f"配布物のファイル一覧が一致しない。{path}")
        for name, expected in files.items():
            if archive.read(name) != expected:
                raise ValueError(f"配布物を再作成する。{name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="配布元と同梱ファイルの一致を確認する")
    parser.add_argument("--dist", action="store_true", help="配布可能なマーケットプレイス ZIP を dist/ に作成する")
    args = parser.parse_args()
    try:
        files = framework()
        if not args.check:
            sync_payload(files, check=False)
        sync_payload(files, check=True)
        print(f"RDC 共通ファイル {len(files)} 件を照合")

        if args.dist:
            manifest = json.loads((PLUGIN / "plugin.json").read_bytes())
            version = manifest["version"]
            claude = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_bytes())
            if (manifest["name"], version) != (claude["name"], claude["version"]):
                raise ValueError("Codex と Claude Code のプラグイン名・版が一致しない")
            paths = {ROOT / name for name in (*CATALOGS, "README.md")}
            paths.update(path for path in source_files(PLUGIN) if path.is_file() and not path.is_relative_to(PAYLOAD))
            package = {path.relative_to(ROOT).as_posix(): file_bytes(path) for path in paths}
            package.update({(PAYLOAD / name).relative_to(ROOT).as_posix(): data for name, data in files.items()})
            dist = ROOT / "dist" / f"rule-driven-compass-{version}.zip"
            if not args.check:
                write_zip(dist, package)
            check_zip(dist, package)
            print(dist)
    except (OSError, ValueError, BadZipFile, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
