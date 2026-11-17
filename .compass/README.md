# Compass の参照先

依頼の着手から完了報告までの手順は [ワークフロー](workflow/README.md) に従う。ここで各段階の参照先と適用条件を確認する。参照パスは `.compass/` が基準。

| タイミング | 参照先 |
| --- | --- |
| 着手前 | [作業前 Skill](workflow/preflight/SKILL.md) |
| 作業・検証 | [ワークフロー](workflow/README.md)、[工程 Skill と成果物テンプレート](workflow/phase/README.md)、[技術ガイド](guide/README.md) |
| 全工程で人間に確認するとき、回答を受けたとき、決定を反映したとき | [課題管理 Skill](workflow/issue-tracking/SKILL.md) |
| 結果報告 | [作業後 Skill](workflow/postflight/SKILL.md) |
| 文書の記録・確認・Excel出力 | [共通の文書手順](documents/README.md) |
| 課題台帳 | [課題管理表](records/issue-log.md) |

## 適用条件

作業前の４項目、依頼・既存仕様、変更の影響を以下の条件と照合し、該当する参照先をすべて選ぶ。

| 種別 | 適用条件 | 参照先 |
| --- | --- | --- |
| 工程 Skill | 開発区分と作業範囲を照合し、今回含まれる工程の Skill を選ぶ。 | [工程別の参照先](workflow/phase/README.md) |
| 技術ガイド | 今回の作業に Python が関係する。 | [Python ガイド](guide/python/README.md)（本文作成予定） |
| 確認ルール | 既存データの構造、制約または移行に影響する。 | データ移行（作成予定） |
| 確認ルール | 公開 API の応答、入力、その他の契約に影響する。 | API 互換性（作成予定） |

参照先の本文が未整備の場合は、導入先の既存指示・仕様・検証手順を参照する。空ファイルや案内のみの README は本文未整備として扱う。

工程 Skill には適用条件、実施手順、必須項目、完了条件を記載する。必須欄と補足欄の記録方法は [共通の記録・確認ルール](documents/document-records.md) を参照する。工程ごとの確認基準と記入用テンプレートは、各 Skill の `references/` を参照する。確認ルールには適用条件、成果物または確認項目、完了条件を記載する。参照先の変更はこの README に、工程と Skill の対応は [工程の README](workflow/phase/README.md) に反映する。
