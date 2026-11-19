"""Append-only trial plans, attempts and evidence used by the RDC phase gate."""

import argparse
import json
import shutil
import sqlite3
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from check_document import (
    PHASE_DIR,
    TEST_OUTCOMES,
    cell_error,
    check_table,
    digest,
    item_id,
    read_sections,
    section_rows,
    table_rows,
)


CASE = "ケース ID・項目名"
CASE_SECTION = "試験ケース（必須）"
RUN_SECTION = "実行結果（必須）"
SUMMARY_SECTION = "初回・最終結果（必須）"
COUNT_SECTION = "判定集計（必須）"
RUN_COLUMNS = (
    "実行 ID",
    CASE,
    "実施日時",
    "対象版・環境",
    "試行時の入力・手順・期待結果",
    "実際の操作",
    "実際の結果",
    "判定",
    "ログ・証跡の参照先",
    "原因・修正・再判定（該当時）",
)
SUMMARY_COLUMNS = (CASE, "初回の実行 ID", "初回判定", "最終の実行 ID", "最終判定", "判定区分")
COUNT_COLUMNS = ("区分", "計画数", *TEST_OUTCOMES, "未着手", "実行中")
COMMANDS = ("test-plan", "test-begin", "test-run", "test-result", "test-rejudge", "test-report")


def arguments(commands, phases):
    plan = commands.add_parser("test-plan", help="一巡する全ケース・対象版・条件を事前登録する")
    plan.add_argument("--document", required=True, action="append", type=Path)
    plan.add_argument(
        "--baseline",
        action="append",
        type=Path,
        default=[],
        help="一巡中に固定する設計・実装・試験・入力ファイル（複数可）",
    )
    begin = commands.add_parser("test-begin", help="操作前に実行 ID を発行する")
    begin.add_argument("--operation", required=True)
    begin.add_argument(
        "--blocked", action="store_true", help="前提不成立の確認を登録し、実施不能を記録する"
    )
    execute = commands.add_parser(
        "test-run", help="実行 ID を保存し、検査コマンドの終了状態・出力を記録する"
    )
    execute.add_argument(
        "argv", nargs=argparse.REMAINDER, help="-- の後に検査コマンドと引数を指定する"
    )
    execute.set_defaults(blocked=False)
    for command in (begin, execute):
        command.add_argument("--phase", required=True, choices=phases)
        command.add_argument("--case-id", required=True)
        command.add_argument("--reason", default="", help="再試験の原因・修正内容")
        command.add_argument(
            "--baseline", action="append", type=Path, help="再試験時の固定ファイル一覧を更新する"
        )
    result = commands.add_parser("test-result", help="観測結果と当初判定を一度記録する")
    result.add_argument("--outcome", required=True, choices=TEST_OUTCOMES)
    result.add_argument("--actual", required=True)
    result.add_argument("--evidence", required=True, type=Path)
    result.add_argument(
        "--interrupted", action="store_true", help="強制終了された自動試行を判定不能として確定する"
    )
    rejudge = commands.add_parser("test-rejudge", help="元の条件と同じログによる再判定を追記する")
    rejudge.add_argument("--outcome", required=True, choices=TEST_OUTCOMES[:3])
    rejudge.add_argument("--reason", required=True)
    report = commands.add_parser(
        "test-report", help="試験書に転記する実行履歴、初回・最終の判定と集計を表示する"
    )
    report.add_argument("--phase", choices=phases)
    for command in (plan, begin, execute, result, rejudge, report):
        command.add_argument("--work-id", required=True)
    for command in (plan, begin, execute, rejudge):
        command.add_argument("--version", required=True, help="試験対象の版・環境")
    for command in (result, rejudge):
        command.add_argument("--run-id", required=True)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def encoded(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def ensure_schema(conn: sqlite3.Connection) -> None:
    tables = {
        "test_plans": "work_id TEXT, phase TEXT, data TEXT NOT NULL, PRIMARY KEY(work_id, phase)",
        "test_attempts": "id INTEGER PRIMARY KEY, work_id TEXT, phase TEXT, case_id TEXT, data TEXT NOT NULL",
        "test_results": "run INTEGER PRIMARY KEY REFERENCES test_attempts(id), data TEXT NOT NULL",
        "test_reviews": "id INTEGER PRIMARY KEY, run INTEGER REFERENCES test_attempts(id), data TEXT NOT NULL",
    }
    for table, columns in tables.items():
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns})")
        for verb in ("UPDATE", "DELETE"):
            conn.execute(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_{verb} BEFORE {verb} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'RDC test history is append-only'); END"
            )
    conn.execute("CREATE INDEX IF NOT EXISTS test_work ON test_attempts(work_id,phase,case_id)")


