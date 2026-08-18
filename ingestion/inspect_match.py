import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

file_path = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "matches"
    / "TW2_439101259.json"
)


with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)


info = data["info"]
metadata = data["metadata"]

print("===== Match Basic Info =====")
print("Match ID:", metadata.get("matchId"))
print("Participant count:", len(metadata.get("participants", [])))

print()
print("===== Game Info =====")
print("gameMode:", info.get("gameMode"))
print("gameType:", info.get("gameType"))
print("queueId:", info.get("queueId"))
print("mapId:", info.get("mapId"))
print("gameDuration:", info.get("gameDuration"))
print("gameVersion:", info.get("gameVersion"))

print()
print("===== Participants =====")

for i, p in enumerate(info.get("participants", []), start=1):
    print(
        i,
        "| champion:", p.get("championName"),
        "| kills:", p.get("kills"),
        "| deaths:", p.get("deaths"),
        "| assists:", p.get("assists"),
        "| win:", p.get("win")
    )
print()
print("===== Participant Identity Check =====")

for i, p in enumerate(info.get("participants", []), start=1):
    print(
        i,
        "| champion:", p.get("championName"),
        "| puuid:", p.get("puuid"),
        "| riotName:", p.get("riotIdGameName"),
        "| tag:", p.get("riotIdTagline")
    )
