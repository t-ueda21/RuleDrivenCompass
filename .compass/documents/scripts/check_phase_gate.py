# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown-it-py==4.0.0"]
# ///
"""Check and record RDC phase entry and completion decisions."""

import argparse
import json
import re
import sqlite3
import sys
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from markdown_it.tree import SyntaxTreeNode

sys.dont_write_bytecode = True
from check_document import TEST_OUTCOMES, cell_error, digest, inspect_document, item_id, read_sections, section_rows
import test_history as journal


PHASE_ORDERS = {
    "production": (
        "investigation", "requirements-definition", "basic-design", "detailed-design",
        "implementation", "unit-testing", "integration-testing", "system-testing", "release",
    ),
    "poc": ("requirements-definition", "implementation", "system-testing"),
    "independent": ("investigation", "release"),
}


@dataclass(frozen=True)
class TestSource:
    phase: str
    heading: str
    id_column: str
    case_column: str


TEST_SOURCES = {
    "unit-testing": TestSource(
        "detailed-design", "部品仕様（必須）", "仕様 ID・項目名",
        "詳細設計の仕様 ID・項目名",
    ),
    "integration-testing": TestSource(
        "basic-design", "要素間の契約（補足）", "契約 ID・項目名",
        "基本設計の契約 ID・項目名",
    ),
    "system-testing": TestSource(
        "requirements-definition", "受け入れ条件（本番必須）", "条件 ID・項目名",
        "要件定義の条件 ID・項目名",
    ),
}
CASE_COLUMN = "ケース ID・項目名"
DATABASE = Path(".compass/records/phase-gates.sqlite3")


@dataclass
class Gate:
    mode: str
    scope: list[str]
    targets: list[str]
    inputs: dict[str, str]
    status: str = "作業中"
    documents: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    restart_required: bool = False
    note: str = ""
    updated: str = ""
    legacy_tests: bool = False


@dataclass(frozen=True)
class Decision:
    status: str
    details: list[str] = field(default_factory=list)
    note: str = ""


def fingerprint(root: Path, paths: list[Path]) -> dict[str, str]:
    files = {}
    for raw in paths:
        path = (root / raw).resolve(strict=True)
        name = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        files[name] = digest(path)
    return files


def changed_files(root: Path, *snapshots: dict[str, str]) -> list[str]:
    saved_versions: dict[str, set[str]] = {}
    for files in snapshots:
        for name, saved in files.items():
            saved_versions.setdefault(name, set()).add(saved)

    problems = []
    for name, versions in saved_versions.items():
        try:
            if {digest(root / name)} != versions:
                problems.append(f"確認した版から変更された。{name}")
        except OSError:
            problems.append(f"確認した資料を読み取れない。{name}")
    return problems


def load_gates(conn: sqlite3.Connection, work_id: str) -> dict[str, Gate]:
    gates = {}
    for phase, value in conn.execute(
        "SELECT phase, value FROM phase_gates WHERE work_id = ?", (work_id,)
    ):
        data = json.loads(value)
        if "legacy_tests" not in data and phase in TEST_SOURCES:
            data["legacy_tests"] = bool(data.get("documents")) or data.get("status") == "通過"
        gates[phase] = Gate(**data)
    return gates


def save_gate(conn: sqlite3.Connection, work_id: str, phase: str, gate: Gate) -> None:
    gate.updated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO phase_gates (work_id, phase, value) VALUES (?, ?, ?) "
        "ON CONFLICT (work_id, phase) DO UPDATE SET value = excluded.value",
        (work_id, phase, json.dumps(asdict(gate), ensure_ascii=False)),
    )


def previous_issues(
    root: Path, gates: dict[str, Gate], scope: list[str], phase: str
) -> list[str]:
    issues = []
    for previous in scope[:scope.index(phase)]:
        gate = gates.get(previous)
        if gate is None or gate.status != "通過":
            issues.append(f"{previous} のゲートが通過していない")
        else:
            issues.extend(
                f"{previous} — {problem}"
                for problem in changed_files(root, gate.inputs, gate.documents, gate.evidence)
            )
    return issues


