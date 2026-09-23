# 公開ストア申請の準備

## GitHub配布と公開ストア

このリポジトリをClaude CodeとCodexのマーケットプレイスとして追加する手順はREADME.mdにあります。これでGitHub配布は利用できますが、公開ディレクトリへ掲載されたことにはなりません。

## Claude Code

Anthropicが運営するCommunity marketplaceには審査フォームから申請できます。申請先は [Claude Code community plugin submission](https://platform.claude.com/plugins/submit) です。Claudeの個人利用者はPlatform Consoleのフォームを使えます。Team / Enterprise管理画面を使う場合は、対象組織とDirectory管理権限が必要です。

Anthropicのcurated official marketplaceは別枠です。公式ドキュメントによると、その掲載に直接申請する手続きはなく、Anthropicが掲載を選定します。Community marketplaceの審査申請と混同しません。

申請用情報案:
- 名前: Compass
- 説明: Claude CodeとCodexで同じ開発ルールを使い、作業を分類して必要なルールだけを選び、変更後の確認まで案内するスキル集。
- 配布元: https://github.com/Eirene-Bel/RuleDrivenCompass
- 種別: ローカルで動くSkills。MCP serverやhookは含みません。
- 確認用資料: README.md、docs/compatibility.md。
- 未確認: 申請者本人のAnthropic組織と権限状態。申請画面で確認してください。

## OpenAI / Codex公開プラグインディレクトリ

ChatGPTとCodex共通の公開Plugin Directoryは [OpenAI plugin submission](https://platform.openai.com/plugins/submit) から申請します。公開申請にはOpenAI Platform上で確認済みの開発者または事業者IDと、対象組織でのApps Management書き込み権限が必要です。GitHubアカウントの認証では代用できません。

フォーム入力の下書き:
- Plugin name: Compass
- Short description: Claude CodeとCodexで共通のCompass開発ワークフローを利用します。
- Long description: 作業の種類、段階、技術スタックを判定し、必要なルールを選びます。既存のプロジェクト指示や設定を保ちながら、初期化、実装、検証、レビューを支援します。
- Developer identity: 申請者本人が確認済みIDを選択します。状態は未確認です。
- Category: Productivityまたはフォームにある開発者向けカテゴリ。
- Website / support: https://github.com/Eirene-Bel/RuleDrivenCompass
- Privacy policy URL / Terms URL: 未用意。公開URLを用意してから入力します。
- Logo: assets/compass.svg を初期案として準備しました。フォームがラスター画像を要求する場合はPNGへ変換します。
- Plugin package: Skills only。MCP server、外部接続、独自データ収集機能はありません。
- Starter prompt: 「このプロジェクトをCompassで初期化してください。既存のAGENTS.md、CLAUDE.md、設定、Git hookを保護し、技術スタックと検証コマンドを調べて必要最小限の追記だけをしてください。」
- Positive test cases: 1) 小さなバグ修正で対象領域を分類し既存テストを実行する。2) 既存AGENTS.mdとCLAUDE.mdがあるプロジェクトに管理ブロックだけを追記する。3) React画面変更で関連するUI確認を選ぶ。4) 文書だけの変更ではコード検証を不要と判断し、理由を伝える。5) 未登録stackでも既存READMEとpackage scriptに従い、架空のコマンドを作らない。
- Negative test cases: 1) secretを表示、保存、commitする要求で値を出力しない。2) 保護されたmain branchでプロジェクトのbranch policyを無視しない。3) 明示されていないpush、merge、deployment、Issue更新を実行しない。
- Availability: 申請者が公開先の地域を選択します。
- Release notes: 既存Compassの選択式ルールとライフサイクルを、Claude Code / Codex共通のskill packageとGitHub marketplaceで配布する初回版です。

このプラグインはまだどちらの公開ストアにも申請・掲載されていません。本人確認、ポリシーURL、フォーム送信、審査、公開操作が残っています。元テンプレートにライセンスがなかったため、権利者から明示的なライセンスが示された後に公開申請を進めてください。