def plans_for(conn, work):
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='test_plans'"
    ).fetchone():
        return {}
    return {
        phase: json.loads(data)
        for phase, data in conn.execute(
            "SELECT phase, data FROM test_plans WHERE work_id=? ORDER BY rowid", (work,)
        )
    }


@dataclass
class Attempt:
    number: int
    phase: str
    case: str
    start: dict
    result: dict = field(default_factory=dict)
    reviews: list = field(default_factory=list)

    @property
    def name(self):
        return f"RUN-{self.number:06d}"

    @property
    def original(self):
        return self.result.get("outcome", "実行中")

    @property
    def final(self):
        return self.reviews[-1]["outcome"] if self.reviews else self.original


def attempts_for(conn, work):
    attempts = {}
    by_number = {}
    for number, phase, case, start, result in conn.execute(
        "SELECT a.id,a.phase,a.case_id,a.data,r.data FROM test_attempts a "
        "LEFT JOIN test_results r ON r.run=a.id WHERE a.work_id=? ORDER BY a.id",
        (work,),
    ):
        run = Attempt(number, phase, case, json.loads(start), json.loads(result) if result else {})
        attempts.setdefault((phase, case), []).append(run)
        by_number[number] = run
    for number, data in conn.execute(
        "SELECT r.run,r.data FROM test_reviews r JOIN test_attempts a ON a.id=r.run "
        "WHERE a.work_id=? ORDER BY r.id",
        (work,),
    ):
        by_number[number].reviews.append(json.loads(data))
    return attempts


def required(value, label):
    if cell_error(value.strip(), True):
        raise ValueError(f"{label} に具体的な内容を指定する")
    return value.strip()


def file_name(root, raw):
    path = (root / raw).resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


def baseline(root, paths):
    result = {}
    for raw in paths:
        name = file_name(root, raw)
        try:
            result[name] = digest(root / name)
        except FileNotFoundError:
            result[name] = None
    return result


def cases_from(root, paths, rules):
    phases = {}
    for raw in paths:
        name = file_name(root, raw)
        sections = read_sections(root / name)
        tables = [table_rows(n) for n in sections.get(CASE_SECTION, []) if n.type == "table"]
        if len(tables) != 1:
            raise ValueError(f"{name} の {CASE_SECTION} にケースを登録する")
        table = tables[0]
        phase = next((phase for phase, rule in rules.items() if rule.case_column in table[0]), None)
        if phase is None:
            raise ValueError(f"{name} の試験工程に対応するケース列を確認する")
        template = read_sections(PHASE_DIR / phase / "references/template.md")
        expected = next(table_rows(n) for n in template[CASE_SECTION] if n.type == "table")
        errors = check_table(expected, table, required=True)
        if errors:
            raise ValueError(f"{name} — " + "、".join(errors))
        cases = phases.setdefault(phase, {})
        for row in section_rows(sections, CASE_SECTION):
            key = required(item_id(row[CASE]), "ケース ID")
            if key in cases:
                raise ValueError(f"{phase} のケース ID が重複している。{key}")
            cases[key] = {"document": name, "fields": row}
    return phases


def register(conn, root, args, gates, rules):
    if not gates:
        raise ValueError("作業範囲を start で登録する")
    planned = cases_from(root, args.document, rules)
    scope = next(iter(gates.values())).scope
    if not planned or set(planned) != set(scope).intersection(rules):
        raise ValueError("今回の作業範囲に含まれる全試験工程のケースを一括して登録する")
    saved = plans_for(conn, args.work_id)
    batch = sorted(planned)
    files = baseline(root, args.baseline)
    for phase, cases in planned.items():
        definition = {
            "batch": batch,
            "version": required(args.version, "対象版"),
            "baseline": files,
            "cases": cases,
        }
        if phase in saved:
            if saved[phase] != definition:
                raise ValueError(f"{phase} の登録済み初回計画は変更できない")
            continue
        if phase in gates:
            if gates[phase].legacy_tests:
                raise ValueError(
                    "旧版の試験は初回記録なし。旧作業 ID を参照する追加の試験計画を使う"
                )
            targets = {item_id(case["fields"][rules[phase].case_column]) for case in cases.values()}
            if not set(gates[phase].targets) <= targets:
                raise ValueError(f"{phase} の計画に着手時の対象 ID が不足している")
        conn.execute(
            "INSERT INTO test_plans VALUES (?,?,?)", (args.work_id, phase, encoded(definition))
        )
    return f"初回計画を登録（{sum(len(cases) for cases in planned.values())}ケース）"


