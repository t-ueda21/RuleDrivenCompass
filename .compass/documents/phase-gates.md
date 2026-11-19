# フェーズゲート

工程を完了する依頼では、着手時に今回の作業範囲と入力を登録し、完了時に必須項目と証跡を照合する。今回の範囲に含まれる前工程がすべて通過していれば、次の工程に着手できる。

| 判定 | 条件 | 次の操作 |
| --- | --- | --- |
| 着手可 | 開発区分・作業範囲に合い、範囲内の前工程が現在の版で通過している。試験は対象 ID とその入力資料を確認済み | 対象の工程 Skill に従って作業する |
| 通過 | 必須欄の具体的な記録、該当する契約の確定、試験対象の追跡、証跡と工程 Skill の完了条件を確認済み | 今回の範囲に次の工程があれば、次の工程の着手判定を実行する |
| 保留 | 必須項目の不足、試験結果の欠落、完了条件の確認待ち、または確認済みの版に変更がある | 表示された不足を解消し、対象の工程を再判定する |

## 着手

プロジェクトルートで実行する。`--work-id` には、今回の依頼中に使う一意の作業 ID を指定する。`--mode` は本番なら `production`、試作なら `poc`、開発案件から独立した調査・リリースなら `independent`。`--scope` には、[工程一覧](../workflow/phase/README.md)の順で、今回の作業範囲に含まれる工程 ID をカンマで連結して指定する。工程 ID は一覧の各 Skill のフォルダ名。`--phase` には今回着手する工程 ID を指定する。

```powershell
uv run .compass/documents/scripts/check_phase_gate.py start --work-id change-42 --mode production --scope basic-design,integration-testing --phase basic-design
```

試験では、今回検証する ID を上流資料から特定し、`--target-id` を対象ごとに指定する。上流の工程が今回の作業範囲にある場合は、その工程が通過した文書を照合に使用する。範囲外の場合は、採用した既存資料を `--input-evidence` に指定する。

| 試験 | 対象 ID を特定する資料 |
| --- | --- |
| 単体試験 | 詳細設計の部品仕様 |
| 結合試験 | 基本設計の要素間の契約 |
| 総合試験 | 本番は要件定義の受け入れ条件、試作は仮説と成功条件 |

結合試験だけを担当する場合の例。

```powershell
uv run .compass/documents/scripts/check_phase_gate.py start --work-id test-42 --mode production --scope integration-testing --phase integration-testing --target-id IF-04 --target-id IF-05 --input-evidence deliverables/basic-design.md
```

## 完了判定

単体・結合・総合試験は、工程着手後、最初の操作の前に[試験の初回記録](test-history.md)を開始する。試験書の初回・最終判定と内訳は台帳と照合する。初回一巡が揃ってから修正・再試験し、証跡の読み直しは同じ実行 ID に根拠を追記する。

1. [共通の記録・確認ルール](document-records.md)で文書を確認する。当該の工程テンプレートにある「必須」と、開発区分に該当する「本番必須」「試作必須」がゲートの対象となる。「補足」「該当時」も共通ルールに従って記録し、適用される完了条件に関係する場合はその結果も確認する。
2. 工程 Skill の完了条件に照らし、記載内容、証跡の参照先、対象版、対応する ID を確認する。条件を満たす場合は `--review confirmed`、確認・対応が残る場合は `--review pending` を指定する。`--note` に判定根拠や保留理由、関連する課題 ID を記録できる。人間への確認・決定は[課題管理 Skill](../workflow/issue-tracking/SKILL.md)に従う。
3. `finish` に確認した Markdown 文書を `--document`、根拠となる文書・コード・ログなどの確認済みファイルを `--evidence` で指定する。それぞれ複数回指定できる。同じ文書に証跡を記録している場合は、その文書を両方に指定できる。指定書式の成果物を使う場合は、テンプレートの該当欄にその成果物の対応箇所と根拠を記録した Markdown を照合に使う。

```powershell
uv run .compass/documents/scripts/check_phase_gate.py finish `
    --work-id test-42 --phase integration-testing `
    --document deliverables/integration-testing.md `
    --evidence tests/test_inventory_import.py `
    --evidence tests/fixtures/inventory_import/valid.csv `
    --evidence tests/fixtures/inventory_import/negative_quantity.csv `
    --evidence deliverables/integration-run.log --review confirmed
```

試験文書には、欄の先頭に ID を記録する。項目名を併記する場合は `IF-05 在庫更新` のように空白で続ける。完了判定の対応欄には `IT-05 / RUN-000005` のようにケース ID と最終の実行 ID を記録する。登録した対象 ID ごとに、ケース、その初回から最終までの実行結果、対応 ID を記載した完了判定を確認する。

試験のレビューでは、ケース ID ごとに、使用した入力と初期状態、仕様に基づく期待結果、実行 ID・実際の結果を照合する。`--evidence` に使用したデータファイルと実行ログを指定する。入力がテストコード内にある場合はそのコードを、生成データの場合は生成処理と再現条件を記録したファイルを使える。手動試験では入力値・操作・観測結果を記録した試験書も証跡として使える。必須の試験が未実行、または使用データと結果の対応を確認できない場合は、理由を記録して `--review pending` で保留とする。

## 再判定と記録

- 判定・理由・確認したファイルの場所と内容のハッシュは、プロジェクトルートの `.compass/records/phase-gates.sqlite3` に作業 ID・工程ごとに記録する。
- 文書、入力資料、証跡の変更や消失を検出した場合は再確認する。入力が更新された工程は `start` で登録し直し、文書と証跡の確認後に `finish` を実行する。前工程を再着手した場合や前工程の判定・成果物の版が更新された場合は、着手済みの後工程も入力を再確認して順に再着手する。
- 保留理由を修正した場合は、同じ作業 ID のまま `finish` を再実行できる。登録した開発区分・作業範囲・対象 ID 自体が変わる場合は、新しい作業 ID で登録する。
- `start` と `finish` は保留時に終了コード `1` を返す。`status` は現在の版での判定、理由、対象 ID と確認資料を表示する。

```powershell
uv run .compass/documents/scripts/check_phase_gate.py status --work-id test-42
```
