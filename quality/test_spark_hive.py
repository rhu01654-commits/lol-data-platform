from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("lol-test-spark-hive")
    .enableHiveSupport()
    .getOrCreate()
)

spark.sql("USE lol_dw")

print("===== DWD MATCH =====")
spark.sql("""
SELECT COUNT(*) AS cnt
FROM dwd_match
""").show()

print("===== DWD PLAYER MATCH =====")
spark.sql("""
SELECT COUNT(*) AS cnt
FROM dwd_player_match
""").show()

print("===== DWS =====")
spark.sql("""
SELECT COUNT(*) AS cnt
FROM dws_champion_day
""").show()

print("===== ADS =====")
spark.sql("""
SELECT COUNT(*) AS cnt
FROM ads_champion_day_metrics
""").show()

spark.stop()
