import requests
import os
import time
from datetime import datetime
import matplotlib.pyplot as plt

CHANNEL = "dj___shige"

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

history = []
times = []

start_time = None
max_viewers = 0


def get_token():
    url = "https://id.twitch.tv/oauth2/token"

    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    r = requests.post(url, params=params)
    return r.json()["access_token"]


def get_viewers(token):

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    url = f"https://api.twitch.tv/helix/streams?user_login={CHANNEL}"

    r = requests.get(url, headers=headers).json()

    if not r["data"]:
        return None

    return r["data"][0]["viewer_count"]


def send_card(viewers, diff):

    color = 3066993

    if diff < 0:
        color = 15158332

    embed = {
        "title": "📺 DJ_SHIGE LIVE監視",
        "color": color,
        "fields": [
            {
                "name": "👀 現在同接",
                "value": f"{viewers} ({diff:+})",
                "inline": False
            },
            {
                "name": "📊 最大同接",
                "value": str(max_viewers),
                "inline": True
            },
            {
                "name": "⏱ 配信時間",
                "value": get_duration(),
                "inline": True
            }
        ],
        "footer": {
            "text": "Twitch Monitor"
        }
    }

    requests.post(WEBHOOK, json={"embeds": [embed]})


def send_spike(old, new):

    embed = {
        "title": "🚨 急増検知",
        "description": f"{old} → {new}",
        "color": 16753920
    }

    requests.post(WEBHOOK, json={"embeds": [embed]})


def get_duration():

    if not start_time:
        return "0m"

    delta = datetime.now() - start_time

    h = delta.seconds // 3600
    m = (delta.seconds % 3600) // 60

    return f"{h}h{m}m"


def save_graph():

    plt.figure()

    plt.plot(times, history)

    plt.xlabel("Time")
    plt.ylabel("Viewers")

    plt.savefig("graph.png")


def send_graph():

    save_graph()

    files = {"file": open("graph.png", "rb")}

    requests.post(WEBHOOK, files=files)


def main():

    global start_time
    global max_viewers

    token = get_token()

    prev = 0

    while True:

        viewers = get_viewers(token)

        if viewers:

            if not start_time:
                start_time = datetime.now()

            history.append(viewers)
            times.append(len(history))

            if viewers > max_viewers:
                max_viewers = viewers

            diff = viewers - prev

            send_card(viewers, diff)

            if prev > 0:

                percent = diff / prev

                if percent > 0.2:
                    send_spike(prev, viewers)

            prev = viewers

        else:

            if history:
                send_graph()

                avg = int(sum(history) / len(history))

                embed = {
                    "title": "📊 配信終了レポート",
                    "fields": [
                        {"name": "最大同接", "value": str(max_viewers)},
                        {"name": "平均同接", "value": str(avg)},
                        {"name": "配信時間", "value": get_duration()}
                    ]
                }

                requests.post(WEBHOOK, json={"embeds": [embed]})

                history.clear()

                start_time = None

        time.sleep(300)


main()
