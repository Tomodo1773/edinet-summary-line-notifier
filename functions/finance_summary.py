import logging
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from langsmith import Client

from utils.edinet import (
    download_edinet_documents,
    extract_content_from_csv,
    filter_edinet_list,
    get_edinet_list,
    delete_document_folder,
)
from utils.line import send_financial_summary
from utils.llm import summarize_financial_reports
from utils.get_watchlist import get_watchlist

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_PROJECT"] = "Finance"

client = Client()

def finance_summary():
    # ウォッチリスト銘柄のシンボルを登録しておく（ex. 8001: 伊藤忠商事）
    # 本コードではget_watchlistを用いてTomoStockからシンボルリストを取得しているが適宜変更
    # ex) watchlist = ["2163"]
    watchlist = get_watchlist()
    logging.info(f"ウォッチリストを取得しました: {watchlist}")  # デバッグ用のコメント

    # 日付設定（本来は当日の日付を設定する想定）
    JST = timezone(timedelta(hours=+9))
    date = datetime.now(JST).strftime("%Y-%m-%d")

    # 日付設定（テスト用に直近で伊藤忠の決算が出た日を設定）
    # date = "2023-06-22"
    # date = "2024-04-25"

    edinet_list = get_edinet_list(date)
    logging.info(f"{date}のEDINETリストを取得しました")  # デバッグ用のコメント
    watchlist_docs = filter_edinet_list(edinet_list, watchlist)
    if not watchlist_docs:
        logging.info("ウォッチリストの報告書はありませんでした。処理を終了します。")
        return
    else:
        logging.info("ウォッチリストの報告書が新規アップロードされています。後続の処理を実行します。")
        # watchlist_docのfilerNameの値のみloggingで出力する
        logging.info(f"対象銘柄: {[watchlist_doc['filerName'] for watchlist_doc in watchlist_docs]}")

    for watchlist_doc in watchlist_docs:
        download_edinet_documents(watchlist_doc)
        logging.info(f"{watchlist_doc['filerName']} >> ドキュメントをダウンロードしました。")  # デバッグ用のコメント
        content_data = extract_content_from_csv(watchlist_doc)
        logging.info(f"{watchlist_doc['filerName']} >> CSVからコンテンツデータを抽出しました。")  # デバッグ用のコメント

        logging.info(f"{watchlist_doc['filerName']} >> 生成AIで要約を取得します...")
        chat_response_data = summarize_financial_reports(content_data, watchlist_doc)
        logging.info(f"{watchlist_doc['filerName']} >> 財務報告の要約を取得しました。")  # デバッグ用のコメント

        send_financial_summary(watchlist_doc, content_data, chat_response_data)
        logging.info(f"{watchlist_doc['filerName']} >> 財務サマリーをLINEに送信しました。")  # デバッグ用のコメント
    
    delete_document_folder()
