---
name: preflight
description: Use before starting Rule Driven Compass work (作業前). Classifies the target, development mode, phase range, and relevant technologies and displays the four-line preflight.
---

# Compass の着手前ルール

分類・判定基準の設計、既存案の要否の相談では、４項目の確定前に[目的確認 Skill](../clarify-purpose/SKILL.md) を読む。分類名や手段だけが示された依頼は、分類結果で何を決めるのかを確認する。４項目の確定に人間の回答が必要な場合は、質問時に[課題管理 Skill](../issue-tracking/SKILL.md) で記録し、回答後に４項目を提示する。目的がすでに明確なら、そのまま４項目を提示する。

依頼、既存のプロジェクト指示、技術を示す設定ファイルを必要な範囲で読み取り、着手に必要な事実を確認する。依頼された作業を始める前に、次の４項目をこの順序で１行ずつ、１つの `text` コードブロックで提示する。値は今回の依頼に合わせる。

```text
作業対象　導入先プロジェクトの作業
開発区分　本番
作業範囲　実装〜単体試験
作業内容　GitHub、Python、SQLite、pytest
```

[４項目の判定基準](references/classification.md) で、開発区分、担当する工程、関連する技術・確認ルールを照合する。
