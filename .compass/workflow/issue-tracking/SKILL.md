---
name: issue-tracking
description: Use for human confirmations and decisions in any RDC phase (課題管理). Records confirmation details, answers, rationale, implementation status, and evidence in one issue log.
---

# 人間への確認と課題管理

作業範囲、仕様、設計、検証、リリースについて人間に確認した事項を、全工程で同じ課題管理表に記録する。更新先は対象プロジェクトのルートから `.compass/records/issue-log.md`。質問、回答・決定、反映確認を同じ課題 ID で追跡する。

## 成果物テンプレート

[課題管理表テンプレート](references/template.md) を使う。課題管理表が未作成の場合は、必要に応じて `.compass/records/` を作成し、テンプレートを `.compass/records/issue-log.md` にコピーして最初の課題を記録する。既存の台帳は既存行の課題 ID を使って追記・更新する。必須項目は状態に応じて確認した内容を記録する。補足欄と回答待ちの欄にも適用結果と理由を記録する。

## 実施手順

1. **確認時。** 関連する既存行を確認する。新規の確認事項には重複しない `Q-001` 形式の課題 ID を付け、発生フェーズ、確認事項、確認先と確認日を記録する。状態は「確認待ち」にする。
2. **回答時。** 同じ課題 ID の行に回答、確定した決定、回答・決定日、判断根拠や参照先を記録する。判断が保留の場合は「確認待ち」、決定が確定して反映が残る場合は「対応待ち」にする。
3. **反映時。** 反映先の文書・コード・試験の項目 ID、確認した結果と証跡を同じ行に追記する。必要な反映をすべて確認した場合、または追加対応が不要と決まった場合に「完了」にする。

記録する欄と完了条件は[記録項目と状態の判定](references/recording.md)で確認する。影響範囲や今後の対応予定など、補足欄も確認結果を記録する。

作業後の報告では、確認待ちの課題を「未確認事項」、対応待ちの課題を「作業結果」の残作業に課題 ID 付きで示す。

## Excel出力

Excelで共有・確認するときは、[共通のExcel出力手順](../../documents/excel-export.md)に従い、記入済みの `.compass/records/issue-log.md` を入力に指定する。
