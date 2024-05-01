# edinet-chatgpt-line-notifier

## プロジェクト概要

このプロジェクトは、EDINETから決算報告書を取得し、ChatGPTを使用して要約を生成し、LINEに通知するシステムです。ウォッチリストに登録された企業の決算報告書が新しくアップロードされた際に、自動的に処理が実行されます。

## 主な機能

- EDINETから指定日の報告書一覧を取得
- ウォッチリストの企業の報告書を抽出
- 報告書をダウンロードし、必要な情報をCSVから抽出
- 抽出した情報をAIで要約
- 要約した決算情報をLINEメッセージとして送信

## 使用技術

- Python
- Azure Functions
- EDINET API
- LINE Messaging API
- Anthropic API (Claude)

## フォルダ構成とファイルの説明

```bash
- edinet-chatgpt-line-notifier/
  - .vscode/
  - functions/
    - finance_summary.py: 決算報告書の取得、要約、LINE通知の主要ロジックが含まれる
  - function_app.py: Azure Functionsのエントリーポイント
  - prompt.py: ChatGPTへのプロンプトを定義
  - requirements.txt: 必要なPythonパッケージを記載
  - sample/
  - schema.py: データ構造を定義
  - utils/
    - edinet.py: EDINETからの決算報告書の取得に関する関数群
    - get_watchlist.py: ウォッチリストの取得に関する関数
    - line.py: LINEへの通知に関する関数
    - llm.py: ChatGPTを使用した要約に関する関数
```

## インストール方法

### 前提条件

- Python 3.9以上
- Azure Functionsのアカウント
- LINE Developersのアカウント
- Anthropic APIのアカウント

### 手順

1. このリポジトリをクローン
2. 必要なPythonパッケージをインストール

```bash
pip install -r requirements.txt
```

3. 環境変数を設定

- EDINET_API: EDINETのAPIキー
- LINE_CHANNEL_ACCESS_TOKEN: LINEチャネルのアクセストークン
- LINE_USER_ID: 通知先のLINEユーザーID
- TOMOSTOCK_USERID: ウォッチリスト取得用のユーザーID
- TOMOSTOCK_PASSWORD: ウォッチリスト取得用のパスワード

4. Azure Functionsにデプロイ

5. Azure Functionsのスケジュールを設定

## 使用方法

1. ウォッチリストに企業シンボルを登録 (utils/get_watchlist.py)
2. Azure Functionsのタイマートリガーにより、毎日20時に自動実行
3. ウォッチリスト企業の決算報告書が新しくアップロードされていた場合、要約してLINEに通知

## ライセンス

ライセンスはMITライセンスです。
