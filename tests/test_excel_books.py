"""Exercise the published Excel exporter from an initialized consumer project."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "plugins/compass/skills/compass-setup/scripts/setup.py"


def workbook_contents(path):
    with ZipFile(path) as workbook:
        sheets = ElementTree.fromstring(workbook.read("xl/workbook.xml")).findall(".//{*}sheet")
        text = " ".join(
            "".join(ElementTree.fromstring(workbook.read(name)).itertext())
            for name in workbook.namelist()
            if name.startswith("xl/worksheets/") and name.endswith(".xml")
        )
    return [sheet.get("name") for sheet in sheets], text


class ExcelBooksTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "利用先 project"
        self.root.mkdir()
        self.env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        subprocess.run([sys.executable, str(SETUP), "--project", str(self.root)],
                       env=self.env, capture_output=True, check=True)
        self.exporter = self.root / ".compass/documents/scripts/export_excel.py"
        self.books = self.root / "books"
        self.docs = self.root / "deliverables"
        self.docs.mkdir()
        self.report = self.docs / "integration.md"
        self.report.write_text("# 結合試験書\n\nIT-01 実測値1234\n", encoding="utf-8")

    def export(self, *args, cwd=None, expected=0):
        result = subprocess.run(
            ["uv", "run", str(self.exporter), *map(str, args)], cwd=cwd or self.root,
            env=self.env, capture_output=True, encoding="utf-8", timeout=60,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_first_export_creates_books_and_reexport_updates_the_same_workbook(self):
        self.assertFalse(self.books.exists())
        self.export(self.report)
        output = self.books / "結合試験書.xlsx"
        sheets, text = workbook_contents(output)
        self.assertEqual(sheets[:2], ["タイトル", "変更履歴"])
        self.assertIn("実測値1234", text)
        self.report.write_text("# 結合試験書\n\n再試験の実測値5678\n", encoding="utf-8")
        self.export(self.report)
        self.assertIn("実測値5678", workbook_contents(output)[1])
        self.assertEqual(list(self.books.iterdir()), [output])

    def test_subdirectory_invocation_uses_project_books(self):
        self.export(self.report.name, cwd=self.docs)
        self.assertTrue((self.books / "結合試験書.xlsx").is_file())
        self.assertFalse((self.docs / "books").exists())

    def test_screen_feedback_stays_in_the_requirements_workbook(self):
        document = self.docs / "requirements.md"
        feedback = (
            "## 画面試作とフィードバック（補足）\n\n"
            "| 画面 | 課題 ID | 要件 | 判定条件 |\n|---|---|---|---|\n"
            "| 予約 v2 | Q-017 | REQ-12 | AC-04 |\n"
        )
        for title in ("要件定義書", "備品受取予約　要件定義書"):
            with self.subTest(title=title):
                document.write_text(f"# {title}\n\n{feedback}", encoding="utf-8")
                self.export(document)
                book = self.books / f"{title}.xlsx"
                sheets, _ = workbook_contents(book)
                self.assertEqual(sheets[:2], ["タイトル", "変更履歴"])
                self.assertIn("画面レビュー", sheets)
                with ZipFile(book) as workbook:
                    page = workbook.read(f"xl/worksheets/sheet{sheets.index('画面レビュー') + 1}.xml")
                    text = "".join(ElementTree.fromstring(page).itertext())
                for value in ("予約 v2", "Q-017", "REQ-12", "AC-04"):
                    self.assertIn(value, text)

    def test_installed_exporter_from_outside_uses_its_own_project_books(self):
        self.export(self.report, cwd=self.root.parent)
        self.assertTrue((self.books / "結合試験書.xlsx").is_file())
        self.assertFalse((self.root.parent / "books").exists())

    def test_compatible_output_options_keep_named_files_in_books(self):
        self.export(self.report, "-o", "books")
        self.export("-o", self.books / "納品用.xlsx", self.report)
        self.export(self.report.name, "--output", "確認用.xlsx", cwd=self.docs)
        self.assertEqual({p.name for p in self.books.iterdir()},
                         {"結合試験書.xlsx", "納品用.xlsx", "確認用.xlsx"})
        self.assertFalse((self.docs / "確認用.xlsx").exists())

    def test_other_output_directories_are_rejected_before_writing(self):
        for output in ("filled", "別フォルダ/試験.xlsx", "books/../escaped.xlsx",
                       self.root.parent / "outside.xlsx", "books/nested/test.xlsx"):
            with self.subTest(output=output):
                self.assertIn("books", self.export(self.report, "-o", output, expected=2))
        self.assertFalse(self.books.exists())
        self.assertFalse((self.root / "filled").exists())
        self.assertFalse((self.root / "別フォルダ").exists())
        self.assertFalse((self.root / "escaped.xlsx").exists())
        self.assertFalse((self.root.parent / "outside.xlsx").exists())

    def test_redirected_books_cannot_write_into_another_directory(self):
        elsewhere = self.root.parent / "elsewhere"
        elsewhere.mkdir()
        if os.name == "nt":
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                 "$ErrorActionPreference='Stop'; New-Item -ItemType Junction "
                 "-Path $env:RDC_TEST_LINK -Target $env:RDC_TEST_TARGET | Out-Null"],
                env={**self.env, "RDC_TEST_LINK": str(self.books), "RDC_TEST_TARGET": str(elsewhere)},
                capture_output=True, check=True,
            )
        else:
            self.books.symlink_to(elsewhere, target_is_directory=True)
        self.assertIn("books", self.export(self.report, "-o", "books", expected=2))
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_templates_and_filled_reports_cannot_overwrite_each_other(self):
        self.export("--templates", self.report)
        output = self.books / "結合試験書.xlsx"
        template = self.books / "テンプレート_結合試験書.xlsx"
        self.assertIn("実測値1234", workbook_contents(output)[1])
        self.assertNotIn("実測値1234", workbook_contents(template)[1])
        self.assertEqual(len(list(self.books.glob("テンプレート_*.xlsx"))), 10)
        self.assertEqual(len(list(self.books.iterdir())), 11)
        original = output.read_bytes()
        self.export("--templates", "-o", "books")
        source = self.root / ".compass/workflow/phase/integration-testing/references/template.md"
        self.export(source)
        self.assertEqual(original, output.read_bytes())
        self.export(source, "-o", "個別.xlsx")
        self.assertTrue((self.books / "テンプレート_個別.xlsx").is_file())
        self.assertFalse((self.books / "個別.xlsx").exists())
        self.export(self.report, "-o", template, expected=2)
        self.assertNotIn("実測値1234", workbook_contents(template)[1])

    def test_batch_collisions_and_invalid_batch(self):
        second = self.docs / "other.md"
        second.write_text("# 結合試験書\n\n別のケース\n", encoding="utf-8")
        self.export(self.report, second, "-o", "books/単一.xlsx", expected=2)
        self.export(self.report, "missing.md", "-o", "books", expected=2)
        self.assertFalse(self.books.exists())
        self.export(self.report, second, "-o", self.books)
        self.assertIn("実測値1234", workbook_contents(self.books / "結合試験書.xlsx")[1])
        self.assertIn("別のケース", workbook_contents(self.books / "結合試験書 (2).xlsx")[1])


if __name__ == "__main__":
    unittest.main()
