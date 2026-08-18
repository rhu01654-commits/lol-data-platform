#!/bin/bash

set -euo pipefail

# ============================================================
# Configuration
# ============================================================

PROJECT_HOME="/home/rae/lol-data-platform"

BATCH_DATE="${1:-}"

if [ -z "$BATCH_DATE" ]; then
    echo "Usage: ./run_daily_pipeline.sh YYYY-MM-DD"
    exit 1
fi

cd "$PROJECT_HOME"

source "$PROJECT_HOME/.venv/bin/activate"

export PYSPARK_PYTHON="$PROJECT_HOME/.venv/bin/python"

PIPELINE_START=$(date +%s)


echo "============================================"
echo "LOL Data Warehouse Pipeline"
echo "Batch Date: $BATCH_DATE"
echo "============================================"


# ============================================================
# Step 1 - DWD Match
# ============================================================

echo
echo "[1/6] Build dwd_match"

START=$(date +%s)

hive -f warehouse/sql/20_build_dwd_match.sql

END=$(date +%s)

echo "[TIME] dwd_match: $((END - START)) seconds"


# ============================================================
# Step 2 - DWD Player Match
# ============================================================

echo
echo "[2/6] Build dwd_player_match"

START=$(date +%s)

spark-submit \
    --master local[2] \
    warehouse/build_dwd_player_match.py \
    --batch-date "$BATCH_DATE"

# Spark 写 HDFS 后，让 Hive 注册分区
hive -S -e "
USE lol_dw;
MSCK REPAIR TABLE dwd_player_match;
"

END=$(date +%s)

echo "[TIME] dwd_player_match: $((END - START)) seconds"


# ============================================================
# Step 3 - DIM
# ============================================================

echo
echo "[3/6] Build dimensions"

START=$(date +%s)

hive -f warehouse/sql/30_build_dim.sql

END=$(date +%s)

echo "[TIME] dimensions: $((END - START)) seconds"


# ============================================================
# Step 4 - DWS
# ============================================================

echo
echo "[4/6] Build DWS"

START=$(date +%s)

hive -f warehouse/sql/40_build_dws.sql

END=$(date +%s)

echo "[TIME] DWS: $((END - START)) seconds"


# ============================================================
# Step 5 - ADS
# ============================================================

echo
echo "[5/6] Build ADS"

START=$(date +%s)

hive -f warehouse/sql/50_build_ads.sql

END=$(date +%s)

echo "[TIME] ADS: $((END - START)) seconds"


# ============================================================
# Step 6 - Data Quality
# ============================================================

echo
echo "[6/6] Run data quality checks"

START=$(date +%s)

spark-submit \
    --master local[2] \
    quality/run_dq_checks.py \
    --batch-date "$BATCH_DATE"

END=$(date +%s)

echo "[TIME] Data Quality: $((END - START)) seconds"


# ============================================================
# Pipeline Summary
# ============================================================

PIPELINE_END=$(date +%s)
TOTAL_TIME=$((PIPELINE_END - PIPELINE_START))

echo
echo "============================================"
echo "PIPELINE SUCCESS"
echo "Batch Date: $BATCH_DATE"
echo "Total Time: ${TOTAL_TIME} seconds"
echo "============================================"
