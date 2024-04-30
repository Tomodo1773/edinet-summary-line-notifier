import csv
import io
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from typing import TypedDict

import requests

# from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser

# from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langsmith import Client

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_PROJECT"] = "Finance"

client = Client()


# watchlist_docのスキーマ定義
# EDINETのドキュメント一覧から取得したウォッチリスト銘柄のドキュメントに関する情報
class WatchlistDoc(TypedDict):
    secCode: str  # 企業シンボル
    filerName: str  # 企業名
    docID: str  # 文書ID
    docTypeCode: str  # 文書種別


# content_dataのスキーマ定義
# ウォッチリスト銘柄のドキュメントのコンテンツに関する情報
class ContentData(TypedDict):
    period: str  # 決算対象期間
    financial_indicators: str  # 経営指標
    mgmt_analysis: str  # 経営の課題
    mgmt_issues: str  # 経営の分析
    business_risks: str  # 事業リスク


def read_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "ファイルが見つかりませんでした。"
    except Exception as e:
        return f"ファイルの読み込み中にエラーが発生しました: {str(e)}"


# 指定された日付でEDINETから文書一覧を取得する
def get_edinet_list(date):
    api_key = os.environ.get("EDINET_API")
    url = f"https://api.edinet-fsa.go.jp/api/v2/documents.json?date={date}&type=2&Subscription-Key={api_key}"
    response = requests.request("GET", url)
    return json.loads(response.text)


# EDINETリストから特定のシンボルリストに一致する文書をフィルタリングする
# 120: 有価証券報告書
# 140: 四半期決算報告書
# 160: 半期決算報告書
def filter_edinet_list(EDINET_LIST, symbol_list) -> list[WatchlistDoc]:
    watchlist_docs: list[WatchlistDoc] = []
    for result in EDINET_LIST["results"]:
        if result["secCode"] and result["secCode"][:-1] in symbol_list:
            if result["docTypeCode"] in ["120", "140", "160"]:
                watchlist_docs.append(
                    {
                        "secCode": result["secCode"][:-1],  # 企業シンボル
                        "filerName": result["filerName"],  # 企業名
                        "docID": result["docID"],  # 文書ID
                        "docTypeCode": result["docTypeCode"],  # 文書種別
                    }
                )
    return watchlist_docs


# EDINETから指定された文書IDの文書をダウンロードする
def download_edinet_documents(watchlist_doc: WatchlistDoc):
    api_key = os.environ.get("EDINET_API")
    docID = watchlist_doc["docID"]
    filer_name_dir = os.path.join("documents", watchlist_doc["filerName"])
    os.makedirs(filer_name_dir, exist_ok=True)
    # EDINETからpdfを取得
    url = f"https://api.edinet-fsa.go.jp/api/v2/documents/{docID}?type=2&Subscription-Key={api_key}"
    response = requests.request("GET", url)
    with open(os.path.join(filer_name_dir, f"{docID}.pdf"), "wb") as f:
        f.write(response.content)
    # EDINETからzipを取得
    url = f"https://api.edinet-fsa.go.jp/api/v2/documents/{docID}?type=5&Subscription-Key={api_key}"
    response = requests.request("GET", url)
    # ZIPファイルを解凍する
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall(filer_name_dir)
    return


# ダウンロードした文書から必要な情報をCSVファイルから抽出する
# 半期決算/四半期決算の場合(docTypeCode=140,160)
# - 「四半期会計期間、表紙」(jpcrp_cor:QuarterlyAccountingPeriodCoverPage)
# - 「第2【事業の状況】 > 1【事業等のリスク】」(jpcrp_cor:BusinessRisksTextBlock)
# - 「第2【事業の状況】 > 2【経営者による財政状態、経営成績及びキャッシュ・フローの状況の分析】」(jpcrp_cor:ManagementAnalysisOfFinancialPositionOperatingResultsAndCashFlowsTextBlock)
# 有価証券報告書の場合(docTypeCode=120)
# - 「事業年度、表紙」(jpcrp_cor:FiscalYearCoverPage)
# - 「第1部【企業情報】 > 第1【企業の概況】 > 1【主要な経営指標等の推移】」(jpcrp_cor:BusinessResultsOfReportingCompanyTextBlock)
#       ※会社によって章の日本語タイトルは異なる。グループ会社があるかどうか、など
# - 「第2【事業の状況】 > 1【経営方針、経営環境及び対処すべき課題等】」(jpcrp_cor:BusinessPolicyBusinessEnvironmentIssuesToAddressEtcTextBlock)
# - 「第2【事業の状況】 > 3【事業等のリスク】」(jpcrp_cor:BusinessRisksTextBlock)
# - 「第2【事業の状況】 > 4【経営者による財政状態、経営成績及びキャッシュ・フローの状況の分析】」(jpcrp_cor:ManagementAnalysisOfFinancialPositionOperatingResultsAndCashFlowsTextBlock)


