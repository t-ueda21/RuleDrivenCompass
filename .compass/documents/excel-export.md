# Excel出力

[出力スクリプト](scripts/export_excel.py) はUTF-8のMarkdown文書を１文書につき１ブックに変換する。標準テンプレートでは９フェーズと課題管理表がそれぞれ１ブックになる。

| シートの順序 | 内容 |
| --- | --- |
| １．タイトル | 文書名と、Markdownの文書管理の項目 |
| ２．変更履歴 | Markdownの変更履歴、改訂履歴または変更・レビュー履歴 |
| ３以降 | [文書別のシート構成](excel-sheets.md)に従って関連する章をまとめる。課題管理表は課題一覧 |

標準テンプレートの文書名を使うと、対応するシート構成で出力する。章の必須・補足区分はシート内の見出しに表示する。変更履歴は元のMarkdownに記録して再出力する。

表の濃色の行は列見出し、淡い黄色のセルは未記入欄。章見出しは必須と補足を色と文字で区別する。

プロジェクトのルートで以下を実行する。前提は `uv`。初回は必要なPythonとライブラリを `uv` が準備する。

## 全テンプレートを出力

各 Skill の `references/template.md` を参照し、フェーズ用９冊と課題管理表１冊を指定フォルダに出力する。ブックのファイル名には文書のタイトルを使う。

```powershell
uv run .compass/documents/scripts/export_excel.py --templates -o rdc-templates
```

## 記入済みの文書を出力

課題管理表１冊だけを出力するときは、出力先の `.xlsx` を指定できる。「課題一覧」には状態列のフィルターがあり、課題 ID・発生フェーズ・状態を固定して確認できる。

```powershell
uv run .compass/documents/scripts/export_excel.py .compass/records/issue-log.md -o issue-log.xlsx
```

基本設計書、結合試験書、課題管理表を一括出力する例。複数文書の出力先にはフォルダを指定し、入力には実際のMarkdownファイルを指定する。

```powershell
uv run .compass/documents/scripts/export_excel.py docs/basic-design.md docs/integration-testing.md .compass/records/issue-log.md -o rdc-review
```

更新は元のMarkdownに記録し、Excelは再出力して確認する。同じ出力先を指定するとブックを更新する。リンクと画像は表示名と参照先のテキスト、Mermaidなどのコードブロックはソーステキストで出力する。
