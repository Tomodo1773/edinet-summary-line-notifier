import json
import logging
import os

import requests


def call_login():
    url = "https://tomostock.azurewebsites.net/api/login"

    username = os.environ.get("TOMOSTOCK_USERID")
    password = os.environ.get("TOMOSTOCK_PASSWORD")

    # POSTリクエストを行う
    headers = {"Content-Type": "application/json"}  # Set correct header
    data = json.dumps({"username": username, "password": password, "type": "http"})  # Include your data as JSON

    response = requests.request(
        "POST",
        url,
        headers=headers,
        data=data,
    )

    if response.status_code == 200:
        logging.info("ログインAPIの呼び出しに成功しました。")
    else:
        logging.info(
            f"ログインAPIの呼び出しに失敗しました。レスポンスコード: {response.status_code}, レスポンス: {response.text}"
        )
    token_data = json.loads(response.text)
    return token_data.get("token")


def send_stockinfo_request(token):
    url = "https://tomostocks.azurewebsites.net/api/stockinfo"

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    params = {"type": "日本株"}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        logging.info("銘柄情報APIの呼び出しに成功しました。")
    else:
        logging.info(
            f"銘柄情報APIの呼び出しに失敗しました。レスポンスコード: {response.status_code}, レスポンス: {response.text}"
        )

    return response.text


def get_watchlist():
    token = call_login()
    response = send_stockinfo_request(token)
    watchlist = [stock["symbol"] for stock in json.loads(response)]
    return watchlist


if __name__ == "__main__":
    watchlist = get_watchlist()
    print(watchlist)
