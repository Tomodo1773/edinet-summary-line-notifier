from typing import TypedDict


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
