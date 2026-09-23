# Rule Driven Compass

Compassは、依頼を分類して必要なルールだけを選び、設計、実装、検証、レビューまで案内する共通ワークフローです。Claude CodeとCodexで同じスキル本文を使います。

各製品へのインストールは一度、プロジェクトごとの初期化は一度です。その後は普段どおり「機能を追加して」「バグを直して」と依頼できます。長い指示文やルール一式を毎回貼る必要はありません。

## できること

- repository、branch policy、作業モード、開発段階、作業種別、技術スタックを依頼に合わせて分類
- 関係するルールとstackメモだけを選択
- 既存の仕様、Issue、README、package scriptを確認してから変更
- 実装、テスト、レビュー、引き渡しを支援
- 実行した確認と未実行の確認を分けて報告
- 既存の指示ファイル、設定、未コミット変更、Git hookを保護

CompassはSkillsと文書だけのプラグインです。MCP接続、実行hook、外部通信、認証情報は含みません。

## 必要なもの

- Windows 10/11を主な対象にしています。
- GitをPATHから実行できること。
- Claude Code、またはCodex CLI / Codexデスクトップ。
- ClaudeまたはOpenAIアカウントの通常認証。Compass専用API keyやGitHub tokenは不要です。公開リポジトリの読み取りにGitHub認証も不要です。
- Node.js、Python、PowerShellはインストールや利用に不要です。保守用検査スクリプトはWindows PowerShell 5.1以降で実行できます。

最低バージョンは固定していません。プラグインとSkillsに対応する各製品の現行版を使ってください。Codex CLIは0.144.1で検証します。Claude Code CLIは検証環境になく、実機導入は未検証です。詳細は docs/compatibility.md を参照してください。

## Claude Codeへインストール

Claude Codeの入力欄で、マーケットプレイスを追加し、Compassを自分用にインストールします。

~~~text
/plugin marketplace add Eirene-Bel/RuleDrivenCompass
/plugin install compass@rule-driven-compass
~~~

インストール画面で User scope を選びます。反映を求められたら /reload-plugins を実行するか、新しいセッションを始めてください。CLIから操作する場合は、マーケットプレイスを追加したあと次を実行できます。

~~~powershell
claude plugin install compass@rule-driven-compass --scope user
~~~

Claude Codeのサインインは通常どおり必要です。

## Codexへインストール

~~~powershell
codex plugin marketplace add Eirene-Bel/RuleDrivenCompass
codex plugin add compass@rule-driven-compass
~~~

インストール後は新しいCodexセッションを始めます。Codexのログインは通常どおり必要です。

## プロジェクトで一度だけ初期化

Compassを使いたいプロジェクトのルートで、Claude Codeでは次を実行します。

~~~text
/compass:compass-setup
~~~

Codexでは次を実行します。

~~~text
$compass-setup
~~~

または、以下の依頼文をそのまま送ってください。

~~~text
このプロジェクトでCompassを使えるように初期化してください。既存のAGENTS.md、CLAUDE.md、設定、Git hookを保護し、技術スタックと既存の検証コマンドを確認して、必要最小限だけ設定してください。
~~~

初期化スキルは既存のAGENTS.mdとCLAUDE.mdを保持し、識別コメントで囲んだCompass案内だけを追記します。既存の .compass/project-profile.json があればそれを使い、新たなprofileが必要な場合だけ .compass/plugin-config.json を作ります。stackや検証コマンドは確認できたものだけ記録します。

製品設定、Git hook、CI、未コミット変更には触れません。共有ルールはプラグインに置き、プロジェクトには複製しません。プロジェクト設定と作業記録はプロジェクト側に残るため、プラグイン更新では失われません。

## 日常の利用例

~~~text
このAPIの入力検証で発生しているバグを直してください。
~~~

~~~text
設定画面に通知頻度の選択肢を追加してください。既存のUI方針を確認し、必要なテストも実行してください。
~~~

~~~text
READMEのインストール手順を現行のpackage scriptに合わせて更新してください。
~~~

~~~text
この差分をCompassの観点でレビューして、未確認の受け入れ条件と追加確認を教えてください。
~~~

明示的に呼び出す場合は、Claude Codeで /compass:compass-workflow、Codexで $compass-workflow を指定します。

