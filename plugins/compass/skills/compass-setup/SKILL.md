---
name: compass-setup
description: Use when the user asks to install, initialize, or update Rule Driven Compass (RDC) in the current project. Deploys its shared workflow, guides, templates, and scripts for Codex and Claude Code.
---

# RDCのセットアップ

1. 指定された導入先のプロジェクトルートを確認する。導入先で、このSkillに同梱した [セットアップスクリプト](scripts/setup.py) を実行する。スクリプトのパスは、現在読み込んでいるこの `SKILL.md` のフォルダを基準に解決し、空白を含むパスは引用符で囲む。

   ```text
   uv run "<このSkillのフォルダ>/scripts/setup.py" --project "."
   ```

   Python 3.10以上が利用できる環境では、同じスクリプトをPythonで直接実行できる。既存の共通ファイルに差分がある場合は、表示されたファイルと内容を確認する。RDCの配布版への更新を依頼された場合は `--update` を指定する。

2. 導入先の `.compass/README.md` と `AGENTS.md` のRDC参照を確認し、配置先と結果を報告する。通常作業では、導入先の `.compass/README.md` が指定するワークフローに従う。
