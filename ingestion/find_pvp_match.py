import os
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("RIOT_API_KEY")

if not api_key:
    raise ValueError("没有找到 RIOT_API_KEY")


headers = {
    "X-Riot-Token": api_key
}


# --------------------------------
# 1. 读取我们第一场人机比赛
# --------------------------------

source_file = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "matches"
    / "TW2_439338347.json"
)

with open(source_file, "r", encoding="utf-8") as f:
    source_match = json.load(f)


# --------------------------------
# 2. 提取真人玩家 PUUID
# --------------------------------

human_puuids = []

for participant in source_match["info"]["participants"]:

    puuid = participant.get("puuid")

    if puuid and puuid != "BOT":
        human_puuids.append(puuid)


print("Human players found:", len(human_puuids))


# --------------------------------
# 3. 查询真人玩家最近的比赛
# --------------------------------

checked_match_ids = set()

found_match = None
found_match_id = None


for player_index, puuid in enumerate(human_puuids, start=1):

    print()
    print(f"Checking player {player_index}...")


    match_ids_url = (
        "https://sea.api.riotgames.com"
        f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
    )

    params = {
        "start": 0,
        "count": 20
    }

    response = requests.get(
        match_ids_url,
        headers=headers,
        params=params,
        timeout=10
    )


    if response.status_code != 200:
        print("Failed to fetch match IDs:", response.status_code)
        continue


    match_ids = response.json()

    print("Recent matches:", len(match_ids))


    # --------------------------------
    # 4. 检查每一场比赛
    # --------------------------------

    for match_id in match_ids:

        # 避免重复检查同一场比赛
        if match_id in checked_match_ids:
            continue

        checked_match_ids.add(match_id)


        detail_url = (
            "https://sea.api.riotgames.com"
            f"/lol/match/v5/matches/{match_id}"
        )

        response = requests.get(
            detail_url,
            headers=headers,
            timeout=10
        )


        if response.status_code == 429:
            print("Rate limited, waiting...")
            time.sleep(5)
            continue


        if response.status_code != 200:
            continue


        match_data = response.json()

        participants = match_data["info"].get(
            "participants",
            []
        )


        # --------------------------------
        # 5. 判断是否纯真人
        # --------------------------------

        has_bot = any(
            p.get("puuid") == "BOT"
            for p in participants
        )

        is_ten_players = len(participants) == 10


        print(
            match_id,
            "| players:",
            len(participants),
            "| bot:",
            has_bot,
            "| mode:",
            match_data["info"].get("gameMode")
        )


        if is_ten_players and not has_bot:

            found_match = match_data
            found_match_id = match_id

            break


        time.sleep(0.2)


    if found_match:
        break


# --------------------------------
# 6. 保存第一场真人比赛
# --------------------------------

if found_match:

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "matches"
    )

    output_file = (
        output_dir
        / f"{found_match_id}.json"
    )


    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            found_match,
            f,
            ensure_ascii=False,
            indent=2
        )


    print()
    print("==============================")
    print("PvP match found!")
    print("==============================")

    print("Match ID:", found_match_id)

    print(
        "Game Mode:",
        found_match["info"].get("gameMode")
    )

    print(
        "Queue ID:",
        found_match["info"].get("queueId")
    )

    print(
        "Players:",
        len(found_match["info"]["participants"])
    )

    print(
        "Saved to:",
        output_file
    )

else:

    print()
    print("No 10-player PvP match found.")
