---
name: preflight
description: Use before starting Rule Driven Compass work (作業前). Classifies the target, development mode, phase range, and relevant technologies and displays the four-line preflight.
---

# Compass の着手前ルール

依頼、既存のプロジェクト指示、技術を示す設定ファイルを必要な範囲で読み取り、着手に必要な事実を確認する。依頼された作業を始める前に、次の４項目をこの順序で１行ずつ、１つの `text` コードブロックで提示する。値は今回の依頼に合わせる。

```text
作業対象　導入先プロジェクトの作業
開発区分　本番
作業範囲　実装〜単体試験
作業内容　GitHub、Python、SQLite、pytest
```

[４項目の判定基準](references/classification.md) で、開発区分、担当する工程、関連する技術・確認ルールを照合する。
