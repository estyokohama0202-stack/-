import requests
import os
import json
from datetime import datetime

# ===== 環境変数 =====
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
WEBHOOK = os.getenv("DISCORD_WEBHOOK")

USERNAME = "dj___shige"
DATA_FILE = "viewer_data.json"

PERCENT_THRESHOLD = 0.20   # 20%急増判定
MIN_BASE_VIEWERS = 30      # 30人以下は急増判定しない


# ===== Twitch API =====
def get_access_token():
    r = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
    )
    return r.json()["access_token"]


def get_viewer_count(token):
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    r = requests.get(
        f"https://api.twitch.tv/helix/streams?user_login={USERNAME}",
        headers=headers
    )

    data = r.json()["data"]

    if not data:
        return None  # 配信してない

    return data[0]["viewer_count"]


# ===== データ保存 =====
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)

    return {
        "history": [],
        "max": 0,
        "min": 999999,
        "start_time": None
    }


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


# ===== Discord通知 =====
def notify(message):
    requests.post(WEBHOOK, json={"content": message})


# ===== メイン処理 =====
def main():
    token = get_access_token()
    viewers = get_viewer_count(token)
    data = load_data()

    # ===== 配信してない場合 =====
    if viewers is None:
        if data["history"]:
            total_change = data["history"][-1] - data["history"][0]

            notify(
                f"📴 配信終了\n"
                f"配信時間: {data['start_time']}〜\n"
                f"最大同接: {data['max']}\n"
                f"最小同接: {data['min']}\n"
                f"総増減: {total_change:+}"
            )

            save_data({
                "history": [],
                "max": 0,
                "min": 999999,
                "start_time": None
            })

        return

    # ===== 配信中 =====
    history = data["history"]

    if not history:
        data["start_time"] = datetime.now().strftime("%H:%M")

    history.append(viewers)

    # ===== 差分表示 =====
    if len(history) >= 2:
        prev = history[-2]
        diff = viewers - prev

        notify(f"👀 現在 {viewers}人 ({diff:+})")

        # ===== 20%急増判定 =====
        if prev >= MIN_BASE_VIEWERS:
            percent_change = diff / prev

            if percent_change >= PERCENT_THRESHOLD:
                notify(
                    f"🚨 急増検知！\n"
                    f"{prev} → {viewers}\n"
                    f"{percent_change*100:.1f}%増加"
                )

    data["max"] = max(data["max"], viewers)
    data["min"] = min(data["min"], viewers)
    data["history"] = history[-300:]  # 履歴制限

    save_data(data)


if __name__ == "__main__":
    main()
