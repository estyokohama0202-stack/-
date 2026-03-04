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


def get_duration():

    if not start_time:
        return "0m"

    delta = datetime.now() - start_time
    h = delta.seconds // 3600
    m = (delta.seconds % 3600) // 60

    return f"{h}h{m}m"


def send_card(viewers, diff):

    color = 5763719
    if diff < 0:
        color = 15548997

    embed = {
        "color": color,
        "fields": [

            {
                "name": "🎥 現在同接",
                "value": f"**{viewers}**\n{diff:+}",
                "inline": False
            },

            {
                "name": "📊 最大同接",
                "value": str(max_viewers),
                "inline": False
            }

        ]
    }

    requests.post(WEBHOOK, json={"embeds":[embed]})

def send_spike(old,new):

    embed = {
        "title": "🚨 急増検知",
        "description": f"{old} → {new}",
        "color": 16753920
    }

    requests.post(WEBHOOK,json={"embeds":[embed]})


def make_graph():

    if len(history) < 2:
        return

    plt.figure(figsize=(10,4))

    plt.plot(history,color="#9146FF",linewidth=3)

    plt.fill_between(range(len(history)),history,alpha=0.2,color="#9146FF")

    plt.title("Viewer Trend")

    plt.xlabel("Time")
    plt.ylabel("Viewers")

    plt.grid(alpha=0.3)

    plt.tight_layout()

    plt.savefig("graph.png")

    plt.close()


def send_graph():

    make_graph()

    files = {"file":open("graph.png","rb")}

    requests.post(WEBHOOK,files=files)


def send_report():

    avg = int(sum(history)/len(history))

    embed = {

        "title":"📊 配信終了レポート",

        "fields":[

            {"name":"最大同接","value":str(max_viewers)},
            {"name":"平均同接","value":str(avg)},
            {"name":"配信時間","value":get_duration()}

        ]

    }

    requests.post(WEBHOOK,json={"embeds":[embed]})

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
            timestamps.append(datetime.now())

            if viewers > max_viewers:
                max_viewers = viewers

            diff = viewers - prev

            send_card(viewers,diff)

            if prev > 0:

                percent = diff/prev

                if percent > 0.2:
                    send_spike(prev,viewers)

            prev = viewers

            if time.time() - last_graph > 1800:

                send_graph()

                last_graph = time.time()

        else:

            if history:

                send_report()

                history.clear()

                start_time = None

        time.sleep(300)


main()