def invalidate_following(
    conn: sqlite3.Connection, work_id: str, gates: dict[str, Gate], scope: list[str], phase: str
) -> None:
    for later in scope[scope.index(phase) + 1:]:
        if later in gates:
            gate = gates[later]
            gate.status = "保留"
            gate.restart_required = True
            gate.issues = [f"{phase} の判定が更新された。入力を確認して start を実行する"]
            save_gate(conn, work_id, later, gate)


def target_issues(
    phase: str, mode: str, targets: list[str], root: Path, inputs: dict[str, str]
) -> list[str]:
    rule = TEST_SOURCES[phase]
    heading = rule.heading
    if phase == "system-testing" and mode == "poc":
        heading = "仮説と成功条件（試作必須）"
    known_ids = set()
    standard_input = False
    for name in inputs:
        path = root / name
        if path.suffix.lower() not in {".md", ".markdown"}:
            continue
        if f"## {heading}" not in path.read_text(encoding="utf-8-sig"):
            continue
        sections = read_sections(path)
        if heading in sections:
            standard_input = True
            known_ids.update(item_id(row.get(rule.id_column, "")) for row in section_rows(sections, heading))
    if not standard_input:
        return []
    return [f"入力の「{heading}」に対象 ID {key} がない" for key in targets if key not in known_ids]


def test_issues(
    phase: str, targets: list[str], documents: list[dict[str, list[SyntaxTreeNode]]], finals: dict
) -> list[str]:
    target_column = TEST_SOURCES[phase].case_column
    cases: dict[str, str] = {}
    runs: dict[str, str] = {}
    completed: set[str] = set()
    judged: set[str] = set()
    issues = []
    for sections in documents:
        for row in section_rows(sections, "試験ケース（必須）"):
            case = item_id(row[CASE_COLUMN])
            if case in cases:
                issues.append(f"試験ケース ID が重複している。{case}")
            cases[case] = item_id(row[target_column])

    for sections in documents:
        for row in section_rows(sections, "実行結果（必須）"):
            run = item_id(row["実行 ID"])
            case = item_id(row[CASE_COLUMN])
            if run in runs:
                issues.append(f"実行 ID が重複している。{run}")
            runs[run] = case
            if case not in cases:
                issues.append(f"実行結果 {run} に対応する試験ケースがない。{case}")
            elif row["判定"].strip("`").strip() not in TEST_OUTCOMES:
                issues.append(f"実行結果 {run} の当初判定を確認する")
            elif case in finals and finals[case].name == run and finals[case].final in TEST_OUTCOMES[:2]:
                completed.add(case)

    if phase == "system-testing":
        title, column, links = (
            "対象範囲の判定（必須）",
            "条件 ID・項目名",
            "対応するケース・実行 ID",
        )
        verdict = "判定"
    else:
        title, column, links = (
            "試験範囲と完了判定（必須）",
            "判定根拠の項目 ID",
            "対応ケース・実行 ID",
        )
        verdict = "対象範囲の判定"
    failed_targets = {
        target
        for case, target in cases.items()
        if case in finals and finals[case].final == "不合格"
    }
    for sections in documents:
        for row in section_rows(sections, title):
            key = item_id(row[column])
            if key in failed_targets and re.match(
                r"^(?:全件)?合格(?:$|[\s（(:：。])", row[verdict].strip("` ")
            ):
                issues.append(f"{key} の最終不合格ケースと対象範囲の合格判定が一致しない")
            references = set(re.split(r"[`\s,、/／]+", row[links]))
            matching_runs = (
                runs[run]
                for run in references & runs.keys()
                if runs[run] in completed and finals[runs[run]].name == run
            )
            if any(case in references and cases.get(case) == key for case in matching_runs):
                judged.add(key)

    for key in targets:
        matching = [case for case, target in cases.items() if target == key]
        if not matching:
            issues.append(f"対象 ID {key} の試験ケースがない")
            continue
        for case in matching:
            if case not in completed:
                issues.append(f"対象 ID {key} のケース {case} に合否を判定した実行結果がない")
        if key not in judged:
            issues.append(f"対象 ID {key} の完了判定に対応するケース・実行 ID がない")
    return issues


