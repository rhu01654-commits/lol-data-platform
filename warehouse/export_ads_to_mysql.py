import os
from pathlib import Path

from dotenv import load_dotenv
from pyspark.sql import SparkSession


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


MYSQL_HOST = os.getenv("MYSQL_ANALYTICS_HOST")
MYSQL_PORT = os.getenv("MYSQL_ANALYTICS_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_ANALYTICS_DB")
MYSQL_USER = os.getenv("MYSQL_ANALYTICS_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_ANALYTICS_PASSWORD")


required_values = {
    "MYSQL_ANALYTICS_HOST": MYSQL_HOST,
    "MYSQL_ANALYTICS_DB": MYSQL_DB,
    "MYSQL_ANALYTICS_USER": MYSQL_USER,
    "MYSQL_ANALYTICS_PASSWORD": MYSQL_PASSWORD,
}

missing = [
    key
    for key, value in required_values.items()
    if not value
]

if missing:
    raise ValueError(
        "Missing environment variables: "
        + ", ".join(missing)
    )


JDBC_URL = (
    f"jdbc:mysql://{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    "?useSSL=false"
    "&allowPublicKeyRetrieval=true"
    "&serverTimezone=Asia/Kuala_Lumpur"
)



TARGET_TABLE = "ads_champion_day_metrics_serving"
# ============================================================
# Spark
# ============================================================

spark = (
    SparkSession.builder
    .appName("lol-publish-ads-to-mysql")
    .enableHiveSupport()
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


try:

    # ========================================================
    # Read Hive ADS
    # ========================================================

    print("=" * 60)
    print("READ HIVE ADS")
    print("=" * 60)

    source_df = spark.table(
        "lol_dw.ads_champion_day_metrics"
    )

    source_count = source_df.count()

    print(
        "Hive source rows:",
        source_count
    )

    if source_count == 0:
        raise RuntimeError(
            "Hive ADS table is empty. "
            "MySQL publish aborted."
        )


    # ========================================================
    # Publish to MySQL
    # Full-refresh serving table
    # ========================================================

    print()
    print("=" * 60)
    print("PUBLISH TO MYSQL")
    print("=" * 60)

    (
        source_df
        .coalesce(1)
        .write
        .format("jdbc")
        .option(
            "url",
            JDBC_URL
        )
        .option(
            "dbtable",
            TARGET_TABLE
        )
        .option(
            "user",
            MYSQL_USER
        )
        .option(
            "password",
            MYSQL_PASSWORD
        )
        .option(
            "driver",
            "com.mysql.cj.jdbc.Driver"
        )
        .option(
            "batchsize",
            "1000"
        )
        .mode("overwrite")
        .save()
    )


    # ========================================================
    # Read Back Validation
    # ========================================================

    print()
    print("=" * 60)
    print("VALIDATE MYSQL")
    print("=" * 60)

    target_df = (
        spark.read
        .format("jdbc")
        .option(
            "url",
            JDBC_URL
        )
        .option(
            "dbtable",
            TARGET_TABLE
        )
        .option(
            "user",
            MYSQL_USER
        )
        .option(
            "password",
            MYSQL_PASSWORD
        )
        .option(
            "driver",
            "com.mysql.cj.jdbc.Driver"
        )
        .load()
    )

    target_count = target_df.count()

    print(
        "MySQL target rows:",
        target_count
    )


    if source_count != target_count:

        raise RuntimeError(
            "Row count mismatch: "
            f"Hive={source_count}, "
            f"MySQL={target_count}"
        )


    print()
    print("=" * 60)
    print("MYSQL SERVING PUBLISH SUCCESS")
    print("=" * 60)

    print(
        "Source:",
        "lol_dw.ads_champion_day_metrics"
    )

    print(
        "Target:",
        f"{MYSQL_DB}.{TARGET_TABLE}"
    )

    print(
        "Rows:",
        target_count
    )


finally:

    spark.stop()