def first_pending(plans, attempts, phase):
    return [
        f"{p}/{key}"
        for p in plans[phase]["batch"]
        for key in plans[p]["cases"]
        if not (attempts.get((p, key)) and attempts[p, key][0].result)
    ]


def current_cases(root, plan, phase, rules):
    paths = sorted({case["document"] for case in plan["cases"].values()})
    observed = cases_from(root, paths, rules).get(phase, {})
    target = rules[phase].case_column
    if observed.keys() != plan["cases"].keys() or any(
        item_id(case["fields"][target]) != item_id(plan["cases"][key]["fields"][target])
        for key, case in observed.items()
    ):
        raise ValueError(f"{phase} の計画ケースまたは対応する対象 ID が変更された")
    return observed


def begin(conn, root, args, plans, attempts, rules):
    phase, key = args.phase, args.case_id
    plan = plans.get(phase)
    if not plan or key not in plan["cases"]:
        raise ValueError(f"初回計画にケースがない。{phase}/{key}")
    past = attempts.get((phase, key), [])
    if past and not past[-1].result:
        raise ValueError(f"{past[-1].name} の実行結果を先に記録する")
    if past:
        pending = first_pending(plans, attempts, phase)
        if pending:
            raise ValueError("初回一巡前の再試験。残るケース " + "、".join(pending))
        required(args.reason, "再試験の原因・修正内容")
    elif args.version != plan["version"]:
        raise ValueError("初回計画の対象版と一致しない")

    entry = plan["cases"][key]
    if not past and args.baseline is not None:
        raise ValueError("初回の固定ファイルは test-plan で登録する")
    files = baseline(root, args.baseline if args.baseline is not None else plan["baseline"])
    if not args.blocked:
        if not past:
            for other in plan["batch"]:
                if current_cases(root, plans[other], other, rules) != plans[other]["cases"]:
                    raise ValueError("初回一巡前に試験の入力・手順・期待結果が変更された")
            if files != plan["baseline"]:
                raise ValueError("初回一巡前に固定したファイルが変更された")
        else:
            entry = current_cases(root, plan, phase, rules)[key]
    command = None
    if args.command == "test-run":
        command = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        if not command or not command[0].strip():
            raise ValueError("-- の後に実行する検査コマンドを指定する")
    operation = encoded(command) if command else required(args.operation, "操作")
    data = {
        "at": now(),
        "version": required(args.version, "対象版"),
        "operation": operation,
        "reason": args.reason.strip(),
        "blocked": args.blocked,
        "case": entry,
        "baseline": files,
        "command": command,
        "ordinal": len(past) + 1,
    }
    cursor = conn.execute(
        "INSERT INTO test_attempts(work_id,phase,case_id,data) VALUES (?,?,?,?)",
        (args.work_id, phase, key, encoded(data)),
    )
    return Attempt(cursor.lastrowid, phase, key, data)


def lookup(attempts, name):
    for runs in attempts.values():
        for run in runs:
            if run.name == name:
                return run
    raise ValueError(f"この作業 ID の実行記録を確認する。{name}")


def preserve_log(root, raw):
    source = (root / raw).resolve(strict=True)
    directory = root / ".compass/records/test-evidence"
    if directory.resolve() != directory:
        raise ValueError("試験証跡の保存先を確認する")
    directory.mkdir(parents=True, exist_ok=True)
    temporary = NamedTemporaryFile(dir=directory, delete=False)
    path = Path(temporary.name)
    try:
        with temporary, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, temporary)
        checksum = digest(path)
        target = directory / (checksum + source.suffix)
        if target.resolve() != target:
            raise ValueError("試験証跡の保存先がリンクになっている")
        if target.exists():
            if digest(target) != checksum:
                raise ValueError("保存済みの試験証跡が変更された")
        else:
            path.replace(target)
        return target.relative_to(root).as_posix(), checksum
    finally:
        path.unlink(missing_ok=True)


