---
name: integration-testing
description: Use when the RDC work scope includes integration testing (結合試験) of interactions between components, services, or databases against basic-design contracts. Records test conditions, evidence, and retests.
---

# 結合試験

作業範囲に「結合試験」が含まれるときに適用する。

## 成果物テンプレート

[結合試験書テンプレート](references/template.md) を使って、担当範囲の成果物を作成・更新し、記録項目を確認する。レビューでは対象の成果物をテンプレートの項目と照合する。

テンプレートの必須欄に確認した内容または根拠の参照先を記録する。補足欄にも内容または適用結果と理由を記録する。完了前は[共通の記録・確認ルール](../../../documents/document-records.md)に沿って全項目を確認する。

## 実施手順

1. 基本設計から、今回つなぐ要素と確認する契約を特定する。画面と API、API と DB など、同じシステム内の境界も対象にする。
2. 契約を確かめられる環境・データ・呼び出し条件を準備し、接続した状態で試験する。
3. 受け渡したデータと応答を期待結果に照らして判定する。代替した接続先がある場合は、実際に確認できた境界と未確認の境界を示す。

## 必須項目

- 試験ケースを参照できるケース ID・項目名。実行した場合は実行 ID、対象版・環境、証跡の参照先
- 対応する基本設計の契約の項目名または ID、接続した要素と境界
- 試験環境・データ、呼び出し条件、期待結果
- 試験手順またはコード、実行結果、合否、対象範囲の判定

## 詳細な確認

代替接続、タイムアウト・再試行、境界をまたぐ副作用、再試験を扱うときは、[結合試験の確認基準](references/checkpoints.md) を参照する。

## 完了条件

対象の接続で基本設計の契約を満たしたか判定できる。未実施の試験や未確認の境界は理由とともに報告する。
