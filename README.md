# edinet-chatgpt-line-notifier

edinet-chatgpt-line-notifierは、EDINETから特定の日付の文書一覧を取得し、特定のシンボルリストに一致する文書をフィルタリングしてダウンロードするPythonスクリプトです。さらに、ダウンロードした文書から必要な情報を抽出し、chatGPTを使用して財務報告の内容を要約し、LINE Messaging APIを介して財務サマリーを送信します。

下記記事に解説記事を書いています。コードの解説についてはこちらのほうが詳細に書いています。

[【My秘書】chatGPT×EDINET×LINEで保有銘柄の決算要約してくれるお姉さん](https://zenn.dev/tomodo_ysys/articles/edinet-chatgpt-financial-report)

## 特徴

- EDINETから特定の日付の文書一覧を取得
- ウォッチリストに登録された銘柄コードに基づいて文書をフィルタリング
- ダウンロードした文書から財務情報を抽出
- chatGPTを使用して財務報告の内容を要約
- LINE Messaging APIを通じて財務サマリーを送信

## 注意事項

- EDINETから取得するドキュメントは半期報告書、四半期報告書のみです。
- chatGPTやLINE通知ではお姉さん風のキャラ付けがされています。

## 前提条件

- OpenAI API Keyが取得済みであること。
- EDINET API Keyが取得済みであること。
- LINE Messaging APIのプロバイダーおよびチャンネルを作成していること。
- LINE投稿用のtokenを取得していること。

## セットアップ

1. `.env.sample` ファイルをコピーして `.env` ファイルを作成します。
2. `.env` ファイルに必要なAPIキーとトークンを設定します。

下記を参考にAPIキー、トークンを設定してください。

```none
EDINET_API= <EDINETのAPI key>
OPENAI_API_KEY= <OpenAIのAPI key>
line_userId= <作成したLINEプロバイダーのユーザID>
line_token= <作成したLINEチャンネルのtoken>
```

3. `main.py` スクリプトを実行して、EDINETから文書をダウンロードし、財務サマリーをLINEに送信します。

## 使用方法

1. ウォッチリストに監視したい銘柄コードを追加します。

main.pyの205行目に設定箇所があります。

```python
    # ウォッチリスト銘柄のシンボルを登録しておく
    watchlist = ["3050"]
```

2. `main.py` を実行して、プロセスを開始します。
3. LINEで財務サマリーを受け取ります。

## リファレンス

[EDINET -操作ガイド-](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0110.html)

[OpenAI API Reference](https://platform.openai.com/docs/overview)

## ライセンス

このプロジェクトはMITライセンスのもとで公開されています。詳細は `LICENSE` ファイルを参照してください。

## 貢献

バグの報告、新機能の提案、プルリクエストなどはGitHubのissueやプルリクエストを通じて歓迎します。

## サポート

使用方法に関する質問やサポートが必要な場合は、GitHubのissueを通じてお問い合わせください。
