import json
import os

import requests

from schema import ContentData, WatchlistDoc


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
                        {"type": "text", "text": chat_response_data["generalize"], "wrap": True},
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
