---
name: requirements-definition
description: Use when the RDC work scope includes requirements definition (要件定義) for production software or a proof of concept. Records requirements, constraints, and testable acceptance or success criteria.
---

# 要件定義

作業範囲に「要件定義」が含まれるときに適用する。

## 成果物テンプレート

[要件定義書テンプレート](references/template.md) を使って、担当範囲の成果物を作成・更新し、記録項目を確認する。レビューでは対象の成果物をテンプレートの項目と照合する。

テンプレートの必須欄に確認した内容または根拠の参照先を記録する。補足欄にも内容または適用結果と理由を記録する。完了前は[共通の記録・確認ルール](../../../documents/document-records.md)に沿って全項目を確認する。

## 実施手順

1. 依頼と既存の要件を照合し、利用者、目的、変更する範囲を特定する。
2. 必要な振る舞いと制約を記載する。利用者や外部システムの役割・機能範囲を共有する場合は、ユースケースの記述や図を使う。
3. 本番では総合試験で判定できる受け入れ条件を、試作では検証する仮説と成功条件を記載する。各条件を項目名または ID で参照できるようにする。

## 必須項目

- 利用者、目的、対象範囲
- 必要な振る舞いと関係する制約
- 対象の要件を参照できる項目名または ID
- 本番では受け入れ条件。試作では検証する仮説と成功条件

## 詳細な確認

品質要件、ユースケース、PoCの判定条件、未確定の要求を整理するときは、[要件定義の確認基準](references/checkpoints.md) を参照する。

## 完了条件

今回の範囲と必要な振る舞いが明確で、総合試験が参照する受け入れ条件、または試作の成功条件を特定できる。
