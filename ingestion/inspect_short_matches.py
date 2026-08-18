import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_MATCH_DIR = PROJECT_ROOT / "data" / "raw" / "matches"


short_matches = []


for file_path in RAW_MATCH_DIR.glob("*.json"):

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    info = data.get("info", {})

    participants = info.get("participants", [])

    duration = info.get("gameDuration", 0)

    has_bot = any(
        p.get("puuid") == "BOT"
        for p in participants
    )

    if duration < 300:

        short_matches.append({
            "match_id": metadata.get("matchId"),
            "duration": duration,
            "game_mode": info.get("gameMode"),
            "queue_id": info.get("queueId"),
            "map_id": info.get("mapId"),
            "has_bot": has_bot,
            "participants": len(participants),
            "game_ended_in_surrender": any(
                p.get("gameEndedInSurrender", False)
                for p in participants
            ),
            "game_ended_in_early_surrender": any(
                p.get("gameEndedInEarlySurrender", False)
                for p in participants
            )
        })


short_matches.sort(
    key=lambda x: x["duration"]
)


print("===== SHORT MATCHES (< 300 seconds) =====")

if not short_matches:
    print("No short matches found.")

else:
    for match in short_matches:

        print()
        print("Match ID:", match["match_id"])
        print("Duration:", match["duration"], "seconds")
        print("Mode:", match["game_mode"])
        print("Queue:", match["queue_id"])
        print("Map:", match["map_id"])
        print("Participants:", match["participants"])
        print("BOT:", match["has_bot"])
        print(
            "Surrender:",
            match["game_ended_in_surrender"]
        )
        print(
            "Early surrender:",
            match["game_ended_in_early_surrender"]
        )
