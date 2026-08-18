from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, size

spark = (
    SparkSession.builder
    .appName("lol-inspect-match")
    .getOrCreate()
)

match_file = (
    "/home/rae/lol-data-platform/"
    "data/raw/matches/TW2_439101259.json"
)

# Riot 原始 JSON 是多行格式，因此需要 multiLine=true
df = (
    spark.read
    .option("multiLine", "true")
    .json(match_file)
)

print("\n===== MATCH BASIC INFO =====")

df.select(
    col("metadata.matchId").alias("match_id"),
    col("info.gameMode").alias("game_mode"),
    col("info.queueId").alias("queue_id"),
    size(col("info.participants")).alias("participant_count")
).show(truncate=False)


print("\n===== PARTICIPANTS BEFORE EXPLODE =====")

df.select(
    col("metadata.matchId").alias("match_id"),
    size(col("info.participants")).alias("participant_count")
).show()


print("\n===== PARTICIPANTS AFTER EXPLODE =====")

players = df.select(
    col("metadata.matchId").alias("match_id"),
    explode(col("info.participants")).alias("player")
)

players.select(
    "match_id",
    col("player.participantId").alias("participant_id"),
    col("player.championName").alias("champion_name"),
    col("player.teamPosition").alias("team_position"),
    col("player.kills").alias("kills"),
    col("player.deaths").alias("deaths"),
    col("player.assists").alias("assists"),
    col("player.win").alias("win")
).show(20, truncate=False)


print("\n===== PLAYER ROW COUNT =====")

print("Rows after explode:", players.count())

spark.stop()