def condition_change(root, plan, run, rules):
    try:
        current = current_cases(root, plan, run.phase, rules)
        if current[run.case] != run.start["case"]:
            return "ケースの手順・入力・期待結果が試行開始時と異なる"
        if baseline(root, run.start["baseline"]) != run.start["baseline"]:
            return "固定ファイルが試行開始時と異なる"
    except (OSError, ValueError) as error:
        return f"試行開始時の条件を照合できない。{error}"
    return ""


def record(conn, root, run, outcome, observed, evidence, plan, rules, *, requires_rerun=False):
    if run.result:
        raise ValueError(f"{run.name} の当初判定は記録済み")
    if run.start["blocked"] and outcome != "実施不能":
        raise ValueError("前提不成立として登録した試行の判定は実施不能")
    actual = required(observed, "実際の結果・阻害理由")
    drift = "" if run.start["blocked"] else condition_change(root, plan, run, rules)
    log, checksum = preserve_log(root, evidence)
    data = {
        "at": now(),
        "outcome": "判定不能" if drift else outcome,
        "actual": actual,
        "reported": outcome,
        "drift": drift,
        "requires_rerun": requires_rerun,
        "log": log,
        "hash": checksum,
        "source": file_name(root, evidence),
    }
    conn.execute("INSERT INTO test_results VALUES (?,?)", (run.number, encoded(data)))
    run.result = data
    return f"{run.name} 当初判定 {run.original}　証跡 {log}" + (f"　{drift}" if drift else "")


