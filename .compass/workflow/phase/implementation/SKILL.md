---
name: implementation
description: Use when the RDC work scope includes implementation (実装) of code, configuration, or other implementation deliverables. Records changes, applicable specifications, diffs, and verification results.
---

# 実装

作業範囲に「実装」が含まれるときに適用する。

## 成果物テンプレート

[実装記録テンプレート](references/template.md) を使って、担当範囲の成果物を作成・更新し、記録項目を確認する。レビューでは対象の成果物をテンプレートの項目と照合する。

テンプレートの必須欄に確認した内容または根拠の参照先を記録する。補足欄にも内容または適用結果と理由を記録する。完了前は[共通の記録・確認ルール](../../../documents/document-records.md)に沿って全項目を確認する。

## 実施手順

1. 依頼範囲、変更対象の仕様、既存コード・設定を確認する。試作では検証する仮説と対象範囲も確認する。
2. 既存の構成と指定された技術手順に沿って、依頼範囲の変更を実装する。
3. 差分と対象の要件・設計を照合する。作業範囲に含まれる試験や検証に、成果物と参照情報を引き渡す。

## 必須項目

- 対応する要件・設計、または試作の仮説
- 変更した成果物と変更内容
- 差分を確認できる参照先

## 詳細な確認

設計との差異、依存関係、データ・APIへの影響、引き渡しを記録するときは、[実装の確認基準](references/checkpoints.md) を参照する。

## 完了条件

依頼範囲の変更が成果物に反映され、対応する仕様と差分を確認できる。検証結果や未確認事項は実施した範囲に沿って報告する。