def start_phase(
    args: argparse.Namespace, root: Path, conn: sqlite3.Connection, gates: dict[str, Gate]
) -> Decision:
    scope = [phase.strip() for phase in args.scope.split(",")]
    order = PHASE_ORDERS[args.mode]
    if scope != [phase for phase in order if phase in scope] or args.phase not in scope:
        raise ValueError("指定の開発区分の工程順で、着手する工程を含む作業範囲を指定する")
    if args.mode == "independent" and len(scope) != 1:
        raise ValueError("開発区分が適用外の場合は調査またはリリースを１工程指定する")
    if gates and any(gate.mode != args.mode or gate.scope != scope for gate in gates.values()):
        raise ValueError("作業 ID に登録済みの開発区分・作業範囲と一致しない")

    targets = sorted(set(args.target_id))
    current = gates.get(args.phase)
    if current and current.targets != targets:
        raise ValueError("着手時に登録した対象 ID と一致しない。対象を変更する場合は新しい作業 ID を使う")
    if any(key != item_id(key) or cell_error(key, required=True) for key in targets):
        raise ValueError("--target-id には試験対象の ID を個別に指定する")

    problems = previous_issues(root, gates, scope, args.phase)
    if problems:
        return Decision("保留", problems)

    inputs = fingerprint(root, args.input_evidence)
    if args.phase in TEST_SOURCES:
        if not targets:
            raise ValueError("試験の着手前に、対象となる仕様・契約・条件の ID を指定する")
        plan = journal.plans_for(conn, args.work_id).get(args.phase)
        if plan:
            target_column = TEST_SOURCES[args.phase].case_column
            planned = {item_id(case["fields"][target_column]) for case in plan["cases"].values()}
            if not set(targets) <= planned:
                raise ValueError("対象 ID が登録済みの初回計画と一致しない")
        source = gates.get(TEST_SOURCES[args.phase].phase)
        if not inputs and source is None:
            raise ValueError("対象 ID の根拠となる既存資料を --input-evidence で指定する")
        source_documents = source.documents if source else {}
        problems = target_issues(args.phase, args.mode, targets, root, source_documents or inputs)
        problems.extend(changed_files(root, source_documents, inputs))
        if problems:
            return Decision("保留", problems)

    gate = Gate(args.mode, scope, targets, inputs, legacy_tests=bool(current and current.legacy_tests))
    save_gate(conn, args.work_id, args.phase, gate)
    invalidate_following(conn, args.work_id, gates, scope, args.phase)
    return Decision("着手可", [f"対象 ID {', '.join(targets)}"] if targets else [])


