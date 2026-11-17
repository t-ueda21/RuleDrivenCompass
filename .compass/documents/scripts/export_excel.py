# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown-it-py==4.0.0", "openpyxl==3.1.5"]
# ///
"""Export each RDC Markdown document as its own Excel workbook."""

import argparse
import re
from collections.abc import Iterator
from dataclasses import dataclass, replace
from math import ceil
from pathlib import Path
from tempfile import NamedTemporaryFile
from unicodedata import east_asian_width

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from openpyxl import Workbook
from openpyxl.cell.cell import Cell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import IllegalCharacterError
from openpyxl.worksheet.worksheet import Worksheet


DOCUMENTS_DIR = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = DOCUMENTS_DIR.parent / "workflow"
MARKDOWN = MarkdownIt("commonmark").enable("table")
INVALID_SHEET_CHARACTERS = re.compile(r"[\[\]:*?/\\\x00-\x1f]")
INVALID_FILE_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_DEVICE_NAME = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])", re.IGNORECASE)
SECTION_LABEL = re.compile(r"\s*（(?:必須|本番必須|試作必須|補足|該当時)）$")
LINE_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
TITLE_SHEET = "タイトル"
REVISION_SHEET = "変更履歴"
BODY_TEXT = "192532"
TABLE_LINE = Side(style="thin", color="ADBACA")
HEADER_LINE = Side(style="thin", color="DDE7F0")
HEADER_BORDER = Border(right=HEADER_LINE, bottom=TABLE_LINE)
DATA_BORDER = Border(bottom=TABLE_LINE)
INPUT_BORDER = Border(right=TABLE_LINE, bottom=TABLE_LINE)


@dataclass(frozen=True)
class TextBlock:
    text: str
    kind: str = "text"


@dataclass(frozen=True)
class TableBlock:
    rows: list[list[str]]


def read_markdown(path: Path) -> SyntaxTreeNode:
    return SyntaxTreeNode(MARKDOWN.parse(path.read_text(encoding="utf-8-sig")))


def template_sources() -> list[Path]:
    """Follow the template links in the phase index in workflow order."""
    phase_dir = WORKFLOW_DIR / "phase"
    index = read_markdown(phase_dir / "README.md")
    sources = []
    for node in index.walk():
        if node.type != "link":
            continue
        target = node.attrGet("href")
        if isinstance(target, str) and target.endswith("/references/template.md"):
            source = (phase_dir / target).resolve()
            if source.parent.name != "references" or source.parent.parent.parent != phase_dir:
                raise ValueError(f"工程フォルダ外のテンプレートを参照している。{target}")
            sources.append(source)
    if not sources:
        raise ValueError("工程のREADMEにテンプレートへのリンクがない。")
    return sources + [WORKFLOW_DIR / "issue-tracking" / "references" / "template.md"]


def inline_text(node: SyntaxTreeNode) -> str:
    if node.type == "softbreak":
        return " "
    if node.type == "hardbreak":
        return "\n"
    text = "".join(map(inline_text, node.children)) if node.children else node.content
    if node.type == "html_inline":
        if text.startswith("<!--"):
            return ""
        if LINE_BREAK.fullmatch(text):
            return "\n"
    if node.type in {"link", "image"}:
        target = node.attrGet("href" if node.type == "link" else "src")
        if target and target != text:
            return f"{text} ({target})" if text else str(target)
    return text


def document_blocks(
    root: SyntaxTreeNode, depth: int = 0
) -> Iterator[TextBlock | TableBlock]:
    for node in root.children:
        if node.type in {"heading", "paragraph"}:
            yield TextBlock(inline_text(node), node.tag if node.type == "heading" else "text")
        elif node.type == "table":
            rows = [
                [inline_text(cell) for cell in row.children]
                for group in node.children
                for row in group.children
            ]
            yield TableBlock(rows)
        elif node.type in {"bullet_list", "ordered_list"}:
            start = int(node.attrGet("start") or 1)
            for number, item in enumerate(node.children, start):
                blocks = list(document_blocks(item, depth + 1))
                if blocks and isinstance(blocks[0], TextBlock):
                    marker = f"{number}. " if node.type == "ordered_list" else "• "
                    blocks[0] = replace(blocks[0], text=f"{'  ' * depth}{marker}{blocks[0].text}")
                yield from blocks
        elif node.type == "blockquote":
            for block in document_blocks(node, depth):
                yield replace(block, kind="note") if isinstance(block, TextBlock) else block
        elif node.type in {"fence", "code_block"}:
            if node.info.strip():
                yield TextBlock(node.info.strip(), "note")
            for line in node.content.splitlines():
                yield TextBlock(line, "code")
        elif node.type == "html_block" and not node.content.lstrip().startswith("<!--"):
            yield TextBlock(node.content.rstrip())


