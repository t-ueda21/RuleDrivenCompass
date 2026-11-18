# 工程 Skill と成果物テンプレート

[作業前 Skill](../preflight/SKILL.md) で提示した開発区分と作業範囲に従い、表から該当する工程の Skill とテンプレートを選ぶ。各 Skill に実施手順、必須項目、完了条件を記載している。各工程の確認基準とテンプレートは、各 Skill の `references/` にある。

表の順序は本番の９工程。試作では要件定義、実装、総合試験の Skill とテンプレートを共用する。連続する作業範囲は、作業前 Skill が示す開発区分ごとの工程順に沿って選ぶ。

| 工程 | Skill | 成果物テンプレート |
| --- | --- | --- |
| 調査 | [調査 Skill](investigation/SKILL.md) | [調査報告書](investigation/references/template.md) |
| 要件定義 | [要件定義 Skill](requirements-definition/SKILL.md) | [要件定義書](requirements-definition/references/template.md) |
| 基本設計 | [基本設計 Skill](basic-design/SKILL.md) | [基本設計書](basic-design/references/template.md) |
| 詳細設計 | [詳細設計 Skill](detailed-design/SKILL.md) | [詳細設計書](detailed-design/references/template.md) |
| 実装 | [実装 Skill](implementation/SKILL.md) | [実装記録](implementation/references/template.md) |
| 単体試験 | [単体試験 Skill](unit-testing/SKILL.md) | [単体試験書](unit-testing/references/template.md) |
| 結合試験 | [結合試験 Skill](integration-testing/SKILL.md) | [結合試験書](integration-testing/references/template.md) |
| 総合試験 | [総合試験 Skill](system-testing/SKILL.md) | [総合試験書](system-testing/references/template.md) |
| リリース | [リリース Skill](release/SKILL.md) | [リリース書](release/references/template.md) |

## テンプレートの利用

- 成果物を新規作成するときはテンプレートの見出しと欄を使う。既存の成果物があるときは該当箇所を更新する。導入先の指定書式があるときは、テンプレートの各項目を指定書式の対応箇所で記録・確認する。
- [共通の記録・確認ルール](../../documents/document-records.md) に沿って、必須項目と補足項目の両方を記録する。該当しない補足や開発区分には、その理由を記録する。既存の成果物・試験コード・ログは、該当項目の根拠として参照できる。
- レビューでは全項目の記入状況と、必須項目の根拠・対応する ID を照合する。不足があれば、項目と理由を報告する。人間への確認・決定は[課題管理 Skill](../issue-tracking/SKILL.md) に従って記録する。

Excelでは１フェーズにつき１ブックを作成する。「タイトル」「変更履歴」に続けて、関連する章をまとめたシートを配置する。[シート構成](../../documents/excel-sheets.md)と[出力手順](../../documents/excel-export.md)を参照する。
