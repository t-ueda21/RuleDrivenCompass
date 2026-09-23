# Claude Code と Codex の対応

## 共通部分

Claude Code と Codex は、同じ GitHub リポジトリ内の同じプラグインパッケージと同じ compass-workflow / compass-setup / compass-remove-project スキルを読みます。作業分類、参照するルール、プロジェクト初期化、検証方針は共有ファイルが正本です。

Claude 用マーケットプレイスと Codex 用マーケットプレイスは登録ファイルだけを分け、どちらも plugins/compass を参照します。ルールを製品ごとに複製しません。

## 自動適用の違い

- Claude Code のプラグインスキルは、依頼内容とスキルの説明に応じてモデルが選びます。初期設定後は CLAUDE.md の Compass 管理ブロックが通常依頼にも共有スキルの利用を指示します。
- Codex では、プラグインを入れるとスキルが利用可能になり、AGENTS.md の Compass 管理ブロックが通常依頼でそのスキルを使うよう指示します。スキルを選ぶかはモデルの判断です。
- どちらもモデルの指示理解に基づくため、OSレベルの強制や100%の自動適用を保証する仕組みではありません。選択されない場合は、Claude Code では /compass:compass-workflow、Codex では $compass-workflow を明示してください。

## Hook とプロジェクト設定

この配布版はhookを持ちません。元テンプレートのGit hook、Claude Code PreToolUse設定、CI、生成スクリプトは移植していません。両製品で同じhook実行や同じ強制力を作ることを避け、プロジェクトのAGENTS.md／CLAUDE.mdとスキルで作業手順を適用します。既存のhookや設定は初期化時にも更新時にも変更しません。

プロジェクト固有の設定は .compass/plugin-config.json、元テンプレート由来の .compass/project-profile.json が既にある場合はそちら、作業記録はプロジェクトの docs/compass/work または既存の指定場所に残します。これらは利用者が管理するプロジェクトファイルで、プラグイン更新対象ではありません。

## 対応状況

- Windows 10/11を主な対象にしています。
- Codex CLI 0.144.1で公開GitHub marketplaceの追加・導入を行い、0.1.0から0.1.1への更新、Skills読み込み、compass-setupとcompass-workflowの実会話呼び出し、両製品のプロジェクト入口とJSON設定の作成、無効化・削除を確認しました。呼び出し確認ではgpt-5.5を指定しました。この検証環境の既定gpt-6-astraモデルはCLIより新しいバージョンを要求したためです。CodexデスクトップUIは未検証です。
- Claude Code のCLIは作業環境にないため、実機の追加・導入・更新は未検証です。Claude公式のmanifest、相対source、skill仕様に合わせた構成と静的検査を行い、利用者側の確認手順をREADMEに記載します。
- 最低バージョンは固定していません。プラグインとマーケットプレイスを扱える現行版を使ってください。

## 元テンプレートからの変更

このプラグインは、ルール選択・分類・開発ライフサイクル・検証の骨子を保ちながら、導入を軽くしています。多数のプロバイダー別CI、hooks、Git操作スクリプト、issueテンプレート、deployment / Docker雛形、個別プロジェクトのprofileや作業記録は含みません。main/develop/prototypeのブランチ構成や作業開始時の必須checkpoint commitも強制せず、導入先の既存ルールを引き継ぎます。