def workbook_layouts() -> dict[str, dict[str, list[str]]]:
    layouts = {}
    title = ""
    source = DOCUMENTS_DIR / "excel-sheets.md"
    for block in document_blocks(read_markdown(source)):
        if isinstance(block, TextBlock) and block.kind == "h2":
            title = block.text
        if not isinstance(block, TableBlock):
            continue
        if not title or title in layouts or block.rows[0] != ["シート", "対応する章"]:
            raise ValueError(f"Excelのシート構成の表を確認する。{title}")
        groups = {}
        assigned = set()
        for name, chapter_list in block.rows[1:]:
            chapters = [chapter.strip() for chapter in chapter_list.splitlines() if chapter.strip()]
            if (not name or name in groups or name in {TITLE_SHEET, REVISION_SHEET}
                    or not chapters or len(chapters) != len(set(chapters))
                    or assigned.intersection(chapters)):
                raise ValueError(f"Excelのシート構成に重複または空欄がある。{title}／{name}")
            groups[name] = chapters
            assigned.update(chapters)
        layouts[title] = groups
    return layouts


def unique_name(base: str, taken: set[str], limit: int) -> str:
    name = base[:limit].rstrip(" .'")
    number = 2
    while name.casefold() in taken:
        suffix = f" ({number})"
        name = base[:limit - len(suffix)].rstrip(" .'") + suffix
        number += 1
    return name


def unique_sheet_name(workbook: Workbook, title: str) -> str:
    base = INVALID_SHEET_CHARACTERS.sub(" ", title).strip(" .'") or "文書"
    if base.casefold() == "history":
        base = "History_"
    return unique_name(base, {name.casefold() for name in workbook.sheetnames}, 31)


def output_filename(title: str, taken: set[str]) -> str:
    base = INVALID_FILE_CHARACTERS.sub(" ", title).strip(" .'") or "文書"
    if WINDOWS_DEVICE_NAME.fullmatch(base.split(".", 1)[0].rstrip()):
        base = f"文書 {base}"
    stem = unique_name(base, taken, 100)
    taken.add(stem.casefold())
    return f"{stem}.xlsx"


def character_width(text: str) -> int:
    return sum(2 if east_asian_width(char) in {"W", "F"} else 1 for char in text)


def cell_text_width(text: str) -> int:
    return max(map(character_width, text.split("\n")))


def table_widths(tables: list[TableBlock]) -> list[int]:
    if not tables:
        return [92]
    columns = max(len(table.rows[0]) for table in tables)
    widths = [14] * columns
    for table in tables:
        for values in table.rows:
            for index, value in enumerate(values):
                widths[index] = max(widths[index], min(44, cell_text_width(value) + 4))
    return widths


def write_cell(cell: Cell, value: str) -> None:
    if len(value) > 32767:
        raise ValueError("Excelの1セルに記録できる文字数を超えている。")
    if value:
        cell.value = value
        cell.data_type = "s"
    cell.alignment = Alignment(vertical="top", wrap_text=True)


def line_count(text: str, width: int) -> int:
    available_width = max(1, width - 3)
    return sum(max(1, ceil(character_width(line) / available_width)) for line in text.split("\n"))