def extract_content_from_csv(watchlist_doc: WatchlistDoc) -> ContentData:
    content_data: ContentData = {}
    filer_name_dir = os.path.join("documents", watchlist_doc["filerName"])
    # 解凍したzipのXBRL_TO_CSVフォルダ内のjpcrpから始まるcsvファイルを解析する
    for file in os.listdir(os.path.join(filer_name_dir, "XBRL_TO_CSV")):
        if file.startswith("jpcrp") and file.endswith(".csv"):
            csv_path = os.path.join(filer_name_dir, "XBRL_TO_CSV", file)
            with open(csv_path, "r", encoding="utf-16") as csv_file:
                reader = csv.reader(csv_file, delimiter="\t")

                if watchlist_doc["docTypeCode"] in ["140", "160"]:
                    for row in reader:
                        if (
                            row[0]
                            == "jpcrp_cor:ManagementAnalysisOfFinancialPositionOperatingResultsAndCashFlowsTextBlock"
                        ):
                            content_data["mgmt_analysis"] = row[8]
                        elif row[0] == "jpcrp_cor:BusinessRisksTextBlock":
                            content_data["business_risks"] = row[8]
                        elif row[0] == "jpcrp_cor:QuarterlyAccountingPeriodCoverPage":
                            content_data["period"] = row[8]
                elif watchlist_doc["docTypeCode"] == "120":
                    for row in reader:
                        if (
                            row[0]
                            == "jpcrp_cor:ManagementAnalysisOfFinancialPositionOperatingResultsAndCashFlowsTextBlock"
                        ):
                            content_data["mgmt_analysis"] = row[8]
                        elif row[0] == "jpcrp_cor:BusinessRisksTextBlock":
                            content_data["business_risks"] = row[8]
                        elif row[0] == "jpcrp_cor:BusinessPolicyBusinessEnvironmentIssuesToAddressEtcTextBlock":
                            content_data["mgmt_issues"] = row[8]
                        elif row[0] == "jpcrp_cor:FiscalYearCoverPage":
                            content_data["period"] = row[8]
    return content_data


# chatGPTを使用して財務報告の内容を要約する
def summarize_financial_reports(content_data: ContentData, watchlist_doc: WatchlistDoc):

    # output parserを設定
    class Summary(BaseModel):
        project_status: str = Field(description="事業の状況", max_length=400)
        outlook: str = Field(description="次期の見通し", max_length=400)
        generalize: str = Field(description="総括", max_length=400)

    parser = JsonOutputParser(pydantic_object=Summary)

    # プロンプトをロード
    system_prompt = read_file("prompt/system_prompt.txt")
    user_prompt = read_file("prompt/user_prompt.txt")

    template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ],
    )

    prompt = template.partial(format_instructions=parser.get_format_instructions())

    # chatモデルを設定
    # chat = ChatAnthropic(model="claude-3-opus-20240229", max_tokens=4096, temperature=0.7)
    chat = ChatAnthropic(model="claude-3-opus-20240229", max_tokens=4096, temperature=0.7)

    # chainを設定
    chain = prompt | chat | parser
    result = chain.invoke(
        {
            "company_name": watchlist_doc["filerName"],
            "period": content_data["period"],
            "mgmt_issues": content_data["mgmt_issues"],
            "business_risks": content_data["business_risks"],
            "mgmt_analysis": content_data["mgmt_analysis"],
        }
    )
    return result


