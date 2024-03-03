import csv
import io
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone

import requests
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI


# 指定された日付でEDINETから文書一覧を取得する
def get_edinet_list(date):
    api_key = os.environ.get("EDINET_API")
    url = f"https://api.edinet-fsa.go.jp/api/v2/documents.json?date={date}&type=2&Subscription-Key={api_key}"
    response = requests.request("GET", url)
    return json.loads(response.text)


# EDINETリストから特定のシンボルリストに一致する文書をフィルタリングする
def filter_edinet_list(EDINET_LIST, symbol_list):
    watchlist_docs = []
    for result in EDINET_LIST["results"]:
        if result["secCode"] and result["secCode"][:-1] in symbol_list:
            if result["docTypeCode"] in ["140", "160"]:
                watchlist_docs.append(
                    {
                        "secCode": result["secCode"][:-1],
                        "filerName": result["filerName"],
                        "docID": result["docID"],
                        "docTypeCode": result["docTypeCode"],
                    }
                )
    return watchlist_docs


# EDINETから指定された文書IDの文書をダウンロードする
def download_edinet_documents(watchlist_docs):
    api_key = os.environ.get("EDINET_API")
    docID = watchlist_docs["docID"]
    filer_name_dir = os.path.join("documents", watchlist_docs["filerName"])
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
def extract_content_from_csv(watchlist_docs):
    content_data = {}
    filer_name_dir = os.path.join("documents", watchlist_docs["filerName"])
    # 解凍したzipのXBRL_TO_CSVフォルダ内のjpcrpから始まるcsvファイルを解析する
    for file in os.listdir(os.path.join(filer_name_dir, "XBRL_TO_CSV")):
        if file.startswith("jpcrp") and file.endswith(".csv"):
            csv_path = os.path.join(filer_name_dir, "XBRL_TO_CSV", file)
            with open(csv_path, "r", encoding="utf-16") as csv_file:
                reader = csv.reader(csv_file, delimiter="\t")
                for row in reader:
                    if (
                        row[0]
                        == "jpcrp_cor:ManagementAnalysisOfFinancialPositionOperatingResultsAndCashFlowsTextBlock"
                    ):
                        content_data["management_analysis_content"] = row[8]
                    elif row[0] == "jpcrp_cor:QuarterlyAccountingPeriodCoverPage":
                        content_data["quarterly_accounting_period_content"] = row[8]
    return content_data


# chatGPTを使用して財務報告の内容を要約する
def summarize_financial_reports(content_data, watchlist_doc):

    # output parserを設定
    class Summary(BaseModel):
        summary: str = Field(description="業績サマリ", max_length=200)
        macro_factor: str = Field(description="マクロの業績変動要因", max_length=50)
        market_factor: str = Field(description="市場の業績変動要因", max_length=50)
        company_factor: str = Field(description="会社の業績変動要因", max_length=50)
        outlook: str = Field(description="今後の展望", max_length=300)

    parser = JsonOutputParser(pydantic_object=Summary)

    # プロンプトを設定
    system_prompt = """あなたは20代後半の私の幼馴染のお姉さんです。
企業の決算を要約して教えてくれます。
「～かしら」「～ね」「～わ」といったお姉さん口調のため口で話します。
たまにちょっとからかうようなことも言ってきます。
"""

    user_prompt = """# 命令文
{company_name}の決算概要を読み、業績、マクロの業績変動要因、市場の業績変動要因、会社の業績変動要因のサマリと今後の展望を解説してください。
# 決算概要
{finance_contents}
# 出力
{format_instructions}
"""

    messages = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ],
    )
    template = messages.partial(format_instructions=parser.get_format_instructions())

    # chatモデルを設定
    chat = ChatOpenAI(model_name="gpt-4-0125-preview", temperature=1, max_tokens=1024).bind(
        response_format={"type": "json_object"}
    )

    # chainを設定
    chain = template | chat | parser
    result = chain.invoke(
        {
            "company_name": watchlist_doc["filerName"],
            "finance_contents": content_data["quarterly_accounting_period_content"],
        }
    )

    return result


# LINE APIを使用して財務サマリーを送信する
def send_financial_summary(watchlist_doc, content_data, chat_response_data):
    token = os.environ.get("line_token")
    userId = os.environ.get("line_userId")

    lineMessageApi = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    summary = chat_response_data["summary"]
    macro_factor = chat_response_data["macro_factor"]
    market_factor = chat_response_data["market_factor"]
    company_factor = chat_response_data["company_factor"]
    outlook = chat_response_data["outlook"]
    content = {
        "type": "bubble",
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
                    "text": content_data["quarterly_accounting_period_content"],
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
                        {"type": "text", "text": "業績", "weight": "bold"},
                        {"type": "text", "text": summary, "wrap": True},
                        {"type": "separator", "margin": "xxl"},
                        {"type": "text", "text": "業績変動要因", "weight": "bold", "margin": "none"},
                        {"type": "text", "text": "- マクロ"},
                        {"type": "text", "text": macro_factor, "wrap": True},
                        {"type": "text", "text": "- 業界"},
                        {"type": "text", "text": market_factor, "wrap": True},
                        {"type": "text", "text": "- 会社"},
                        {"type": "text", "text": company_factor, "wrap": True},
                        {"type": "separator", "margin": "xxl"},
                        {"type": "text", "text": "今後の展望", "weight": "bold"},
                        {"type": "text", "text": outlook, "wrap": True},
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
    watchlist = ["8001"]

    # 日付設定（本来は当日の日付を設定する想定）
    # JST = timezone(timedelta(hours=+9))
    # date = datetime.now(JST).strftime("%Y-%m-%d")

    # 日付設定（テスト用に直近で伊藤忠の決算が出た日を設定）
    date = "2024-02-14"

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

        print(f"{watchlist_doc['filerName']} >> chatGPTで要約を取得します...")
        chat_response_data = summarize_financial_reports(content_data, watchlist_doc)
        print(f"{watchlist_doc['filerName']} >> 財務報告の要約を取得しました。")  # デバッグ用のコメント

        send_financial_summary(watchlist_doc, content_data, chat_response_data)
        print(f"{watchlist_doc['filerName']} >> 財務サマリーをLINEに送信しました。")  # デバッグ用のコメント