## 読み込まれたことを確認

Claude Codeでは次を実行します。

~~~text
/plugin list
/help
~~~

一覧にCompassがあり、Skillsに /compass:compass-setup と /compass:compass-workflow が表示されることを確認します。対象プロジェクトのAGENTS.mdまたはCLAUDE.mdに COMPASS-PLUGIN:START と COMPASS-PLUGIN:END があることも確認してください。

Codexでは次を実行します。

~~~powershell
codex plugin list
~~~

Compassが表示され、Skills一覧または $compass-setup の呼び出し候補に出ることを確認します。

## 更新

Claude Codeではマーケットプレイスを更新します。

~~~text
/plugin marketplace update rule-driven-compass
~~~

サードパーティMarketplaceの自動更新は初期状態で無効の場合があります。自動更新したい場合は /plugin を開き、Marketplaces から rule-driven-compass を選び、Enable auto-update を有効にします。手動更新後に通知が出たら /reload-plugins を実行します。

Codex CLIではGitマーケットプレイスを更新します。

~~~powershell
codex plugin marketplace upgrade rule-driven-compass
~~~

新しいCodexセッションを始め、codex plugin list で状態を確認します。共有プラグイン本体だけが更新され、プロジェクトのprofileや作業記録は変更されません。

## 無効化とアンインストール

一時停止はClaude Codeで /plugin disable compass@rule-driven-compass を実行します。CodexのPlugins DirectoryでCompassを無効にするか、WindowsのPowerShellからユーザー設定を開き、次の項目を追加または更新します。既存の設定を消さずにマージしてください。

~~~powershell
notepad "$env:USERPROFILE\.codex\config.toml"
~~~

~~~toml
[plugins."compass@rule-driven-compass"]
enabled = false
~~~

再び使うときは enabled を true に戻します。特定のプロジェクトだけで無効にする場合は、そのプロジェクトの .codex/config.toml に同じ設定を置きます。CodexのプラグインCLIにはremoveもあり、これは無効化ではなくアンインストールです。

プロジェクト内の案内も外したい場合は、プラグイン削除の前に、Claude Codeで /compass:compass-remove-project、Codexで $compass-remove-project を実行します。管理ブロックだけを取り除き、profile、作業記録、設定、hookは残します。残った内容は利用者が確認して整理してください。

マーケットプレイスごと削除する場合、Claude Codeでは /plugin uninstall compass@rule-driven-compass と /plugin marketplace remove rule-driven-compass を実行します。Codex CLIでは次を実行します。

~~~powershell
codex plugin remove compass@rule-driven-compass
codex plugin marketplace remove rule-driven-compass
~~~

## よくある問題

- **marketplace addに失敗**: GitがPATHから実行できるか、GitHubへの接続が許可されているか確認します。
- **Claude Codeでpluginやskillが見つからない**: /plugin marketplace list を確認し、/plugin marketplace update rule-driven-compass の後に /plugin install compass@rule-driven-compass を実行します。反映されない時は /reload-plugins または新しいセッションを使います。
- **Codexでpluginコマンドがない**: Codex CLIをプラグイン対応の現行版へ更新し、codex plugin --help で操作を確認します。
- **通常の依頼でCompassが選ばれない**: 対象プロジェクトに管理ブロックがあるか確認し、新しいセッションを始めます。必要なら $compass-workflow または /compass:compass-workflow を明示します。
- **管理マーカーが壊れている**: 自動で書き換えず、Compass部分を確認します。マーカー外の文章は保持してください。
- **既存設定やhookの動作に問題**: Compass初期化はそれらを変更しません。Git diffを確認して別の変更を切り分けます。

## 配布と公開ストア

このGitHubリポジトリをマーケットプレイスとして追加する方法は、個人・チーム向けの直接配布です。Claude Community marketplaceやOpenAI Plugin Directoryへの掲載申請とは別です。下書きと手順は docs/store-submission.md にあります。

元テンプレートにはLICENSEファイルとGitHubライセンス情報がありませんでした。そのため、このリポジトリにもライセンスを推測で付けていません。詳細は docs/source-and-license.md を参照してください。互換性と未検証項目は docs/compatibility.md に記載しています。

パッケージを手元で検査するには、PowerShellで scripts/validate-package.ps1 を実行します。
