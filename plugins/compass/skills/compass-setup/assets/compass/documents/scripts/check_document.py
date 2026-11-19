# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown-it-py==4.0.0"]
# ///
"""Check the recorded fields of a completed RDC Markdown phase document."""

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode


PHASE_DIR = Path(__file__).resolve().parents[2] / "workflow" / "phase"
MARKDOWN = MarkdownIt("commonmark").enable("table")
MODE_LABELS = {"本番必須": "production", "試作必須": "poc"}
SECTION_LABEL = re.compile(r"（(必須|本番必須|試作必須|補足)）$")
STATUS_LABELS = (
    "該当なし", "対象外", "未確認", "未確定", "未実施", "判定不能", "要確認", "確認待ち",
    "保留", "未検証", "未判定", "実施不能",
)
TEST_OUTCOMES = ("合格", "不合格", "判定不能", "実施不能")
STATUS = re.compile(r"(" + "|".join(STATUS_LABELS) + r")[（(](.*)[）)]", re.DOTALL)
REQUIREMENT_SECTION = "要件との対応（必須）"
CONTRACT_SECTION = "要素間の契約（補足）"
CONTRACT_COLUMN = "契約 ID・項目名（該当時）"
SCREEN_REVIEW = "画面試作とフィードバック（補足）"
PLACEHOLDERS = {
    "", "-", "—", "―", "…", "...", "tbd", "n/a", "todo",
    "記入", "［記入］", "仮記入", "未記入", "未定", "理由", "理由を記載",
}


@dataclass
class DocumentInspection:
    sections: dict[str, list[SyntaxTreeNode]]
    section_count: int
    messages: list[str]
    blocking: list[str]


def node_text(node: SyntaxTreeNode) -> str:
    if node.type == "inline" or not node.children:
        return node.content.strip()
    return " ".join(map(node_text, node.children)).strip()


def read_sections(path: Path) -> dict[str, list[SyntaxTreeNode]]:
    tree = SyntaxTreeNode(MARKDOWN.parse(path.read_text(encoding="utf-8-sig")))
    sections: dict[str, list[SyntaxTreeNode]] = {}
    current = None
    for node in tree.children:
        if node.type == "heading" and node.tag == "h2":
            title = node_text(node)
            if title in sections:
                raise ValueError(f"見出しが重複している。{title}")
            current = sections.setdefault(title, [])
        elif current is not None:
            current.append(node)
    return sections


def table_rows(table: SyntaxTreeNode) -> list[list[str]]:
    return [
        [node_text(cell) for cell in row.children]
        for group in table.children
        for row in group.children
    ]


def section_rows(sections: dict[str, list[SyntaxTreeNode]], title: str) -> list[dict[str, str]]:
    for node in sections.get(title, []):
        if node.type == "table":
            headers, *rows = table_rows(node)
            return [dict(zip(headers, row)) for row in rows if any(row)]
    return []


def item_id(value: str) -> str:
    return re.split(r"[\s:：]+", value.replace("`", "").strip(), maxsplit=1)[0]


