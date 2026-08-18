import argparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    explode,
    regexp_extract,
    from_unixtime,
    to_date,
    when,
    size,
    sum as spark_sum,
    input_file_name
)


# ============================================================
# 1. Parameters
# ============================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--batch-date",
    required=True,
    help="Pipeline batch date, format: YYYY-MM-DD"
)

args = parser.parse_args()

batch_date = args.batch_date


# ============================================================
# 2. Spark Session
# ============================================================

spark = (
    SparkSession.builder
    .appName("lol-build-dwd-player-match")
    .getOrCreate()
)


# ============================================================
# 3. Input / Output
# ============================================================

# Full Refresh:
# 每次读取 Raw Zone 中所有历史 ingest_date 分区
input_path = (
    "hdfs://localhost:9000/"
    "lol-data-platform/raw/riot_api/matches/"
    "ingest_date=*/*.json"
)

output_path = (
    "hdfs://localhost:9000/"
    "lol-data-platform/dwd/player_match"
)

print("Pipeline batch date:", batch_date)
print("Input path:", input_path)
print("Output path:", output_path)


# ============================================================
# 4. Extract
# ============================================================

# Riot 原始 JSON 是 multi-line JSON：
# 一个文件 = 一场比赛
#
# input_file_name() 会获取每条数据来自哪个 HDFS 文件，
# 再从路径中提取 ingest_date。
matches = (
    spark.read
    .option("multiLine", "true")
    .json(input_path)
    .withColumn(
        "source_ingest_date",
        regexp_extract(
            input_file_name(),
            r"ingest_date=([0-9]{4}-[0-9]{2}-[0-9]{2})",
            1
        )
    )
)

match_count = matches.count()

print("Input match count:", match_count)

if match_count == 0:
    spark.stop()
    raise ValueError("No match data found in Raw Zone")


# ============================================================
# 5. Calculate Expected Player-Match Count
# ============================================================

# 不再写死：
# 21 matches × 10 players = 210
#
# 而是动态计算：
# SUM(每场 participants 数量)
expected_player_count = (
    matches
    .select(
        size(
            col("info.participants")
        ).alias("participant_count")
    )
    .agg(
        spark_sum(
            "participant_count"
        ).alias("expected_count")
    )
    .collect()[0]["expected_count"]
)

if expected_player_count is None:
    spark.stop()
    raise ValueError(
        "Unable to calculate expected player-match count"
    )

print(
    "Expected player-match count:",
    expected_player_count
)


# ============================================================
# 6. Transform - Explode Participants
# ============================================================

# 原始粒度：
# 1 row = 1 match
#
# explode 后：
# 1 row = 1 player in 1 match
players = matches.select(

    col("metadata.matchId")
    .alias("match_id"),

    col("info.gameId")
    .cast("long")
    .alias("game_id"),

    col("info.platformId")
    .alias("platform_id"),

    from_unixtime(
        (
            col("info.gameStartTimestamp") / 1000
        ).cast("long")
    )
    .cast("timestamp")
    .alias("game_start_time"),

    col("info.gameMode")
    .alias("game_mode"),

    col("info.queueId")
    .cast("int")
    .alias("queue_id"),

    regexp_extract(
        col("info.gameVersion"),
        r"^([0-9]+\.[0-9]+)",
        1
    ).alias("patch_version"),

    # 从真实 HDFS 输入文件路径提取出来的采集日期
    col("source_ingest_date"),

    explode(
        col("info.participants")
    ).alias("player")
)


# ============================================================
# 7. Flatten - Build DWD Player-Match
# ============================================================

