# 公式仕様の確認先

調査日: 2026-09-23

この配布構成は、次の公式仕様を参照しています。

## Claude Code

- [プラグイン作成](https://code.claude.com/docs/en/plugins): plugin manifest、Skillsの配置、スキルがタスク文脈から選択される動作。
- [マーケットプレイス作成](https://code.claude.com/docs/en/plugin-marketplaces): marketplace.json、GitHub配布、同一リポジトリ内の ./plugins/compass 相対source。
- [プラグインの追加と管理](https://code.claude.com/docs/en/discover-plugins): marketplace add、install、scope、list、update、disable、uninstall、reload。
- [Community marketplace申請](https://code.claude.com/docs/en/plugins): Community marketplaceには審査フォームがあり、curated official marketplaceへの直接申請制度とは異なる。

Claude Code用manifestは plugins/compass/.claude-plugin/plugin.json、marketplaceはルートの .claude-plugin/marketplace.json です。

## Codex

- [プラグインのパッケージ](https://developers.openai.com/plugins/build/plugins): portable plugin.json、skills/<name>/SKILL.md、.agents/plugins/marketplace.json、Codex marketplace CLI。
- [公開プラグインの申請](https://developers.openai.com/plugins/deploy/submission): 公開ディレクトリの本人確認、権限、掲載情報、テストケース、申請手順。
- [Claude Code pluginのOpenAI向け提出](https://developers.openai.com/plugins/guides/submit-claude-plugin): Claude形式からOpenAI形式への変換要件。

Codex用manifestは plugins/compass/plugin.json、Codex marketplaceはルートの .agents/plugins/marketplace.json です。

## 差分の扱い

二つの製品は別々のmarketplace catalogを必要としますが、Skillsと共有ルールは plugins/compass/skills/ の一組だけです。Codexの公開ディレクトリとGitHub Marketplace追加は別の配布経路です。Claude Community marketplaceとAnthropic curated official marketplaceも別の掲載区分です。
