# Excel出力

[出力スクリプト](scripts/export_excel.py) は、UTF-8のMarkdown文書を１文書につき１ブックに変換する。**Excel成果物の保存先は導入先プロジェクト直下の `books/` に固定する。** 最初のExcel出力時にこのフォルダを作成する。

| シートの順序 | 内容 |
| --- | --- |
| １．タイトル | 文書名と、Markdownの文書管理の項目 |
| ２．変更履歴 | Markdownの変更履歴、改訂履歴または変更・レビュー履歴 |
| ３以降 | [文書別のシート構成](excel-sheets.md)に従って関連する章をまとめる。課題管理表は課題一覧 |

標準テンプレートの文書名を使うと、対応するシート構成で出力する。章の必須・補足区分はシート内の見出しに表示する。変更履歴は元のMarkdownに記録して再出力する。

表の濃色の行は列見出し、淡い黄色のセルは未記入欄。章見出しは必須と補足を色と文字で区別する。

以下の例はプロジェクトのルートで実行する。案件内では、実行位置から親をたどって最初に `.compass/README.md` がある場所をルートとする。案件外から起動したときは入力文書の属するRDCプロジェクトを使い、`--templates` 単独なら導入済みスクリプトの案件を使う。入力文書にも実行位置にもRDCの目次がない場合は、実行ディレクトリをルートとする。前提は `uv`。初回は必要なPythonとライブラリを `uv` が準備する。

## 全テンプレートを出力

各 Skill の `references/template.md` を参照し、フェーズ用９冊と課題管理表１冊を `books/` に出力する。同梱テンプレートのブックには `テンプレート_` を付ける。例えば `books/テンプレート_結合試験書.xlsx` になる。同梱テンプレートを個別に指定した場合も同じ命名を使う。

```powershell
uv run .compass/documents/scripts/export_excel.py --templates
```

## 記入済みの文書を出力

課題管理表を記入した後は、次のコマンドで `books/課題管理表.xlsx` を出力する。「課題一覧」には状態列のフィルターがあり、課題 ID・発生フェーズ・状態を固定して確認できる。

```powershell
uv run .compass/documents/scripts/export_excel.py .compass/records/issue-log.md
```

基本設計書、結合試験書、課題管理表を一括出力する例。記入済みのMarkdownファイルを指定すると、`books/基本設計書.xlsx`、`books/結合試験書.xlsx`、`books/課題管理表.xlsx` ができる。

```powershell
uv run .compass/documents/scripts/export_excel.py docs/basic-design.md docs/integration-testing.md .compass/records/issue-log.md
```

更新は元のMarkdownに記録し、再出力で同名のブックを更新する。単一文書のファイル名は `-o 納品用.xlsx` または `-o books/納品用.xlsx` で指定できる。どちらも `books/納品用.xlsx` に保存する。複数文書は出力先を省略するか、`-o books` を指定する。他のディレクトリを指定するとエラーになる。

`テンプレート_` は同梱テンプレートの予約接頭辞。記入済み文書のタイトル自体がこの文字列で始まる場合、自動生成するファイル名には先頭に `文書_` を付ける。リンクと画像は表示名と参照先のテキスト、Mermaidなどのコードブロックはソーステキストで出力する。
