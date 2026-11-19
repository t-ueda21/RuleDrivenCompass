"""Regression checks for RDC's first-attempt policy through the public gate CLI."""

import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / ".compass/documents/scripts/check_phase_gate.py"
PHASES = ROOT / ".compass/workflow/phase"
PHASE = "integration-testing"
GENERATED = ("実行結果（必須）", "初回・最終結果（必須）", "判定集計（必須）")


def sections(text):
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2]))


class FirstResultTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "spec.md").write_text("# 受入条件 T1\n0以上を受理する。", encoding="utf-8")
        (self.root / "build.txt").write_text("v1", encoding="utf-8")
        (self.root / "run.log").write_text("observed original facts", encoding="utf-8")
        self.doc = self.document(PHASE, ["C1", "C2"])

    def document(self, phase, cases, generated=None, final_run=None):
        doc = self.root / f"{phase}.md"
        template = (PHASES / phase / "references/template.md").read_text(encoding="utf-8")
        out = [template.splitlines()[0]]
        for title, body in sections(template).items():
            out.extend(["", "## " + title, ""])
            if generated and title in generated:
                out.append(generated[title].strip())
                continue
            if title.endswith("（補足）"):
                out.append("該当なし（独立した検証ケース）")
                continue
            rows = [line for line in body.splitlines() if line.startswith("|")]
            out.extend(rows[:2])
            cols = [v.strip() for v in rows[0].strip("|").split("|")]
            if title == "試験ケース（必須）":
                data = [[case, "T1", "在庫", "入力0", "手順A", "数量0を保存"] for case in cases]
            elif title in ("試験範囲と完了判定（必須）", "対象範囲の判定（必須）"):
                data = [
                    ["T1", f"{cases[0]} / {final_run or 'RUN-OLD'}", "合格", "在庫DBを照合", "合格"]
                ]
            else:
                data = [
                    [v.strip() or "記録済みの試験値" for v in row.strip("|").split("|")]
                    for row in rows[2:]
                ]
            for row in data:
                self.assertEqual(len(row), len(cols))
                out.append("| " + " | ".join(row) + " |")
        doc.write_text("\n".join(out) + "\n", encoding="utf-8")
        return doc

    def call(self, *args, work="W", expected=0):
        p = subprocess.run(
            ["uv", "run", str(GATE), args[0], "--work-id", work, *map(str, args[1:])],
            cwd=self.root,
            capture_output=True,
            encoding="utf-8",
            timeout=45,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )
        output = p.stdout + p.stderr
        if expected is not None:
            self.assertEqual(p.returncode, expected, output)
        return p.returncode, output

    def start(self, phase=PHASE, scope=PHASE):
        self.call(
            "start",
            "--phase",
            phase,
            "--scope",
            scope,
            "--mode",
            "production",
            "--target-id",
            "T1",
            "--input-evidence",
            "spec.md",
        )

    def plan(self, *docs, expected=0):
        args = ["test-plan", "--version", "v1", "--baseline", "build.txt"]
        for doc in docs or (self.doc,):
            args.extend(["--document", doc.name])
        return self.call(*args, expected=expected)

    def begin(self, case, phase=PHASE, version="v1", extra=(), expected=0):
        _, output = self.call(
            "test-begin",
            "--phase",
            phase,
            "--case-id",
            case,
            "--version",
            version,
            "--operation",
            "テスト呼出",
            *extra,
            expected=expected,
        )
        return re.search(r"RUN-\d+", output).group() if expected == 0 else output

    def result(self, run, verdict="合格", actual="数量0", expected=0):
        return self.call(
            "test-result",
            "--run-id",
            run,
            "--outcome",
            verdict,
            "--actual",
            actual,
            "--evidence",
            "run.log",
            expected=expected,
        )

    def finish(self, phase=PHASE, expected=0):
        return self.call(
            "finish",
            "--phase",
            phase,
            "--document",
            f"{phase}.md",
            "--evidence",
            "spec.md",
            "--review",
            "confirmed",
            expected=expected,
        )

    def report(self, phase=PHASE):
        return self.call("test-report", "--phase", phase)[1]

    def test_failed_procedure_then_repair_after_sweep(self):
        self.start()
        self.plan()
        a = self.begin("C1")
        self.result(a, "判定不能", "CSV名の誤記で停止")
        self.result(a, "合格", expected=1)
        self.begin("C1", extra=("--reason", "手順を訂正"), expected=1)
        b = self.begin("C2")
        self.begin("C1", extra=("--reason", "手順を訂正"), expected=1)
        self.result(b)
        self.begin("C1", expected=1)
        self.doc.write_text(
            self.doc.read_text(encoding="utf-8").replace("手順A", "手順B", 1), encoding="utf-8"
        )
        retry = self.begin("C1", version="v2", extra=("--reason", "原因はCSV名の誤記。手順Bに修正"))
        (self.root / "run.log").write_text("second log", encoding="utf-8")
        self.result(retry)
        report = self.report()
        self.assertIn(f"| C1 | {a} | 判定不能 | {retry} | 合格 | 再試験 |", report)
        self.assertIn("CSV名の誤記で停止", report)
        self.assertIn("手順Bに修正", report)
        self.assertIn("| 初回 | 2 | 1 | 0 | 1 | 0 | 0 | 0 |", report)
        self.assertIn("| 最終 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |", report)
        copies = list((self.root / ".compass/records/test-evidence").rglob("*"))
        self.assertIn(b"observed original facts", [p.read_bytes() for p in copies if p.is_file()])
        self.start()
        self.assertIn(f"| C1 | {a} | 判定不能 |", self.report())

    def test_gate_rejects_erased_first_row_and_false_counts(self):
        self.start()
        self.plan()
        first = self.begin("C1")
        self.result(first, "不合格", "期待0、観測1")
        self.result(self.begin("C2"))
        last = self.begin("C1", extra=("--reason", "初期値を修正"))
        self.result(last)
        tables = sections(self.report())
        self.document(PHASE, ["C1", "C2"], tables, last)
        self.finish()
        original = self.doc.read_text(encoding="utf-8")
        for tampered in (
            "\n".join(
                line for line in original.splitlines() if not line.startswith(f"| {first} |")
            ),
            original.replace(f"| C1 | {first} | 不合格 |", f"| C1 | {last} | 合格 |"),
            original.replace("| 初回 | 2 | 1 | 1 |", "| 初回 | 2 | 2 | 0 |"),
        ):
            self.assertNotEqual(original, tampered)
            self.doc.write_text(tampered, encoding="utf-8")
            self.finish(expected=1)

    def test_rejudgment_keeps_single_run_and_original_evidence(self):
        self.start()
        self.plan()
        first = self.begin("C1")
        self.result(first, "不合格", "ログには0、当初は異常と判定")
        args = [
            "test-rejudge",
            "--run-id",
            first,
            "--outcome",
            "合格",
            "--reason",
            "元の期待値0と同じログの0が一致",
            "--version",
        ]
        self.call(*args, "v1", expected=1)
        self.result(self.begin("C2"))
        self.call(*args, "v2", expected=1)
        self.call(*args, "v1")
        report = self.report()
        self.assertIn(f"| C1 | {first} | 不合格 | {first} | 合格 | 再判定 |", report)
        self.assertIn("元の期待値0と同じログの0が一致", report)
        self.assertEqual(len(re.findall(r"^\| RUN-\d+ \|", report, re.MULTILINE)), 2)
        self.doc.write_text(
            self.doc.read_text(encoding="utf-8").replace("数量0を保存", "数量1を保存", 1),
            encoding="utf-8",
        )
        self.call(*args, "v1", expected=1)

    def test_multiple_phases_share_sweep_and_blocked_is_not_a_pass(self):
        scope = PHASE + ",system-testing"
        self.start(scope=scope)
        second = self.document("system-testing", ["S1"])
        self.plan(self.doc, expected=1)
        self.plan(self.doc, second)
        a = self.begin("C1")
        self.result(a, "不合格", "登録0件")
        self.result(self.begin("C2"))
        self.begin("C1", extra=("--reason", "修正"), expected=1)
        self.begin("S1", "system-testing", expected=1)
        blocked = self.begin("S1", "system-testing", extra=("--blocked",))
        self.result(blocked, "合格", expected=1)
        self.result(blocked, "実施不能", "結合試験 C1 が不合格で前提未達")
        self.call(
            "test-rejudge",
            "--run-id",
            blocked,
            "--outcome",
            "合格",
            "--reason",
            "再読",
            "--version",
            "v1",
            expected=1,
        )
        self.result(self.begin("C1", extra=("--reason", "登録処理を修正")))
        self.assertIn(f"| S1 | {blocked} | 実施不能 |", self.report("system-testing"))

    def test_frozen_plan_cannot_shrink_or_change_before_sweep(self):
        self.start()
        self.plan()
        self.result(self.begin("C1"))
        self.document(PHASE, ["C1"])
        self.plan(expected=1)
        self.begin("C2", expected=1)
        self.document(PHASE, ["C1", "C2"])
        self.begin("C2", version="v2", expected=1)
        (self.root / "build.txt").write_text("changed", encoding="utf-8")
        self.begin("C2", expected=1)
        (self.root / "build.txt").write_text("v1", encoding="utf-8")
        self.result(self.begin("C2"))

    def test_unfinished_attempt_survives_restart_and_concurrent_begins(self):
        self.start()
        self.plan()
        args = [
            "test-begin",
            "--phase",
            PHASE,
            "--case-id",
            "C1",
            "--operation",
            "テスト呼出",
            "--version",
            "v1",
        ]
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: self.call(*args, expected=None), range(2)))
        self.assertEqual(sorted(code for code, _ in results), [0, 1])
        first = re.search(r"RUN-\d+", next(out for code, out in results if code == 0)).group()
        self.start()
        self.assertIn(f"| C1 | {first} | 実行中 |", self.report())
        self.begin("C1", expected=1)
        self.result(first, "判定不能", "実行中断をログで確認")
        self.finish(expected=1)

    def test_all_three_templates_and_all_pass_summary(self):
        for phase in ("unit-testing", PHASE, "system-testing"):
            with self.subTest(phase=phase):
                work = "W-" + phase
                doc = self.document(phase, ["ONLY"])
                self.call(
                    "start",
                    "--phase",
                    phase,
                    "--scope",
                    phase,
                    "--mode",
                    "production",
                    "--target-id",
                    "T1",
                    "--input-evidence",
                    "spec.md",
                    work=work,
                )
                self.call("test-plan", "--version", "v1", "--document", doc.name, work=work)
                out = self.call(
                    "test-begin",
                    "--phase",
                    phase,
                    "--case-id",
                    "ONLY",
                    "--version",
                    "v1",
                    "--operation",
                    "操作1",
                    work=work,
                )[1]
                run = re.search(r"RUN-\d+", out).group()
                self.call(
                    "test-result",
                    "--run-id",
                    run,
                    "--outcome",
                    "合格",
                    "--actual",
                    "数量0",
                    "--evidence",
                    "run.log",
                    work=work,
                )
                text = self.call("test-report", "--phase", phase, work=work)[1]
                self.assertIn("| 初回 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |", text)
                doc = self.document(phase, ["ONLY"], sections(text), run)
                self.call(
                    "finish",
                    "--phase",
                    phase,
                    "--document",
                    doc.name,
                    "--evidence",
                    "run.log",
                    "--review",
                    "confirmed",
                    work=work,
                )

    def test_old_ledger_stays_readable_without_inventing_a_first_result(self):
        path = self.root / ".compass/records/phase-gates.sqlite3"
        path.parent.mkdir(parents=True)
        with sqlite3.connect(path) as db:
            db.execute(
                "CREATE TABLE phase_gates(work_id TEXT,phase TEXT,value TEXT,PRIMARY KEY(work_id,phase))"
            )
            db.execute(
                "INSERT INTO phase_gates VALUES ('W',?,?)",
                (
                    PHASE,
                    '{"mode":"production","scope":["integration-testing"],"targets":["T1"],"inputs":{},"status":"通過"}',
                ),
            )
        db.close()
        text = self.call("status")[1]
        self.assertIn("通過", text)
        self.assertIn("初回記録なし", text)
        self.finish(expected=1)

    def test_command_reserves_id_and_captures_launch_failure_and_retry(self):
        self.start()
        self.plan()

        def execute(case, command, *options, expected=0):
            return self.call(
                "test-run",
                "--phase",
                PHASE,
                "--case-id",
                case,
                "--version",
                "v1",
                *options,
                "--",
                *command,
                expected=expected,
            )[1]

        failed = execute("C1", [str(self.root / "missing-runner")], expected=1)
        first = re.search(r"RUN-\d+", failed).group()
        self.assertIn("判定不能", failed)
        success = [sys.executable, "-c", "print('output from | actual test')"]
        execute("C1", success, "--reason", "呼出名を修正", expected=1)
        execute("C2", success)
        last = re.search(r"RUN-\d+", execute("C1", success, "--reason", "呼出名を修正")).group()
        report = self.report()
        self.assertIn(f"| C1 | {first} | 判定不能 | {last} | 合格 | 再試験 |", report)
        logs = [
            p.read_bytes()
            for p in (self.root / ".compass/records/test-evidence").rglob("*")
            if p.is_file()
        ]
        self.assertTrue(any(b"missing-runner" in log for log in logs))
        self.assertTrue(any(b"output from | actual test" in log for log in logs))
        self.document(PHASE, ["C1", "C2"], sections(report), last)
        self.finish()
        self.begin("C1", extra=("--blocked", "--reason", "状態確認"), expected=1)

    def test_mid_run_change_preserves_observation_and_requires_a_new_run(self):
        self.start()
        self.plan()
        first = self.begin("C1")
        (self.root / "build.txt").write_text("edited before recording", encoding="utf-8")
        self.result(first, "合格", "観測値は0")
        report = self.report()
        self.assertIn(f"| C1 | {first} | 判定不能 |", report)
        self.assertIn("観測値は0", report)
        self.assertIn("合格", sections(report)["実行結果（必須）"])
        self.result(self.begin("C2", extra=("--blocked",)), "実施不能", "初回版の再現ができない")
        (self.root / "build.txt").write_text("v1", encoding="utf-8")
        self.call(
            "test-rejudge",
            "--run-id",
            first,
            "--version",
            "v1",
            "--outcome",
            "合格",
            "--reason",
            "観測値0",
            expected=1,
        )

    def test_work_report_totals_include_all_planned_phases(self):
        self.start(scope=PHASE + ",system-testing")
        self.plan(self.doc, self.document("system-testing", ["C1"]))
        self.result(self.begin("C1"))
        text = self.call("test-report")[1]
        self.assertIn("作業全体", text)
        self.assertIn("初回 計画数 3 合格 1 不合格 0 判定不能 0 実施不能 0 未着手 2 実行中 0", text)

    def test_reopened_legacy_completed_phase_cannot_relabel_retest_as_first(self):
        path = self.root / ".compass/records/phase-gates.sqlite3"
        path.parent.mkdir(parents=True)
        with sqlite3.connect(path) as db:
            db.execute(
                "CREATE TABLE phase_gates(work_id TEXT,phase TEXT,value TEXT,PRIMARY KEY(work_id,phase))"
            )
            db.execute(
                "INSERT INTO phase_gates VALUES ('W',?,?)",
                (
                    PHASE,
                    '{"mode":"production","scope":["integration-testing"],"targets":["T1"],"inputs":{},"status":"通過"}',
                ),
            )
        db.close()
        self.start()
        self.plan(expected=1)
        self.assertIn("初回記録なし", self.call("status")[1])

    def test_command_that_never_started_cannot_be_rejudged_as_passed(self):
        self.start()
        self.plan()
        _, output = self.call(
            "test-run",
            "--phase",
            PHASE,
            "--case-id",
            "C1",
            "--version",
            "v1",
            "--",
            str(self.root / "missing-executable"),
            expected=1,
        )
        failed = re.search(r"RUN-\d+", output).group()
        self.result(self.begin("C2"))
        self.call(
            "test-rejudge",
            "--run-id",
            failed,
            "--version",
            "v1",
            "--outcome",
            "合格",
            "--reason",
            "実行を確認したつもり",
            expected=1,
        )
        self.assertIn(f"| C1 | {failed} | 判定不能 | {failed} | 判定不能 | 初回 |", self.report())

    def test_downstream_start_can_recover_from_target_outside_plan(self):
        scope = PHASE + ",system-testing"
        self.start(scope=scope)
        self.plan(self.doc, self.document("system-testing", ["S1"]))
        last = self.begin("C1")
        self.result(last)
        self.result(self.begin("C2"))
        self.document(PHASE, ["C1", "C2"], sections(self.report()), last)
        self.finish()
        self.call(
            "start",
            "--phase",
            "system-testing",
            "--mode",
            "production",
            "--scope",
            scope,
            "--input-evidence",
            "spec.md",
            "--target-id",
            "T9",
            expected=1,
        )
        self.start(phase="system-testing", scope=scope)
        self.result(self.begin("S1", phase="system-testing"))


    def test_target_summary_cannot_claim_pass_for_a_failed_final_case(self):
        self.start()
        self.plan()
        failed = self.begin("C1")
        self.result(failed, "不合格", "期待0、実測1")
        self.result(self.begin("C2"))
        self.document(PHASE, ["C1", "C2"], sections(self.report()), failed)
        self.finish(expected=1)
        original = self.doc.read_text(encoding="utf-8")
        self.doc.write_text(
            original.replace(
                f"| T1 | C1 / {failed} | 合格 | 在庫DBを照合 | 合格 |",
                f"| T1 | C1 / {failed} | 在庫DBを照合 | C1の件数不一致を記録 | 不合格 |",
            ),
            encoding="utf-8",
        )
        self.finish()


if __name__ == "__main__":
    unittest.main()