player_dwd = players.select(

    # ----------------------------
    # Match information
    # ----------------------------

    col("match_id"),

    col("game_id"),

    col("platform_id"),

    col("game_start_time"),

    col("game_mode"),

    col("queue_id"),

    col("patch_version"),


    # ----------------------------
    # Player identity
    # ----------------------------

    col("player.participantId")
    .cast("int")
    .alias("participant_id"),

    col("player.puuid")
    .alias("puuid"),

    col("player.teamId")
    .cast("int")
    .alias("team_id"),


    # ----------------------------
    # Champion
    # ----------------------------

    col("player.championId")
    .cast("int")
    .alias("champion_id"),

    col("player.championName")
    .alias("champion_name"),


    # ----------------------------
    # Position
    # ----------------------------

    col("player.teamPosition")
    .alias("team_position"),

    col("player.individualPosition")
    .alias("individual_position"),


    # ----------------------------
    # Combat statistics
    # ----------------------------

    col("player.champLevel")
    .cast("int")
    .alias("champ_level"),

    col("player.kills")
    .cast("int")
    .alias("kills"),

    col("player.deaths")
    .cast("int")
    .alias("deaths"),

    col("player.assists")
    .cast("int")
    .alias("assists"),


    # ----------------------------
    # Economy / Damage
    # ----------------------------

    col("player.goldEarned")
    .cast("long")
    .alias("gold_earned"),

    col("player.totalDamageDealtToChampions")
    .cast("long")
    .alias("total_damage_dealt_to_champions"),

    col("player.totalDamageTaken")
    .cast("long")
    .alias("total_damage_taken"),


    # ----------------------------
    # Farming / Vision
    # ----------------------------

    col("player.totalMinionsKilled")
    .cast("int")
    .alias("total_minions_killed"),

    col("player.neutralMinionsKilled")
    .cast("int")
    .alias("neutral_minions_killed"),

    col("player.visionScore")
    .cast("int")
    .alias("vision_score"),

    col("player.wardsPlaced")
    .cast("int")
    .alias("wards_placed"),

    col("player.wardsKilled")
    .cast("int")
    .alias("wards_killed"),


    # ----------------------------
    # Items
    # ----------------------------

    col("player.item0")
    .cast("int")
    .alias("item_0"),

    col("player.item1")
    .cast("int")
    .alias("item_1"),

    col("player.item2")
    .cast("int")
    .alias("item_2"),

    col("player.item3")
    .cast("int")
    .alias("item_3"),

    col("player.item4")
    .cast("int")
    .alias("item_4"),

    col("player.item5")
    .cast("int")
    .alias("item_5"),

    col("player.item6")
    .cast("int")
    .alias("item_6"),


    # ----------------------------
    # Result
    # ----------------------------

    col("player.win")
    .cast("boolean")
    .alias("win"),


    # ----------------------------
    # Data-quality / business flags
    # ----------------------------

    when(
        col("player.puuid") == "BOT",
        1
    )
    .otherwise(0)
    .alias("is_bot_player"),

    when(
        col("player.gameEndedInEarlySurrender") == True,
        1
    )
    .otherwise(0)
    .alias("is_early_surrender"),


    # ----------------------------
    # Ingestion date
    # ----------------------------

    col("source_ingest_date"),


    # ----------------------------
    # Business partition date
    # ----------------------------

    to_date(
        col("game_start_time")
    ).alias("dt")
)


# ============================================================
# 8. Data Quality Validation
# ============================================================

player_count = player_dwd.count()

print("Match count:", match_count)
print(
    "Expected player-match count:",
    expected_player_count
)
print(
    "Actual player-match count:",
    player_count
)

if player_count != expected_player_count:

    spark.stop()

    raise ValueError(
        "Player-match count mismatch: "
        f"expected={expected_player_count}, "
        f"actual={player_count}"
    )


# ============================================================
# 9. Load - Write DWD ORC
# ============================================================

# Full Refresh：
# 每次根据完整 Raw Zone 重建整个 player_match DWD。
#
# 当前数据量很小，这种方式：
# - 简单
# - 可重复执行
# - 不会 append 出重复数据
(
    player_dwd.write
    .mode("overwrite")
    .partitionBy("dt")
    .format("orc")
    .save(output_path)
)


# ============================================================
# 10. Success
# ============================================================

print(
    "DWD player_match written successfully."
)

print(
    "Output:",
    output_path
)

print(
    "Pipeline batch date:",
    batch_date
)


spark.stop()
