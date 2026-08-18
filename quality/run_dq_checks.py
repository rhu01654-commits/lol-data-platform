import argparse
import sys
import time
import uuid
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    TimestampType,
)


# ============================================================
# 1. Parameters
# ============================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--batch-date",
    required=True,
    help="Data batch date, format: YYYY-MM-DD"
)

args = parser.parse_args()

BATCH_DATE = args.batch_date


# ============================================================
# 2. Start Spark
# ============================================================

start_time = time.time()

spark = (
    SparkSession.builder
    .appName("lol-data-quality-check")
    .enableHiveSupport()
    .getOrCreate()
)

# 减少无关日志
spark.sparkContext.setLogLevel("WARN")

spark.sql("USE lol_dw")


# ============================================================
# 3. Run ID
# ============================================================

run_id = str(uuid.uuid4())
check_time = datetime.now()


# ============================================================
# 4. Data Quality Rules
# ============================================================

# 7 条规则一次提交给 Spark，
# 不再启动多次 Hive CLI / MapReduce Job。

dq_sql = """

SELECT
    'DQ01' AS rule_id,
    'match_id uniqueness' AS rule_name,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS status,
    CAST(COUNT(*) AS STRING) AS actual_value,
    '0' AS expected_value
FROM (
    SELECT match_id
    FROM dwd_match
    GROUP BY match_id
    HAVING COUNT(*) > 1
) t


UNION ALL


SELECT
    'DQ02',
    'match_id not null',
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END,
    CAST(COUNT(*) AS STRING),
    '0'
FROM dwd_match
WHERE match_id IS NULL


UNION ALL


SELECT
    'DQ03',
    '10 players per match',
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END,
    CAST(COUNT(*) AS STRING),
    '0'
FROM (
    SELECT match_id
    FROM dwd_player_match
    GROUP BY match_id
    HAVING COUNT(*) <> 10
) t


UNION ALL


SELECT
    'DQ04',
    'player-match uniqueness',
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END,
    CAST(COUNT(*) AS STRING),
    '0'
FROM (
    SELECT
        match_id,
        participant_id
    FROM dwd_player_match
    GROUP BY
        match_id,
        participant_id
    HAVING COUNT(*) > 1
) t


UNION ALL


SELECT
    'DQ05',
    'match = win + loss',
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END,
    CAST(COUNT(*) AS STRING),
    '0'
FROM dws_champion_day
WHERE match_count <> win_count + loss_count


UNION ALL


SELECT
    'DQ06',
    'win_rate range',
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END,
    CAST(COUNT(*) AS STRING),
    '0'
FROM ads_champion_day_metrics
WHERE win_rate IS NULL
   OR win_rate < 0
   OR win_rate > 1


UNION ALL


SELECT
    'DQ07',
    'DWS/ADS reconciliation',

    CASE
        WHEN d.dws_count = a.ads_count
        THEN 'PASS'
        ELSE 'FAIL'
    END,

    CONCAT(
        'DWS=',
        CAST(d.dws_count AS STRING),
        ', ADS=',
        CAST(a.ads_count AS STRING)
    ),

    'DWS count = ADS count'

FROM
    (
        SELECT COUNT(*) AS dws_count
        FROM dws_champion_day
    ) d

CROSS JOIN
    (
        SELECT COUNT(*) AS ads_count
        FROM ads_champion_day_metrics
    ) a

"""


# ============================================================
# 5. Execute Checks
# ============================================================

rows = spark.sql(dq_sql).collect()

checks = []

for row in rows:

    checks.append(
        (
            row["rule_id"],
            row["rule_name"],
            row["status"],
            row["actual_value"],
            row["expected_value"],
        )
    )


checks.sort(key=lambda x: x[0])


if len(checks) != 7:

    spark.stop()

    raise RuntimeError(
        f"Expected 7 DQ results, got {len(checks)}"
    )


# ============================================================
# 6. Print Report
# ============================================================

print("\n===== DATA QUALITY REPORT =====")

failed = 0

for (
    rule_id,
    rule_name,
    status,
    actual,
    expected
) in checks:

    print(
        f"{status:<4} | "
        f"{rule_id:<4} | "
        f"{rule_name:<30} | "
        f"{actual}"
    )

    if status != "PASS":
        failed += 1


# ============================================================
# 7. Persist DQ Results
# ============================================================

result_schema = StructType([
    StructField("run_id", StringType(), False),
    StructField("rule_id", StringType(), False),
    StructField("rule_name", StringType(), False),
    StructField("status", StringType(), False),
    StructField("actual_value", StringType(), True),
    StructField("expected_value", StringType(), True),
    StructField("check_time", TimestampType(), False),
    StructField("batch_date", StringType(), False),
])


result_rows = []

for (
    rule_id,
    rule_name,
    status,
    actual,
    expected
) in checks:

    result_rows.append(
        (
            run_id,
            rule_id,
            rule_name,
            status,
            actual,
            expected,
            check_time,
            BATCH_DATE,
        )
    )


result_df = spark.createDataFrame(
    result_rows,
    schema=result_schema
)


# 写入已有 Hive DQ 历史表
result_df.write \
    .mode("append") \
    .insertInto("dq_check_result")


# ============================================================
# 8. Summary
# ============================================================

elapsed = time.time() - start_time

print("---------------------------------------------")
print(f"Run ID       : {run_id}")
print(f"Batch date   : {BATCH_DATE}")
print(f"Total checks : {len(checks)}")
print(f"Passed       : {len(checks) - failed}")
print(f"Failed       : {failed}")
print(f"DQ time      : {elapsed:.2f} seconds")


# ============================================================
# 9. Exit
# ============================================================

spark.stop()


if failed > 0:
    print("DATA QUALITY CHECK FAILED")
    sys.exit(1)

print("DATA QUALITY CHECK PASSED")
