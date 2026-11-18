---
name: detailed-design
description: Use when the RDC work scope includes detailed design (詳細設計) for component processing, inputs and outputs, data, state, or errors. Produces internal specifications for implementation and unit testing.
---

# 詳細設計

作業範囲に「詳細設計」が含まれるときに適用する。

## 成果物テンプレート

[詳細設計書テンプレート](references/template.md) を使って、担当範囲の成果物を作成・更新し、記録項目を確認する。レビューでは対象の成果物をテンプレートの項目と照合する。

テンプレートの必須欄に確認した内容または根拠の参照先を記録する。補足欄にも内容または適用結果と理由を記録する。完了前は[共通の記録・確認ルール](../../../documents/document-records.md)に沿って全項目を確認する。

## 実施手順

1. 基本設計の担当範囲と要素間の契約を確認し、詳細を定義する部品を特定する。
2. 部品に入力が与えられたときの処理、データの扱い、出力、境界・異常時の挙動を決める。
3. 詳細設計書の該当箇所を作成・更新する。単体試験で確認する入出力や異常時の条件を項目名または ID で参照できるようにする。

## 必須項目

- 対応する基本設計と対象の部品
- 前提・入力、処理、使うデータ、出力
- 今回の変更に関係する境界・異常時の挙動

## 詳細な確認

処理分岐、データ構造、状態遷移、異常時の挙動を検討するときは、[詳細設計の確認基準](references/checkpoints.md) を参照する。

## 完了条件

実装と単体試験が同じ前提・入力・期待結果を使える詳細設計書がある。