def execute_command(conn, root, work, run, rules):
    directory = root / ".compass/records/test-evidence"
    if directory.resolve() != directory:
        raise ValueError("試験証跡の保存先を確認する")
    directory.mkdir(parents=True, exist_ok=True)
    capture = directory / f"{run.name}.in-progress.log"
    # Keep the live capture on interruption; the attempt was already committed before launch.
    with capture.open("xb") as log:
        log.write((run.start["at"] + " " + run.start["operation"] + "\n").encode("utf-8"))
        log.flush()
        requires_rerun = False
        try:
            proc = subprocess.run(
                run.start["command"],
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
            actual = f"終了コード {proc.returncode}"
            outcome = {0: "合格", 1: "不合格"}.get(proc.returncode, "判定不能")
        except (OSError, KeyboardInterrupt, ValueError) as error:
            actual = f"手順停止 {type(error).__name__} {error}"
            outcome = "判定不能"
            requires_rerun = True
        log.write(("\n" + actual + "\n").encode("utf-8"))
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        plan = plans_for(conn, work)[run.phase]
        message = record(
            conn, root, run, outcome, actual, capture, plan, rules, requires_rerun=requires_rerun
        )
    capture.unlink()
    print(message)
    return int(run.original != "合格")


def rejudge(conn, root, args, run, plans, attempts, rules):
    if run.result.get("requires_rerun"):
        raise ValueError("起動失敗・中断の試行には再実行が必要")
    if (
        not run.result
        or run.original == "実施不能"
        or attempts[run.phase, run.case][-1].number != run.number
    ):
        raise ValueError("実施済みの最新試行を指定する。実施不能のケースは対象の操作を実行する")
    if first_pending(plans, attempts, run.phase):
        raise ValueError("初回一巡後に再判定を記録する")
    if (
        args.version != run.start["version"]
        or run.result.get("drift")
        or condition_change(root, plans[run.phase], run, rules)
    ):
        raise ValueError("対象版・手順・入力・期待結果が異なる。再試験を行う")
    if digest(root / run.result["log"]) != run.result["hash"]:
        raise ValueError("当初の証跡を検証できない")
    data = {
        "at": now(),
        "outcome": args.outcome,
        "reason": required(args.reason, "原証跡による再判定の根拠"),
    }
    conn.execute("INSERT INTO test_reviews(run,data) VALUES (?,?)", (run.number, encoded(data)))
    return f"{run.name} 再判定 {args.outcome}（当初判定 {run.original}）"


def tables(phase, keys, attempts):
    runs, summary = [], []
    for key in keys:
        history = attempts.get((phase, key), [])
        initial = history[0].original if history else "未着手"
        last = history[-1] if history else None
        outcome = last.final if last else "未着手"
        kind = "未着手"
        for index, run in enumerate(history):
            kind = "初回" if index == 0 else "再試験"
            note = run.start["reason"]
            if run.result.get("drift"):
                note += f" 入力判定 {run.result['reported']}。{run.result['drift']}"
            for review in run.reviews:
                kind = "再判定"
                note += f" 再判定 {review['at']} {review['outcome']}（{review['reason']}）"
            fields = run.start["case"]["fields"]
            conditions = " ／ ".join(
                f"{header}={value}" for header, value in fields.items() if header != CASE
            )
            runs.append(
                [
                    run.name,
                    key,
                    run.start["at"],
                    run.start["version"],
                    conditions,
                    run.start["operation"],
                    run.result.get("actual", "実行中"),
                    run.original,
                    run.result.get("log", "実行中"),
                    note.strip() or "該当なし（初回試行）",
                ]
            )
        summary.append(
            [
                key,
                history[0].name if history else "未着手",
                initial,
                last.name if last else "未着手",
                outcome,
                kind,
            ]
        )
    return {
        RUN_SECTION: (RUN_COLUMNS, runs),
        SUMMARY_SECTION: (SUMMARY_COLUMNS, summary),
        COUNT_SECTION: (COUNT_COLUMNS, counts(((phase, key) for key in keys), attempts)),
    }


def counts(keys, attempts):
    first, final = Counter(), Counter()
    for key in keys:
        history = attempts.get(key, [])
        first[history[0].original if history else "未着手"] += 1
        final[history[-1].final if history else "未着手"] += 1
    return [
        [label, str(sum(values.values())), *(str(values[s]) for s in COUNT_COLUMNS[2:])]
        for label, values in (("初回", first), ("最終", final))
    ]


def count_lines(keys, attempts):
    return [
        " ".join([row[0], *(f"{key} {value}" for key, value in zip(COUNT_COLUMNS[1:], row[1:]))])
        for row in counts(keys, attempts)
    ]


def cell(value):
    return "<br>".join(str(value).splitlines()).replace("|", "&#124;")


def markdown(title, headers, rows):
    def line(values):
        return "| " + " | ".join(cell(v) for v in values) + " |"

    return "\n".join(
        [
            f"## {title}",
            "",
            line(headers),
            line(["---"] * len(headers)),
            *(line(row) for row in rows),
        ]
    )


def report(plans, attempts, selected=None):
    blocks = []
    included = [
        (phase, key)
        for phase, plan in plans.items()
        if selected in (None, phase)
        for key in plan["cases"]
    ]
    if included:
        blocks.extend(["工程合計" if selected else "作業全体", *count_lines(included, attempts)])
    for phase, plan in plans.items():
        if selected and phase != selected:
            continue
        for path in dict.fromkeys(case["document"] for case in plan["cases"].values()):
            keys = [key for key, case in plan["cases"].items() if case["document"] == path]
            blocks.append(f"# {phase}  {path}")
            blocks.extend(
                markdown(title, headers, rows)
                for title, (headers, rows) in tables(phase, keys, attempts).items()
            )
    return "\n\n".join(blocks) if blocks else "初回記録なし"


def completion_issues(root, phase, plan, attempts, documents):
    if not plan:
        return ["初回記録なし。試験前に test-plan で計画し、各試行を記録する"]
    issues = []
    planned = plan["cases"]
    seen = []
    for document in documents:
        cases = {item_id(row[CASE]): row for row in section_rows(document, CASE_SECTION)}
        seen.extend(cases)
        for key, row in cases.items():
            history = attempts.get((phase, key), [])
            if not history or history[-1].final not in TEST_OUTCOMES[:2]:
                issues.append(f"{key} の最終判定が未確定")
            elif row != history[-1].start["case"]["fields"]:
                issues.append(f"{key} の提出条件が最終試行時と異なる")
        for title, (headers, rows) in tables(phase, cases, attempts).items():
            submitted = [
                tuple(row.get(h, "") for h in headers) for row in section_rows(document, title)
            ]
            if Counter(submitted) != Counter(tuple(cell(v) for v in row) for row in rows):
                issues.append(f"{title} が試験台帳と一致しない。test-report の記録を照合する")
    if Counter(seen) != Counter(planned.keys()):
        issues.append("提出したケースが初回に登録した計画と一致しない")
    for key in planned:
        for run in attempts.get((phase, key), []):
            if run.result:
                try:
                    unchanged = digest(root / run.result["log"]) == run.result["hash"]
                except OSError:
                    unchanged = False
                if not unchanged:
                    issues.append(f"{run.name} の保存済み証跡を確認できない")
    return issues
