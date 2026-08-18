from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    explode,
    size,
    regexp_extract,
    from_unixtime,
    to_date,
    when
)

spark = (
    SparkSession.builder
    .appName("lol-player-match-preview")
    .getOrCreate()
)

# HDFS 中的 Riot 原始 Match JSON
input_path = (
    "hdfs://localhost:9000/"
    "lol-data-platform/raw/riot_api/matches/"
    "ingest_date=2026-08-16/*.json"
)

# 每个 Riot JSON 文件是一个多行 JSON 对象
matches = (
    spark.read
    .option("multiLine", "true")
    .json(input_path)
)

print("\n===== MATCH COUNT =====")
print("Matches:", matches.count())


print("\n===== PARTICIPANT COUNT DISTRIBUTION =====")

matches.select(
    col("metadata.matchId").alias("match_id"),
    size(col("info.participants")).alias("participant_count")
).show(30, truncate=False)


# 一场比赛 → 多个玩家
players = matches.select(
    col("metadata.matchId").alias("match_id"),

    col("info.platformId").alias("platform_id"),

    col("info.gameVersion").alias("game_version"),

    regexp_extract(
        col("info.gameVersion"),
        r"^([0-9]+\.[0-9]+)",
        1
    ).alias("patch_version"),

    to_date(
        from_unixtime(
            col("info.gameStartTimestamp") / 1000
        )
    ).alias("dt"),

    when(
        col("info.gameMode").isNotNull(),
        col("info.gameMode")
    ).alias("game_mode"),

    col("info.queueId").alias("queue_id"),

    explode(
        col("info.participants")
    ).alias("player")
)


player_dwd = players.select(
    "match_id",
    "platform_id",
    "game_version",
    "patch_version",
    "dt",
    "game_mode",
    "queue_id",

    col("player.participantId").alias("participant_id"),
    col("player.puuid").alias("puuid"),

    col("player.teamId").alias("team_id"),

    col("player.championId").alias("champion_id"),
    col("player.championName").alias("champion_name"),

    col("player.teamPosition").alias("team_position"),
    col("player.individualPosition").alias("individual_position"),

    col("player.champLevel").alias("champ_level"),

    col("player.kills").alias("kills"),
    col("player.deaths").alias("deaths"),
    col("player.assists").alias("assists"),

    col("player.goldEarned").alias("gold_earned"),

    col("player.totalDamageDealtToChampions")
        .alias("total_damage_dealt_to_champions"),

    col("player.totalDamageTaken")
        .alias("total_damage_taken"),

    col("player.totalMinionsKilled")
        .alias("total_minions_killed"),

    col("player.neutralMinionsKilled")
        .alias("neutral_minions_killed"),

    col("player.visionScore").alias("vision_score"),
    col("player.wardsPlaced").alias("wards_placed"),
    col("player.wardsKilled").alias("wards_killed"),

    col("player.item0").alias("item_0"),
    col("player.item1").alias("item_1"),
    col("player.item2").alias("item_2"),
    col("player.item3").alias("item_3"),
    col("player.item4").alias("item_4"),
    col("player.item5").alias("item_5"),
    col("player.item6").alias("item_6"),

    col("player.win").alias("win"),

    when(
        col("player.puuid") == "BOT",
        1
    ).otherwise(0).alias("is_bot_player"),

    when(
        col("player.gameEndedInEarlySurrender") == True,
        1
    ).otherwise(0).alias("is_early_surrender")
)


print("\n===== PLAYER-MATCH COUNT =====")
print("Player-match rows:", player_dwd.count())


print("\n===== PREVIEW =====")

player_dwd.select(
    "match_id",
    "participant_id",
    "champion_name",
    "team_position",
    "kills",
    "deaths",
    "assists",
    "gold_earned",
    "win",
    "is_bot_player",
    "dt"
).show(30, truncate=False)


print("\n===== SCHEMA =====")

player_dwd.printSchema()


spark.stop()