# LINE APIを使用して財務サマリーを送信する
def send_financial_summary(watchlist_doc: WatchlistDoc, content_data: ContentData, chat_response_data):
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    userId = os.environ.get("LINE_USER_ID")

    lineMessageApi = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    content = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "決算概要", "weight": "bold", "color": "#1DB446", "size": "sm"},
                {
                    "type": "text",
                    "text": watchlist_doc["filerName"],
                    "weight": "bold",
                    "size": "xxl",
                    "margin": "md",
                },
                {
                    "type": "text",
                    "text": content_data["period"],
                    "size": "xs",
                    "color": "#aaaaaa",
                    "wrap": True,
                },
                {"type": "separator", "margin": "xxl"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "xxl",
                    "spacing": "sm",
                    "contents": [
                        {"type": "text", "text": "事業の状況", "weight": "bold"},
                        {"type": "text", "text": chat_response_data["project_status"], "wrap": True},
                        {"type": "separator", "margin": "xxl"},
                        {"type": "text", "text": "次期の見通し", "weight": "bold"},
                        {"type": "text", "text": chat_response_data["outlook"], "wrap": True},
                        {"type": "separator", "margin": "xxl"},
                        {"type": "text", "text": "総括", "weight": "bold"},
                        {"type": "text", "text":chat_response_data["generalize"], "wrap": True},
                    ],
                },
            ],
        },
        "styles": {"footer": {"separator": True}},
    }

    flexMessage = {
        "type": "flex",
        "altText": watchlist_doc["filerName"] + "の決算が出たみたいね",
        "contents": content,
    }

    data = {"to": userId, "messages": [flexMessage]}
    try:
        response = requests.post(lineMessageApi, headers=headers, data=json.dumps(data))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Error occurred while sending message: ", str(e))
    else:
        if response.status_code == 200:
            print("Message sent successfully.")
        else:
            print(f"Failed to send the message. HTTP status code: {response.status_code}")
            print("Response body: ", response.text)


if __name__ == "__main__":
    # ウォッチリスト銘柄のシンボルを登録しておく（ex. 8001: 伊藤忠商事）
    watchlist = ["2163"]

    # 日付設定（本来は当日の日付を設定する想定）
    # JST = timezone(timedelta(hours=+9))
    # date = datetime.now(JST).strftime("%Y-%m-%d")

    # 日付設定（テスト用に直近で伊藤忠の決算が出た日を設定）
    # date = "2023-06-22"
    date = "2024-04-25"

    edinet_list = get_edinet_list(date)
    print(f"{date}のEDINETリストを取得しました")  # デバッグ用のコメント
    watchlist_docs = filter_edinet_list(edinet_list, watchlist)
    if not watchlist_docs:
        print("ウォッチリストの報告書はありませんでした。処理を終了します。")
        exit()
    else:
        print("ウォッチリストの報告書が新規アップロードされています。後続の処理を実行します。")
        # watchlist_docのfilerNameの値のみprintする
        print(f"対象銘柄: {[watchlist_doc['filerName'] for watchlist_doc in watchlist_docs]}")

    for watchlist_doc in watchlist_docs:
        download_edinet_documents(watchlist_doc)
        print(f"{watchlist_doc['filerName']} >> ドキュメントをダウンロードしました。")  # デバッグ用のコメント
        content_data = extract_content_from_csv(watchlist_doc)
        print(f"{watchlist_doc['filerName']} >> CSVからコンテンツデータを抽出しました。")  # デバッグ用のコメント

        print(f"{watchlist_doc['filerName']} >> 生成AIで要約を取得します...")
        chat_response_data = summarize_financial_reports(content_data, watchlist_doc)
        print(f"{watchlist_doc['filerName']} >> 財務報告の要約を取得しました。")  # デバッグ用のコメント

        send_financial_summary(watchlist_doc, content_data, chat_response_data)
        print(f"{watchlist_doc['filerName']} >> 財務サマリーをLINEに送信しました。")  # デバッグ用のコメント
