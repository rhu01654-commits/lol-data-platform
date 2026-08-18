import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_MATCH_DIR = PROJECT_ROOT / "data" / "raw" / "matches"


# ==========================================
# 统计变量
# ==========================================

total_files = 0
parse_errors = 0

match_ids = []
duplicate_match_ids = []

game_modes = Counter()
queue_ids = Counter()
map_ids = Counter()
patch_versions = Counter()
participant_counts = Counter()

bot_matches = 0
valid_pvp_matches = 0

durations = []
start_timestamps = []

missing_fields = Counter()


required_match_fields = [
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


seen_match_ids = set()


# ==========================================
# 遍历所有 JSON
# ==========================================

for file_path in sorted(RAW_MATCH_DIR.glob("*.json")):

    total_files += 1

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

    except Exception as e:

        parse_errors += 1

        print(
            "JSON parse error:",
            file_path.name,
            e
        )

        continue


    metadata = data.get("metadata", {})
    info = data.get("info", {})

    match_id = metadata.get("matchId")


    # ==========================================
    # Match ID 去重检查
    # ==========================================

    if match_id:

        if match_id in seen_match_ids:
            duplicate_match_ids.append(match_id)

        seen_match_ids.add(match_id)
        match_ids.append(match_id)

    else:
        missing_fields["metadata.matchId"] += 1


    # ==========================================
    # 必要字段缺失检查
    # ==========================================

    for field in required_match_fields:

        if info.get(field) is None:
            missing_fields[field] += 1


    # ==========================================
    # 基础统计
    # ==========================================

    game_mode = info.get("gameMode")
    queue_id = info.get("queueId")
    map_id = info.get("mapId")
    game_version = info.get("gameVersion")

    participants = info.get(
        "participants",
        []
    )


    game_modes[game_mode] += 1
    queue_ids[queue_id] += 1
    map_ids[map_id] += 1

    participant_counts[
        len(participants)
    ] += 1


    # ==========================================
    # Patch，例如 16.16.804... -> 16.16
    # ==========================================

    if game_version:

        parts = game_version.split(".")

        if len(parts) >= 2:

            patch = (
                f"{parts[0]}.{parts[1]}"
            )

            patch_versions[patch] += 1


    # ==========================================
    # Duration
    # ==========================================

    duration = info.get("gameDuration")

    if isinstance(duration, (int, float)):
        durations.append(duration)


    # ==========================================
    # 日期范围
    # ==========================================

    start_ts = info.get(
        "gameStartTimestamp"
    )

    if isinstance(start_ts, (int, float)):
        start_timestamps.append(start_ts)


    # ==========================================
    # BOT 检查
    # ==========================================

    has_bot = any(
        p.get("puuid") == "BOT"
        for p in participants
    )

    if has_bot:
        bot_matches += 1


    # ==========================================
    # 当前项目 V1 有效 PvP 定义
    # ==========================================

    is_valid_pvp = (
        len(participants) == 10
        and not has_bot
        and map_id == 11
    )

    if is_valid_pvp:
        valid_pvp_matches += 1


# ==========================================
# 输出结果
# ==========================================

print()
print("=" * 60)
print("DATASET PROFILE")
print("=" * 60)

print()
print("===== BASIC =====")

print("JSON files:", total_files)
print("Parsed matches:", len(match_ids))
print("Parse errors:", parse_errors)

print(
    "Unique match IDs:",
    len(set(match_ids))
)

print(
    "Duplicate match IDs:",
    len(duplicate_match_ids)
)


print()
print("===== MATCH TYPE =====")

print("Valid PvP matches:", valid_pvp_matches)
print("BOT matches:", bot_matches)


print()
print("===== PARTICIPANT COUNT =====")

for count, n in sorted(
    participant_counts.items()
):
    print(
        f"{count} participants:",
        n
    )


print()
print("===== GAME MODE =====")

for mode, n in game_modes.most_common():
    print(mode, ":", n)


print()
print("===== QUEUE ID =====")

for queue, n in queue_ids.most_common():
    print(queue, ":", n)


print()
print("===== MAP ID =====")

for map_id, n in map_ids.most_common():
    print(map_id, ":", n)


print()
print("===== PATCH =====")

for patch, n in patch_versions.most_common():
    print(patch, ":", n)


print()
print("===== GAME DURATION =====")

if durations:

    print(
        "Minimum:",
        min(durations),
        "seconds"
    )

    print(
        "Maximum:",
        max(durations),
        "seconds"
    )

    print(
        "Average:",
        round(mean(durations), 2),
        "seconds"
    )

    print(
        "Median:",
        round(median(durations), 2),
        "seconds"
    )


print()
print("===== DATE RANGE (UTC) =====")

if start_timestamps:

    min_date = datetime.fromtimestamp(
        min(start_timestamps) / 1000,
        tz=timezone.utc
    )

    max_date = datetime.fromtimestamp(
        max(start_timestamps) / 1000,
        tz=timezone.utc
    )

    print(
        "Earliest:",
        min_date.isoformat()
    )

    print(
        "Latest:",
        max_date.isoformat()
    )


print()
print("===== MISSING FIELDS =====")

if missing_fields:

    for field, n in (
        missing_fields.most_common()
    ):
        print(field, ":", n)

else:
    print(
        "No missing required match fields."
    )


print()
print("=" * 60)
print("PROFILE FINISHED")
print("=" * 60)
