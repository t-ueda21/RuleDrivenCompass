"""Requirements gate checks for interactive screen reviews in an installed RDC project."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "plugins/compass/skills/compass-setup/scripts/setup.py"
REVIEW = "画面試作とフィードバック（補足）"
REVIEW_TABLE = (
    "| 画面・操作 | 試作の版・参照先 | 利用者の反応・確認根拠 | 課題 ID | 判断 | "
    "要件 ID・項目名（該当時） | 条件 ID・項目名（該当時） |\n"
    "| --- | --- | --- | --- | --- | --- | --- |\n"
)


class ScreenPrototypeGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)
        self.env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        subprocess.run([sys.executable, str(SETUP), "--project", str(self.project)],
                       env=self.env, check=True, capture_output=True)
        self.gate = self.project / ".compass/documents/scripts/check_phase_gate.py"

    def gate_result(self, mode, review_body, *, declared=None, ledger_state="完了"):
        # Other sections are out of scope for this fixture. Provide all required fields.
        template = self.project / ".compass/workflow/phase/requirements-definition/references/template.md"
        document = ["# 要件定義書"]
        if declared is None:
            declared = bool(review_body and review_body.startswith("|"))
        if declared and ledger_state is not None:
            log = self.project / ".compass/records/issue-log.md"
            log.write_text(
                "# 課題管理表\n\n## 課題一覧\n\n"
                "| 課題 ID | 状態 | 確認先 | 回答・決定日 | 回答・決定内容 | 判断根拠・参照先 |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                f"| Q-001 | {ledger_state} | 試験参加者 | 2026-11-20 | 予約内容を操作確認 | v2の操作レビュー |\n",
                encoding="utf-8",
            )
        for section in template.read_text(encoding="utf-8").split("\n## ")[1:]:
            title, body = section.split("\n", 1)
            if title == REVIEW:
                continue
            document.append("## " + title)
            if title.endswith("（補足）") or title.endswith("（試作必須）" if mode == "production" else "（本番必須）"):
                document.append("対象外（今回の予約条件の確認範囲外）")
                continue
            rows = [row for row in body.splitlines() if row.startswith("|")]
            table = rows[:2]
            for line in rows[2:]:
                cells = [v.strip() or "予約日時と利用者を確認" for v in line.strip("|").split("|")]
                if title == "要件一覧（必須）":
                    cells = ["R1", "機能", "予約内容を確認できる", "利用者", "C1"]
                elif title == "要求の情報源（必須）" and declared:
                    cells = ["画面試作", "予約画面 v2", "R1", "Q-001"]
                elif title.startswith(("受け入れ条件", "仮説と成功条件")):
                    cells[:2] = ["C1", "R1"]
                table.append("| " + " | ".join(cells) + " |")
            document.append("\n".join(table))
        if review_body is not None:
            document.extend(["## " + REVIEW, review_body])
        spec = self.project / "requirements.md"
        spec.write_text("\n\n".join(document) + "\n", encoding="utf-8")
        args = ["--work-id", "screen-" + mode, "--phase", "requirements-definition"]

        def run(*command):
            return subprocess.run(["uv", "run", str(self.gate), *command], cwd=self.project,
                                  env=self.env, capture_output=True, text=True, encoding="utf-8")

        start = run("start", *args, "--scope", "requirements-definition", "--mode", mode)
        self.assertEqual(start.returncode, 0, start.stdout + start.stderr)
        return run("finish", *args, "--document", spec.name, "--evidence", spec.name, "--review", "confirmed")

    def test_review_pending_blocks_even_with_confirmed_document_review(self):
        body = REVIEW_TABLE + "| 予約 | v1 試作 | 未確認（利用者の回答待ち） | Q-001 | 確認待ち |  |  |"
        result = self.gate_result("production", body)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(REVIEW, result.stdout)
        self.assertNotIn("判断 — 状態に理由を記録する", result.stdout)

    def test_accepted_feedback_requires_the_corresponding_condition(self):
        body = REVIEW_TABLE + "| 予約 | v2 試作 | 利用者が予約を確認 | Q-001 | 採用 | R1 | C9 |"
        result = self.gate_result("poc", body)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("C9", result.stdout)

    def test_revised_review_can_pass_in_both_modes(self):
        body = REVIEW_TABLE + "| 予約 | v2 試作 | 利用者が予約を確認 | Q-001 | 採用 | R1 | C1 |"
        for mode in ("production", "poc"):
            with self.subTest(mode=mode):
                result = self.gate_result(mode, body)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_ui_and_previous_format_can_pass_without_prototypes(self):
        for body in ("対象外（APIのみの案件）", None):
            with self.subTest(body=body):
                result = self.gate_result("production", body)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_user_can_decline_a_change_without_inventing_a_requirement(self):
        body = REVIEW_TABLE + "| 予約 | v1 試作 | 利用者が現行範囲で十分と回答 | Q-001 | 見送り |  |  |"
        result = self.gate_result("production", body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_gate_needs_a_recorded_reply_for_a_resolved_review(self):
        body = REVIEW_TABLE + "| 予約 | v2 試作 | 利用者レビュー | Q-001 | 採用 | R1 | C1 |"
        for ledger_state in (None, "確認待ち"):
            with self.subTest(ledger_state=ledger_state):
                result = self.gate_result("production", body, ledger_state=ledger_state)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("画面試作", result.stdout)

    def test_declared_screen_cannot_drop_or_exclude_its_review(self):
        for body in (None, "対象外（今回の範囲外）"):
            with self.subTest(body=body):
                result = self.gate_result("production", body, declared=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(REVIEW, result.stdout)