def digest(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def recorded_status(value: str) -> str | None:
    match = STATUS.fullmatch(value.strip().rstrip("。"))
    if match and match[2].strip().casefold() not in PLACEHOLDERS:
        return match[1]
    return None


def cell_error(value: str, required: bool) -> str | None:
    value = value.strip("`").strip()
    if value.casefold() in PLACEHOLDERS:
        return "空欄または仮記入"
    status = recorded_status(value)
    if status and required:
        return f"必須欄の具体的な内容が未確定（{status}）"
    is_status_field = any(
        value == label or value.startswith((f"{label}（", f"{label}("))
        for label in STATUS_LABELS
    )
    if not status and is_status_field:
        return "状態に理由を記録する"
    return None


def recorded_rows(
    rows: list[list[str]], fixed_labels: set[str]
) -> list[list[str]]:
    return [
        row for row in rows
        if any(row[1:]) or (row[0] and row[0] not in fixed_labels)
    ]


def check_table(
    template: list[list[str]],
    rows: list[list[str]],
    required: bool,
    *,
    required_only: bool = False,
) -> list[str]:
    headers = template[0]
    fixed_labels = [row[0] for row in template[1:] if row[0]]
    if not rows or rows[0] != headers:
        return ["テンプレートの列見出しを使う"]

    data = rows[1:]
    reason_column = headers.index("理由") if "理由" in headers else None
    errors = []
    if fixed_labels:
        labels = [row[0] for row in data if any(row)]
        errors.extend(
            f"記録項目がない。{label}" for label in fixed_labels
            if label not in labels and not (required_only and label.endswith("（該当時）"))
        )
        if len(labels) != len(set(labels)):
            errors.append("記録項目の行が重複している")
    if not any(any(row) for row in data):
        return [*errors, "記録行が空欄"]

    for number, row in enumerate(data, 1):
        if not any(row):
            continue
        label = row[0] or f"記録行 {number}"
        for index, (header, value) in enumerate(zip(headers, row)):
            if index == 0 and label in fixed_labels:
                continue
            conditional = header.endswith("（該当時）")
            if fixed_labels and index > 0:
                conditional = conditional or label.endswith("（該当時）")
            if required_only and conditional:
                continue
            verdict_column = (headers[0] == "実行 ID" and header == "判定") or (
                "初回判定" in headers and header in {"初回判定", "最終判定"}
            )
            if verdict_column and value in TEST_OUTCOMES:
                continue
            # The review-specific check reports pending decisions with the affected screen.
            if header == "判断" and "試作の版・参照先" in headers and value in {"確認待ち", "再確認待ち", "保留"}:
                continue
            if header == "状況" and value in STATUS_LABELS and reason_column is not None:
                value = f"{value}（{row[reason_column]}）"
            error = cell_error(value, required and not conditional)
            if error:
                errors.append(f"{label}／{header} — {error}")
    return errors


def check_section(
    expected: list[list[str]],
    nodes: list[SyntaxTreeNode],
    label: str,
    mode: str | None,
    *,
    required_only: bool = False,
) -> list[str]:
    tables = [table_rows(node) for node in nodes if node.type == "table"]
    fixed = {row[0] for row in expected[1:] if row[0]}
    has_data = any(recorded_rows(table[1:], fixed) for table in tables)
    statuses = [
        status for node in nodes
        if node.type in {"paragraph", "blockquote"}
        if (status := recorded_status(node_text(node)))
    ]

    required_mode = MODE_LABELS.get(label)
    if required_mode and required_mode != mode:
        if "対象外" in statuses and not has_data:
            return []
        return ["対象外の開発区分。見出しを残し、対象外（理由）を記録する"]

    required = label != "補足"
    if statuses and has_data:
        return ["章の適用結果と記入済みの行を確認する。適用結果が行ごとに異なる場合は各欄に記録する"]
    if statuses and not has_data:
        if required:
            return ["必須項目の具体的な内容を記録する"]
        return []
    if not has_data or len(tables) != 1:
        return ["記録欄を記入する" if required else "記録欄または適用結果と理由を記入する"]
    return check_table(expected, tables[0], required, required_only=required_only)


def check_basic_design_contracts(sections: dict[str, list[SyntaxTreeNode]]) -> list[str]:
    requirements = next(
        (table_rows(node) for node in sections.get(REQUIREMENT_SECTION, []) if node.type == "table"),
        [],
    )
    if not requirements or CONTRACT_COLUMN not in requirements[0]:
        return []

    errors = []
    referenced = set()
    column = requirements[0].index(CONTRACT_COLUMN)
    for row in requirements[1:]:
        value = row[column]
        status = recorded_status(value)
        if status in {"該当なし", "対象外"}:
            continue
        if status:
            errors.append(f"{REQUIREMENT_SECTION} — {row[0]} の契約の適用が未確定")
        elif not cell_error(value, required=True):
            referenced.add(value.strip("`").strip())

    contracts = next(
        (table_rows(node) for node in sections.get(CONTRACT_SECTION, []) if node.type == "table"),
        [],
    )
    recorded = set()
    if contracts and "確定状況" in contracts[0]:
        for row in contracts[1:]:
            if not any(row):
                continue
            key = row[0].strip("`").strip()
            recorded.add(key)
            for header, value in zip(contracts[0], row):
                if header == "確定状況":
                    error = None if value.strip("`") == "確定" else "契約を確定してから完了を判断する"
                else:
                    error = cell_error(value, required=True)
                if error:
                    errors.append(f"{CONTRACT_SECTION} — {key}／{header} — {error}")
    for key in sorted(referenced - recorded):
        errors.append(f"{CONTRACT_SECTION} — 要件との対応にある契約 {key} の記録がない")
    return errors


def document_templates() -> dict[str, Path]:
    return {
        path.parent.parent.name: path for path in PHASE_DIR.glob("*/references/template.md")
    }


def check_screen_review(
    expected: list[list[str]], sections: dict[str, list[SyntaxTreeNode]], mode: str | None
) -> list[str]:
    sources = section_rows(sections, "要求の情報源（必須）")
    declared = any(item_id(row.get("要求元・資料", "")) == "画面試作" for row in sources)
    if SCREEN_REVIEW not in sections:
        # Existing requirements documents without a screen prototype keep their original format.
        return ["要求の情報源にある画面試作のレビュー記録がない"] if declared else []

    nodes = sections[SCREEN_REVIEW]
    reviews = section_rows(sections, SCREEN_REVIEW)
    excluded = any(
        recorded_status(node_text(node)) in {"該当なし", "対象外"}
        for node in nodes if node.type in {"paragraph", "blockquote"}
    )
    if excluded and not reviews:
        return ["要求の情報源の画面試作を対象外にできない"] if declared else []

    errors = [
        f"{row.get('画面・操作', '')} — 利用者確認と採否が未確定（{row['判断']}）"
        for row in reviews if "判断" in row and row["判断"] not in {"採用", "変更なし", "見送り"}
    ]
    structure_errors = check_section(expected, nodes, "必須", mode, required_only=True)
    if structure_errors:
        return errors + structure_errors
    if not declared:
        errors.append("提示した版を「要求の情報源」に「画面試作」として記録する")
    requirements = {item_id(row.get("要件 ID・項目名", "")) for row in section_rows(sections, "要件一覧（必須）")}
    condition_section, target = "受け入れ条件（本番必須）", "要件 ID・項目名"
    if mode == "poc":
        condition_section, target = "仮説と成功条件（試作必須）", "要件・確認対象"
    condition_pairs = {
        (item_id(row.get(target, "")), item_id(row.get("条件 ID・項目名", "")))
        for row in section_rows(sections, condition_section)
    }
    for row in reviews:
        if row["判断"] == "採用":
            requirement = item_id(row["要件 ID・項目名（該当時）"])
            condition = item_id(row["条件 ID・項目名（該当時）"])
            if requirement not in requirements or (requirement, condition) not in condition_pairs:
                errors.append(f"{row['画面・操作']} — 採用した要件 {requirement} と判定条件 {condition} の対応を確認する")
    return errors


def inspect_document(phase: str, document: Path, mode: str | None) -> DocumentInspection:
    expected = read_sections(PHASE_DIR / phase / "references" / "template.md")
    actual = read_sections(document)
    if not expected:
        raise ValueError("テンプレートの工程見出しがない")
    messages = []
    blocking = []
    for title, nodes in expected.items():
        label = SECTION_LABEL.search(title)
        tables = [node for node in nodes if node.type == "table"]
        if label is None or len(tables) != 1:
            raise ValueError(f"テンプレートの記録区分または表を確認する。{title}")
        if phase == "requirements-definition" and title == SCREEN_REVIEW:
            errors = check_screen_review(table_rows(tables[0]), actual, mode)
            messages.extend(f"{title} — {error}" for error in errors)
            blocking.extend(f"{title} — {error}" for error in errors)
            continue
        category = label[1]
        expected_mode = MODE_LABELS.get(category)
        if expected_mode and mode is None:
            raise ValueError("本番・試作の切り替えがある工程には --mode を指定する")
        required = category != "補足" and (expected_mode is None or mode == expected_mode)
        if title not in actual:
            message = f"{title} — 見出しと記録がない"
            messages.append(message)
            if required:
                blocking.append(message)
            continue
        rows = table_rows(tables[0])
        errors = check_section(rows, actual[title], category, mode)
        messages.extend(f"{title} — {error}" for error in errors)
        if required:
            blocking.extend(
                f"{title} — {error}"
                for error in check_section(rows, actual[title], category, mode, required_only=True)
            )
    if phase == "basic-design":
        errors = check_basic_design_contracts(actual)
        messages.extend(errors)
        blocking.extend(errors)
    return DocumentInspection(actual, len(expected), messages, blocking)


def main() -> int:
    parser = argparse.ArgumentParser(description="RDCの標準テンプレートで作成した工程文書の記入状況を確認する。")
    parser.add_argument("phase", choices=sorted(document_templates()))
    parser.add_argument("document", type=Path)
    parser.add_argument("--mode", choices=("production", "poc"))
    args = parser.parse_args()
    try:
        inspection = inspect_document(args.phase, args.document, args.mode)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if inspection.messages:
        print(f"{args.document} — 記入状況の要確認 {len(inspection.messages)} 件", file=sys.stderr)
        for message in inspection.messages:
            print(f"- {message}", file=sys.stderr)
        return 1
    print(f"{args.document} — 必須欄と補足欄の記入を確認（{inspection.section_count}項目）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
