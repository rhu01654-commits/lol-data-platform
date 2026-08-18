import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("RIOT_API_KEY")

if not api_key:
    raise ValueError("没有找到 RIOT_API_KEY")


# 这里填刚刚获取到的 PUUID
puuid = "U5XHGiIq3LaD8PhYYq8_KaiAgElvlY-p9kjWWAfMf2DAH-QSo6_GZJj7KV6udczWGOXXsiVHQTvkWQ"

# Match-V5 使用 regional routing
url = (
    f"https://sea.api.riotgames.com"
    f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
)

headers = {
    "X-Riot-Token": api_key
}

params = {
    "start": 0,
    "count": 20
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=10
)

print("HTTP Status:", response.status_code)

if response.status_code == 200:
    match_ids = response.json()

    print("Match count:", len(match_ids))

    for match_id in match_ids:
        print(match_id)

elif response.status_code == 401:
    print("API Key 无效或已经过期")

elif response.status_code == 404:
    print("没有找到相关比赛数据")

elif response.status_code == 429:
    print("请求过多，被 Riot 限流")

else:
    print(response.text)