def write_text(sheet: Worksheet, row: int, block: TextBlock, widths: list[int]) -> None:
    if len(widths) > 1:
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(widths))
    cell = sheet.cell(row, 1)
    write_cell(cell, block.text)
    size = 16 if block.kind == "title" else 11
    color = BODY_TEXT
    fill = None
    bold = False
    supplemental = block.text.endswith(("（補足）", "（該当時）"))
    if block.kind == "title":
        color, bold = "FFFFFF", True
        fill = "364554" if supplemental else "18324D"
    elif block.kind.startswith("h"):
        fill = "EEF1F4" if supplemental else "D3E4F6"
        bold = True
    elif block.kind == "note":
        fill = "EEF3F8"
    elif block.kind == "code":
        fill = "F2F4F7"
    cell.font = Font(name="Yu Gothic", size=size, color=color, bold=bold)
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    lines = line_count(block.text, sum(widths) * 11 // size)
    sheet.row_dimensions[row].height = min(408, (size + 6) * lines + 6)


def write_table(sheet: Worksheet, row: int, block: TableBlock, widths: list[int]) -> int:
    rows = block.rows
    if len(rows) == 1:
        rows = [*rows, [""] * len(rows[0])]
    record_form = rows[0] == ["記録項目", "内容"]
    header_font = Font(name="Yu Gothic", size=11, color="FFFFFF", bold=True)
    label_font = Font(name="Yu Gothic", size=11, color=BODY_TEXT, bold=True)
    value_font = Font(name="Yu Gothic", size=11, color=BODY_TEXT)
    header_fill = PatternFill("solid", fgColor="304B63")
    label_fill = PatternFill("solid", fgColor="E7EDF5")
    input_fill = PatternFill("solid", fgColor="FFF1C9")
    white_fill = PatternFill("solid", fgColor="FFFFFF")
    stripe_fill = PatternFill("solid", fgColor="F4F6F9")
    for offset, values in enumerate(rows):
        header = offset == 0
        for column, value in enumerate(values, 1):
            cell = sheet.cell(row + offset, column)
            write_cell(cell, value)
            if header:
                cell.font = header_font
                cell.fill = header_fill
                cell.border = HEADER_BORDER
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            elif record_form and column == 1 and value:
                cell.font = label_font
                cell.fill = label_fill
                cell.border = DATA_BORDER
            else:
                cell.font = value_font
                if value:
                    cell.fill = stripe_fill if offset % 2 == 0 else white_fill
                    cell.border = DATA_BORDER
                else:
                    cell.fill = input_fill
                    cell.border = INPUT_BORDER
        lines = max(line_count(value, width) for value, width in zip(values, widths))
        sheet.row_dimensions[row + offset].height = min(408, 16 * lines + 8)
    return row + len(rows)


def add_sheet(
    workbook: Workbook, name: str, title: str, blocks: list[TextBlock | TableBlock]
) -> None:
    sheet = workbook.create_sheet(unique_sheet_name(workbook, name))
    tables = [block for block in blocks if isinstance(block, TableBlock)]
    widths = table_widths(tables)
    if len(tables) == 1 and tables[0].rows[0] == ["記録項目", "内容"]:
        widths[1] = max(widths[1], 48)
    for column, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(column)].width = width
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"
    write_text(sheet, 1, TextBlock(title, "title"), widths)

    row = 3
    for block in blocks:
        if isinstance(block, TableBlock):
            next_row = write_table(sheet, row, block, widths)
            if len(tables) == 1 and name != TITLE_SHEET:
                end_column = get_column_letter(len(block.rows[0]))
                sheet.auto_filter.ref = f"A{row}:{end_column}{next_row - 1}"
                if row <= 6:
                    issue_columns = ["課題 ID", "発生フェーズ", "状態"]
                    first_scroll_column = "D" if block.rows[0][:3] == issue_columns else "A"
                    sheet.freeze_panes = f"{first_scroll_column}{row + 1}"
            row = next_row + 1
        else:
            write_text(sheet, row, block, widths)
            row += 1


def add_content_sheets(
    workbook: Workbook,
    body: list[tuple[str, list[TextBlock | TableBlock]]],
    layout: dict[str, list[str]],
) -> None:
    chapter_to_group = {chapter: name for name, chapters in layout.items() for chapter in chapters}
    groups = {name: [] for name in layout}
    other_sections = []
    for heading, content in body:
        group = chapter_to_group.get(SECTION_LABEL.sub("", heading))
        if group is None:
            other_sections.append((heading, content))
        else:
            groups[group].append((heading, content))

    for name, sections in groups.items():
        if not sections:
            continue
        if len(sections) == 1 and SECTION_LABEL.sub("", sections[0][0]) == name:
            heading, content = sections[0]
            add_sheet(workbook, name, heading, content)
            continue
        blocks = []
        for heading, content in sections:
            blocks.extend([TextBlock(heading, "h2"), *content])
        add_sheet(workbook, name, name, blocks)
    for heading, content in other_sections:
        add_sheet(workbook, SECTION_LABEL.sub("", heading), heading, content)


