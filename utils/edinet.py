import csv
import io
import json
import os
import zipfile

import requests

from schema import ContentData, WatchlistDoc


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
