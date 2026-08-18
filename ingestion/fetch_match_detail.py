import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 读取 .env
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("RIOT_API_KEY")

if not api_key:
    raise ValueError("没有找到 RIOT_API_KEY")


# 你刚刚获取到的比赛 ID
match_id = "TW2_439338347"


# Match-V5 使用 SEA regional routing
url = (
    f"https://sea.api.riotgames.com"
    f"/lol/match/v5/matches/{match_id}"
)

headers = {
    "X-Riot-Token": api_key
}


response = requests.get(
    url,
    headers=headers,
    timeout=10
)

print("HTTP Status:", response.status_code)


if response.status_code == 200:

    match_data = response.json()

    # 创建保存目录
    output_dir = PROJECT_ROOT / "data" / "raw" / "matches"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存 JSON
    output_file = output_dir / f"{match_id}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            match_data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("Match downloaded successfully!")
    print("Saved to:", output_file)

    # 打印一些基础信息
    print()
    print("Match ID:", match_data["metadata"]["matchId"])
    print(
        "Participant count:",
        len(match_data["metadata"]["participants"])
    )

    print(
        "Game Duration:",
        match_data["info"]["gameDuration"],
        "seconds"
    )

    print(
        "Game Version:",
        match_data["info"]["gameVersion"]
    )


elif response.status_code == 401:
    print("API Key 无效或已经过期")

elif response.status_code == 404:
    print("没有找到这个 Match ID")

elif response.status_code == 429:
    print("请求过多，被 Riot 限流")

else:
    print(response.text)
