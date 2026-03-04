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
timestamps = []

spikes = []
drops = []

start_time = None
max_viewers = 0

last_graph = time.time()


def get_token():

    r = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
    )

    return r.json()["access_token"]


def get_viewers(token):

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    r = requests.get(
        f"https://api.twitch.tv/helix/streams?user_login={CHANNEL}",
        headers=headers
    ).json()

    if not r["data"]:
        return None

    return r["data"][0]["viewer_count"]
def send_card(viewers, diff):

    if diff > 0:
        color = 5763719
        diff_text = f"+{diff}"
    elif diff < 0:
        color = 15548997
        diff_text = f"{diff}"
    else:
        color = 9807270
        diff_text = "0"

    embed = {
        "color": color,
        "fields": [

            {
                "name": "📊 現在同時接続者数",
                "value": f"**{viewers:,}**\n{diff_text}",
                "inline": False
            },

            {
                "name": "📈 最大同時接続者数",
                "value": f"{max_viewers:,}",
                "inline": False
            }

        ],

        "footer": {
            "text": "Twitch Viewer Monitor",
            "icon_url": "https://static-cdn.jtvnw.net/jtv_user_pictures/xarth/404_user_70x70.png"
        }

    }  # ←これが必要

    requests.post(WEBHOOK, json={"embeds":[embed]})
def send_spike(old, new):

    embed = {
        "title": "🚨📈 同接急増検知しました",
        "description": f"{old:,} → {new:,}",
        "color": 16753920
    }

    requests.post(WEBHOOK, json={"embeds":[embed]})


def send_drop(old, new):

    embed = {
        "title": "🚨📉 同接急落検知しました",
        "description": f"{old:,} → {new:,}",
        "color": 15158332
    }

    requests.post(WEBHOOK, json={"embeds":[embed]})


def make_graph():

    if len(history) < 2:
        return

    plt.figure(figsize=(10,4))

    plt.plot(history, color="#9146FF", linewidth=3)

    plt.fill_between(range(len(history)),
                     history,
                     alpha=0.2,
                     color="#9146FF")

    for i in spikes:
        plt.scatter(i, history[i],
                    color="red",
                    s=140,
                    zorder=5)

    for i in drops:
        plt.scatter(i, history[i],
                    color="yellow",
                    s=140,
                    zorder=5)

    plt.title("Viewer Trend")
    plt.xlabel("Time")
    plt.ylabel("Viewers")

    plt.grid(alpha=0.3)

    plt.tight_layout()

    plt.savefig("graph.png")
    plt.close()


def send_graph():

    make_graph()

    files = {"file": open("graph.png", "rb")}

    requests.post(WEBHOOK, files=files)


def send_report():

    avg = int(sum(history) / len(history))

    embed = {

        "title": "📊 配信終了レポート",

        "fields": [

            {"name": "最大同接", "value": f"{max_viewers:,}"},
            {"name": "平均同接", "value": f"{avg:,}"}

        ]
    }

    requests.post(WEBHOOK, json={"embeds":[embed]})

    send_graph()


def main():

    global start_time
    global max_viewers
    global last_graph

    token = get_token()

    prev = 0

    while True:

        viewers = get_viewers(token)

        if viewers:

            if not start_time:
                start_time = datetime.now()

            history.append(viewers)

            if viewers > max_viewers:
                max_viewers = viewers

            diff = viewers - prev

            send_card(viewers, diff)

            if prev > 0:

                percent = diff / prev

                if percent > 0.2:
                    spikes.append(len(history)-1)
                    send_spike(prev, viewers)

                if percent <= -0.2:
                    drops.append(len(history)-1)
                    send_drop(prev, viewers)

            prev = viewers

            if time.time() - last_graph > 1800:

                send_graph()

                last_graph = time.time()

        else:

            if history:

                send_report()

                history.clear()
                spikes.clear()
                drops.clear()

                start_time = None
                max_viewers = 0

        time.sleep(300)


main()
