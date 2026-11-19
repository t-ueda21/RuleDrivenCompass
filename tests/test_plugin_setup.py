import codecs
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "plugins/compass/skills/compass-setup/scripts/setup.py"
PACKAGE = ROOT / "scripts/package_compass.py"


def common_files(directory):
    files = {}
    for path in directory.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            if path.suffix.lower() in {".md", ".py", ".json", ".yaml", ".yml"}:
                data = data.replace(b"\r\n", b"\n")
            files[path.relative_to(directory).as_posix()] = data
    return files


class PluginSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / "テスト project"
        self.project.mkdir()

    def run_setup(self, *args, success=True):
        result = subprocess.run(
            [sys.executable, str(SETUP), "--project", str(self.project), *args],
            capture_output=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.assertEqual(result.returncode, 0 if success else 1, result.stderr)
        return result

    def test_fresh_install_matches_package_and_has_no_project_records(self):
        self.run_setup()
        actual = common_files(self.project / ".compass")
        self.assertEqual(actual, common_files(SETUP.parents[1] / "assets/compass"))
        subprocess.run([sys.executable, str(PACKAGE), "--check"], cwd=ROOT, check=True, capture_output=True)
        self.assertIn("guide/python/README.md", actual)
        self.assertIn("workflow/phase/investigation/references/cost-estimate.xlsx", actual)
        self.assertEqual({p for p in actual if p.startswith("records/")}, {"records/README.md"})
        self.assertTrue((self.project / "AGENTS.md").is_file())
        self.assertFalse((self.project / "CLAUDE.md").exists())
        self.assertFalse((self.project / ".claude").exists())
        self.assertIn("今回の変更 0 件", self.run_setup().stdout)

    def test_principles_and_conditional_rules_are_reachable_after_install(self):
        self.run_setup()
        compass = self.project / ".compass"
        setup_skill = SETUP.parents[1] / "SKILL.md"
        bundled = setup_skill.parent / "assets/compass"
        routes = {
            setup_skill: [bundled / "principles/README.md"],
            self.project / "AGENTS.md": [compass / "README.md"],
            compass / "README.md": [
                compass / "principles/README.md",
                compass / "workflow/README.md",
                compass / "workflow/clarify-purpose/SKILL.md",
                compass / "documents/article-standards.md",
            ],
            compass / "principles/README.md": [compass / "principles/do-not-lie.md"],
            compass / "workflow/README.md": [compass / "workflow/clarify-purpose/SKILL.md"],
            compass / "workflow/preflight/SKILL.md": [compass / "workflow/clarify-purpose/SKILL.md"],
            compass / "workflow/clarify-purpose/SKILL.md": [compass / "workflow/issue-tracking/SKILL.md"],
            compass / "documents/README.md": [compass / "documents/article-standards.md"],
        }
        for source, targets in routes.items():
            links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", source.read_text(encoding="utf-8-sig"))
            local_paths = {(source.parent / link).resolve() for link in links if "://" not in link}
            for target in targets:
                with self.subTest(source=source.name, target=target):
                    self.assertIn(target, local_paths)
                    self.assertTrue(target.is_file())

    def test_update_preserves_records_and_existing_project_instructions(self):
        records = self.project / ".compass/records"
        records.mkdir(parents=True)
        for name in ("issue-log.md", "phase-gates.sqlite3"):
            (records / name).write_bytes(b"existing project record")
        agents = self.project / "AGENTS.md"
        agents.write_bytes(codecs.BOM_UTF8 + b"# Team rules\r\n")
        claude = self.project / ".claude/CLAUDE.md"
        claude.parent.mkdir()
        example = b"Keep this example:\r\n```text\r\n@../AGENTS.md\r\n```\r\n"
        claude.write_bytes(example)
        self.run_setup()
        self.assertTrue(agents.read_bytes().startswith(codecs.BOM_UTF8 + b"# Team rules\r\n"))
        self.assertEqual(claude.read_bytes(), example + b"\r\n@../AGENTS.md\r\n")
        guide = self.project / ".compass/guide/python/README.md"
        guide.write_bytes(b"Local guide")
        self.assertIn("guide", self.run_setup(success=False).stderr)
        self.assertEqual(guide.read_bytes(), b"Local guide")
        self.run_setup("--update")
        self.assertIn("Python", guide.read_text(encoding="utf-8"))
        self.assertIn("今回の変更 0 件", self.run_setup().stdout)
        for name in ("issue-log.md", "phase-gates.sqlite3"):
            self.assertEqual((records / name).read_bytes(), b"existing project record")

    def test_packaging_includes_new_guides_and_excludes_even_tracked_records(self):
        build = self.project / "scripts/package_compass.py"
        build.parent.mkdir()
        shutil.copyfile(PACKAGE, build)
        expected = {"README.md", "workflow/README.md", "guide/new-tool/example.bin", "records/README.md"}
        for name in expected | {"records/issue-log.md", "records/phase-gates.sqlite3"}:
            file = self.project / ".compass" / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"fixture")
        subprocess.run(["git", "init", "-q"], cwd=self.project, check=True)
        subprocess.run(["git", "add", "-f", ".compass"], cwd=self.project, check=True)
        subprocess.run([sys.executable, str(build)], cwd=self.project, check=True, capture_output=True)
        payload = self.project / "plugins/compass/skills/compass-setup/assets/compass"
        self.assertEqual(set(common_files(payload)), expected)
        retired = Path("guide/new-tool/example.bin")
        source = self.project / ".compass"
        (source / retired).unlink()
        (source / retired.parent).rmdir()
        (source / retired.parent).write_bytes(b"replacement")
        check = subprocess.run([sys.executable, str(build), "--check"], cwd=self.project, capture_output=True)
        self.assertEqual(check.returncode, 1)
        self.assertTrue((payload / retired).exists())
        subprocess.run([sys.executable, str(build)], cwd=self.project, check=True, capture_output=True)
        self.assertFalse((payload / retired).exists())
        self.assertEqual((payload / retired.parent).read_bytes(), b"replacement")
        (source / retired.parent).unlink()
        (source / retired.parent).mkdir()
        (source / retired).write_bytes(b"restored")
        subprocess.run([sys.executable, str(build)], cwd=self.project, check=True, capture_output=True)
        self.assertEqual((payload / retired).read_bytes(), b"restored")


if __name__ == "__main__":
    unittest.main()