def finish_phase(
    args: argparse.Namespace, root: Path, conn: sqlite3.Connection, gates: dict[str, Gate]
) -> Decision:
    gate = gates.get(args.phase)
    if gate is None or gate.restart_required:
        raise ValueError(f"{args.phase} の着手を start で確認する")

    issues = []
    documents: dict[str, str] = {}
    evidence: dict[str, str] = {}
    if not args.document:
        issues.append("工程文書が指定されていない")
    if not args.evidence:
        issues.append("完了条件の証跡が指定されていない")
    if args.review != "confirmed":
        issues.append("工程 Skill の完了条件の確認が完了していない")
    for paths, fingerprints in ((args.document, documents), (args.evidence, evidence)):
        for path in paths:
            try:
                fingerprints.update(fingerprint(root, [path]))
            except (OSError, ValueError) as error:
                issues.append(f"資料を読み取れない。{path} — {error}")

    sections = []
    for name in documents:
        try:
            inspection = inspect_document(args.phase, root / name, gate.mode)
            issues.extend(f"{name} — {problem}" for problem in inspection.blocking)
            if not inspection.blocking:
                sections.append(inspection.sections)
        except (OSError, ValueError) as error:
            issues.append(f"{name} — {error}")
    counts = []
    if args.phase in TEST_SOURCES:
        plan = journal.plans_for(conn, args.work_id).get(args.phase)
        attempts = journal.attempts_for(conn, args.work_id) if plan else {}
        issues.extend(journal.completion_issues(root, args.phase, plan, attempts, sections))
        finals = {case: runs[-1] for (phase, case), runs in attempts.items() if phase == args.phase}
        issues.extend(test_issues(args.phase, gate.targets, sections, finals))
        if plan:
            counts = journal.count_lines(((args.phase, key) for key in plan["cases"]), attempts)
            for (phase, _), runs in attempts.items():
                if phase == args.phase:
                    evidence.update(
                        {run.result["log"]: run.result["hash"] for run in runs if run.result}
                    )

    issues.extend(previous_issues(root, gates, gate.scope, args.phase))
    issues.extend(changed_files(root, gate.inputs, documents, evidence))
    status = "保留" if issues else "通過"
    if (gate.status, gate.documents, gate.evidence) != (status, documents, evidence):
        invalidate_following(conn, args.work_id, gates, gate.scope, args.phase)
    gate.status = status
    gate.documents = documents
    gate.evidence = evidence
    gate.note = args.note
    gate.issues = issues
    save_gate(conn, args.work_id, args.phase, gate)
    return Decision(status, issues + counts, gate.note)


def print_report(title: str, issues: list[str], note: str = "") -> None:
    print(title)
    for issue in issues:
        print(f"- {issue}")
    if note:
        print(f"  {note}")


def show_status(root: Path, gates: dict[str, Gate], plans: dict, attempts: dict) -> int:
    if not gates:
        print("判定記録がない")
        return 0
    scope = next(iter(gates.values())).scope
    for phase in scope:
        gate = gates.get(phase)
        counts = (
            journal.count_lines(((phase, key) for key in plans[phase]["cases"]), attempts)
            if phase in plans
            else []
        )
        if not gate:
            print_report(f"{phase} 未着手", counts)
            continue
        issues = previous_issues(root, gates, scope, phase)
        issues.extend(changed_files(root, gate.inputs, gate.documents, gate.evidence))
        status = "保留（再確認）" if issues else gate.status
        if phase in TEST_SOURCES and phase not in plans:
            counts = ["初回記録なし"]
        print_report(f"{phase} {status}  {gate.updated}", gate.issues + issues + counts, gate.note)
        if gate.targets:
            print(f"  対象 ID {', '.join(gate.targets)}")
        for label, files in (
            ("入力", gate.inputs),
            ("文書", gate.documents),
            ("証跡", gate.evidence),
        ):
            for path in files:
                print(f"  {label} {path}")
    return 0


def journal_action(args, root, conn, gates):
    journal.ensure_schema(conn)
    if args.command == "test-plan":
        return journal.register(conn, root, args, gates, TEST_SOURCES)
    plans = journal.plans_for(conn, args.work_id)
    attempts = journal.attempts_for(conn, args.work_id)
    starting = args.command in {"test-begin", "test-run"}
    if starting:
        phase = args.phase
    else:
        run = journal.lookup(attempts, args.run_id)
        if args.command == "test-result":
            if args.interrupted and args.outcome != "判定不能":
                raise ValueError("中断した試行は判定不能として事実と根拠を記録する")
            if run.start.get("command") and not (args.interrupted and args.outcome == "判定不能"):
                raise ValueError(
                    "自動試行は test-run が記録する。強制終了時は --interrupted と判定不能で中断理由を記録する"
                )
            return journal.record(
                conn,
                root,
                run,
                args.outcome,
                args.actual,
                args.evidence,
                plans[run.phase],
                TEST_SOURCES,
                requires_rerun=args.interrupted,
            )
        phase = run.phase
    # A downstream dependency can prevent the very first operation from being executed.
    gate = gates.get(phase)
    if gate and gate.status == "通過":
        raise ValueError(f"{phase} の再着手を start で確認する")
    if not (starting and args.blocked):
        if not gate or gate.restart_required:
            raise ValueError(f"{phase} の着手を start で確認する")
        problems = previous_issues(root, gates, gate.scope, phase) + changed_files(
            root, gate.inputs
        )
        if problems:
            raise ValueError("、".join(problems))
    if starting:
        return journal.begin(conn, root, args, plans, attempts, TEST_SOURCES)
    return journal.rejudge(conn, root, args, run, plans, attempts, TEST_SOURCES)


