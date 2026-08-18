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
participants = info["participants"]
teams = info["teams"]


print("========== TOP LEVEL ==========")
print(list(data.keys()))


print()
print("========== MATCH FIELDS ==========")

match_fields = [
    "gameId",
    "gameCreation",
    "gameStartTimestamp",
    "gameEndTimestamp",
    "gameDuration",
    "gameMode",
    "gameType",
    "gameVersion",
    "mapId",
    "platformId",
    "queueId"
]

for field in match_fields:
    print(field, "=", info.get(field))


print()
print("========== PARTICIPANT SAMPLE ==========")

p = participants[0]

participant_fields = [
    "participantId",
    "puuid",
    "riotIdGameName",
    "riotIdTagline",
    "teamId",

    "championId",
    "championName",
    "champLevel",

    "teamPosition",
    "individualPosition",

    "kills",
    "deaths",
    "assists",

    "goldEarned",

    "totalDamageDealtToChampions",
    "totalDamageTaken",

    "totalMinionsKilled",
    "neutralMinionsKilled",

    "visionScore",
    "wardsPlaced",
    "wardsKilled",

    "item0",
    "item1",
    "item2",
    "item3",
    "item4",
    "item5",
    "item6",

    "win"
]

for field in participant_fields:
    print(field, "=", p.get(field))


print()
print("========== TEAM SAMPLE ==========")

for team in teams:
    print(
        "teamId =", team.get("teamId"),
        "| win =", team.get("win")
    )


print()
print("========== ALL PARTICIPANT KEYS ==========")

for key in sorted(p.keys()):
    print(key)
