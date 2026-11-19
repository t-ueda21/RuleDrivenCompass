# Rule Driven Compass

Rule Driven Compass（RDC）は、CodexとClaude Codeで同じ開発工程・検証・報告手順を利用するためのプラグイン。対象プロジェクトに `.compass/` を配置し、共通の対話・判断原則と、作業前・9工程・画面試作・目的確認・課題管理・作業後の14 Skill、技術ガイド、確認基準、テンプレート、コスト試算表、フェーズゲート、Excel出力を提供する。

## インストール

マーケットプレイス名は `rule-driven-compass`、プラグイン名は `compass`。GitHubリポジトリを各クライアントに登録してインストールする。

| 環境 | マーケットプレイスの登録 | プラグインのインストール |
| --- | --- | --- |
| Codex | `codex plugin marketplace add t-ueda21/RuleDrivenCompass --ref main` | `codex plugin add compass@rule-driven-compass` |
| Claude Code | `claude plugin marketplace add t-ueda21/RuleDrivenCompass` | `claude plugin install compass@rule-driven-compass` |

ローカルのチェックアウトを登録する場合は、リポジトリのルートでCodexなら `codex plugin marketplace add .`、Claude Codeなら `claude plugin marketplace add ./` を実行する。

## プロジェクトでの利用

1. 導入先のプロジェクトを開き、Codexでは `$compass:compass-setup`、Claude Codeでは `/compass:compass-setup` を実行する。セットアップにはPython 3.10以上または `uv` を使う。
2. 通常の依頼では `AGENTS.md` から `.compass/README.md` を参照する。Claude Codeでは既存のプロジェクト指示ファイルが優先される場合がある。セットアップは対象プロジェクトの既存の `CLAUDE.md`、`.claude/CLAUDE.md`、`CLAUDE.local.md` の順で最初の1ファイルに、必要に応じて `AGENTS.md` の参照を追記する。上位ディレクトリの指示やクライアント設定を使う場合も、`/compass:compass-workflow` からRDCを直接利用できる。[Claude Codeの指示ファイル仕様](https://code.claude.com/docs/en/memory#when-claude-code-reads-agentsmd)
3. 課題台帳は最初の確認時、工程判定の台帳は最初の工程着手時に、導入先の `.compass/records/` に生成する。設計書・試験書・課題管理表などのExcel成果物は導入先の **`books/`** に保存し、初回出力時にフォルダを作成する。実行例は導入先の `.compass/documents/README.md` から参照する。

再セットアップは既存の案件記録とプロジェクト指示を保持する。共通ファイルの同じパスに異なる内容がある場合は差分を確認し、配布版へ更新するときにセットアップスクリプトへ `--update` を指定する。

単体・結合・総合試験では、試験計画を固定して初回の操作から記録し、全ケースを一巡した後に修正・再試験する。試験書と完了報告には、初回と最終の件数、手順エラー・実施不能・再判定の根拠も表示する。[試験記録の手順](plugins/compass/skills/compass-setup/assets/compass/documents/test-history.md)

## 配布版の作成

配布元リポジトリの `.compass/` で共通ファイルを管理する。新しいガイドやテンプレートも同じ構成で同梱する。案件記録の `records/` からは利用案内の `README.md` を収録する。共通ファイルの変更時は以下を実行する。

```sh
uv run scripts/package_compass.py
uv run scripts/package_compass.py --check
```

1つ目のコマンドでプラグインの `plugins/compass/skills/compass-setup/assets/compass/` に共通ファイルを同期し、2つ目で配布元との一致を確認する。配布元と同期先を同じコミットに含める。
