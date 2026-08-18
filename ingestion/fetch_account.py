import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("RIOT_API_KEY")

if not api_key:
    raise ValueError("没有找到 RIOT_API_KEY")


# 改成你自己的 Riot ID
game_name = "Good7"
tag_line = "1202"

url = (
    f"https://asia.api.riotgames.com"
    f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
)

headers = {
    "X-Riot-Token": api_key
}

response = requests.get(url, headers=headers, timeout=10)

print("HTTP Status:", response.status_code)

if response.status_code == 200:
    data = response.json()

    print("Game Name:", data["gameName"])
    print("Tag Line:", data["tagLine"])
    print("PUUID:", data["puuid"])

elif response.status_code == 404:
    print("没有找到这个 Riot ID，请检查游戏名和 Tag")

elif response.status_code == 401:
    print("API Key 无效或已经过期")

elif response.status_code == 429:
    print("请求过多，被 Riot 限流")

else:
    print(response.text)
