from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("lol-spark-test").getOrCreate()

df = spark.createDataFrame(
    [(875, "Sett"), (157, "Yasuo"), (777, "Yone")],
    ["champion_id", "champion_name"]
)

df.show()
df.printSchema()

spark.stop()