def main() -> int:
    parser = argparse.ArgumentParser(description="RDC の工程の着手と完了を判定する。プロジェクトルートで実行する。")
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="入力と前工程の通過を確認し、今回の工程を登録する")
    finish = commands.add_parser("finish", help="工程文書、証跡、完了条件を確認する")
    status = commands.add_parser("status", help="作業 ID の工程ごとの判定を表示する")
    for command in (start, finish, status):
        command.add_argument("--work-id", required=True)
    for command in (start, finish):
        command.add_argument("--phase", required=True, choices=PHASE_ORDERS["production"])
    start.add_argument("--mode", required=True, choices=PHASE_ORDERS)
    start.add_argument("--scope", required=True, help="作業範囲の工程 ID を順番にカンマ区切りで指定する")
    start.add_argument("--target-id", action="append", default=[])
    start.add_argument("--input-evidence", action="append", type=Path, default=[])
    finish.add_argument("--document", action="append", type=Path, default=[])
    finish.add_argument("--evidence", action="append", type=Path, default=[])
    finish.add_argument("--review", required=True, choices=("confirmed", "pending"))
    finish.add_argument("--note", default="")
    journal.arguments(commands, tuple(TEST_SOURCES))
    args = parser.parse_args()

    root = Path.cwd()
    database = root / DATABASE
    try:
        if not args.work_id.strip():
            raise ValueError("空欄以外の作業 ID を指定する")
        if args.command in {"status", "test-report"}:
            if not database.is_file():
                print("初回記録なし" if args.command == "test-report" else "判定記録がない")
                return 0
            with closing(sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)) as conn:
                conn.execute("BEGIN")
                plans = journal.plans_for(conn, args.work_id)
                attempts = journal.attempts_for(conn, args.work_id) if plans else {}
                if args.command == "test-report":
                    print(journal.report(plans, attempts, args.phase))
                    return 0
                return show_status(root, load_gates(conn, args.work_id), plans, attempts)

        if args.command != "start" and not database.is_file():
            raise ValueError("工程の着手を start で確認する")
        database.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(database, timeout=15)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS phase_gates ("
                "work_id TEXT NOT NULL, phase TEXT NOT NULL, value TEXT NOT NULL, "
                "PRIMARY KEY (work_id, phase))"
            )
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                gates = load_gates(conn, args.work_id)
                if args.command in journal.COMMANDS:
                    reply = journal_action(args, root, conn, gates)
                else:
                    action = start_phase if args.command == "start" else finish_phase
                    decision = action(args, root, conn, gates)
            if args.command in journal.COMMANDS:
                if isinstance(reply, journal.Attempt):
                    kind = "初回" if reply.start["ordinal"] == 1 else "再試験"
                    print(f"{reply.name} {reply.phase}/{reply.case} {kind}", flush=True)
                    if args.command == "test-run":
                        return journal.execute_command(
                            conn, root, args.work_id, reply, TEST_SOURCES
                        )
                else:
                    print(reply)
                return 0
        print_report(f"{args.phase} {decision.status}", decision.details, decision.note)
        return int(decision.status == "保留")
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"保留 — {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