def build_workbook(source: Path, layouts: dict[str, dict[str, list[str]]]) -> tuple[str, Workbook]:
    blocks = list(document_blocks(read_markdown(source)))
    if not blocks:
        raise ValueError("出力できる文書の内容がない。")
    title = source.stem
    if isinstance(blocks[0], TextBlock) and blocks[0].kind == "h1":
        title = blocks.pop(0).text or title

    intro: list[TextBlock | TableBlock] = []
    sections: list[tuple[str, list[TextBlock | TableBlock]]] = []
    current = intro
    for block in blocks:
        if isinstance(block, TextBlock) and block.kind == "h2":
            current = []
            sections.append((block.text, current))
        else:
            current.append(block)

    cover: list[TextBlock | TableBlock] = []
    revisions: list[TextBlock | TableBlock] = []
    revision_title = REVISION_SHEET
    body: list[tuple[str, list[TextBlock | TableBlock]]] = []
    if intro:
        if all(isinstance(block, TextBlock) and block.kind == "note" for block in intro):
            cover.extend(intro)
        else:
            body.append(("課題一覧" if title == "課題管理表" else "本文", intro))

    for heading, content in sections:
        name = SECTION_LABEL.sub("", heading).strip()
        if name in {"文書管理", "文書情報"}:
            cover.extend([TextBlock(heading, "h2"), *content])
        elif name in {REVISION_SHEET, "改訂履歴", "変更・レビュー履歴"}:
            if heading.endswith("（補足）"):
                revision_title = f"{REVISION_SHEET}（補足）"
            revisions.extend(content)
        else:
            body.append((heading, content))

    if not cover:
        cover.append(TableBlock([["記録項目", "内容"], ["文書版または更新日", ""]]))
    if not revisions:
        revisions.append(TableBlock([["版・日付", "変更理由・対象項目", "確認内容・結果", "参照先"]]))

    workbook = Workbook()
    workbook.remove(workbook.active)
    add_sheet(workbook, TITLE_SHEET, title, cover)
    add_sheet(workbook, REVISION_SHEET, revision_title, revisions)
    add_content_sheets(workbook, body, layouts.get(title, {}))
    return title, workbook


def save_workbook(workbook: Workbook, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=output.parent, suffix=".xlsx", delete=False) as file:
        temporary = Path(file.name)
    try:
        workbook.save(temporary)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="RDCのMarkdown文書を１文書１ブックでExcelに出力する。")
    parser.add_argument("documents", nargs="*", type=Path, metavar="MARKDOWN")
    parser.add_argument("--templates", action="store_true", help="工程と課題管理のテンプレートを出力する")
    parser.add_argument(
        "-o", "--output", required=True, type=Path, metavar="OUTPUT",
        help="出力フォルダ、または単一文書の出力先 .xlsx",
    )
    args = parser.parse_intermixed_args()
    if not args.templates and not args.documents:
        parser.error("Markdownファイルまたは --templates を指定する。")
    output = args.output.expanduser()
    single_file = output.suffix.casefold() == ".xlsx"

    try:
        sources = template_sources() if args.templates else []
        sources += args.documents
        input_paths = dict.fromkeys(path.expanduser().resolve() for path in sources)
        if single_file and len(input_paths) != 1:
            parser.error("複数の文書を出力する場合は出力フォルダを指定する。")
        layouts = workbook_layouts()
        names: set[str] = set()
        exports = []
        for source in input_paths:
            if source.suffix.casefold() not in {".md", ".markdown"}:
                parser.error(f"Markdownファイルを指定する。{source}")
            try:
                title, workbook = build_workbook(source, layouts)
            except (OSError, ValueError, IllegalCharacterError) as error:
                parser.error(f"{source} — {error}")
            destination = output if single_file else output / output_filename(title, names)
            exports.append((destination, workbook))
        for destination, workbook in exports:
            save_workbook(workbook, destination)
            print(f"{destination.resolve()} に{len(workbook.worksheets)}シートを出力")
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
