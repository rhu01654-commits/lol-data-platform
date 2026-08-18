import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# Parameters
# ============================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--batch-date",
    required=True,
    help="Batch date, format YYYY-MM-DD"
)

parser.add_argument(
    "--target-new-matches",
    type=int,
    default=20
)

args = parser.parse_args()

BATCH_DATE = args.batch_date
TARGET_NEW_MATCHES = (
    args.target_new_matches
)


try:
    datetime.strptime(
        BATCH_DATE,
        "%Y-%m-%d"
    )
except ValueError:
    raise ValueError(
        "--batch-date must use YYYY-MM-DD"
    )


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

COLLECT_SCRIPT = (
    PROJECT_ROOT
    / "ingestion"
    / "collect_matches.py"
)

PREPARE_SCRIPT = (
    PROJECT_ROOT
    / "ingestion"
    / "prepare_jsonl.py"
)

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "matches"
)

STAGING_FILE = (
    PROJECT_ROOT
    / "data"
    / "staging"
    / f"matches_{BATCH_DATE}.jsonl"
)

BATCH_STATE_FILE = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "batches"
    / f"{BATCH_DATE}.json"
)

HDFS_BIN = (
    "/home/rae/hadoop/bin/hdfs"
)

HDFS_RAW_DIR = (
    "/lol-data-platform/"
    "raw/riot_api/matches/"
    f"ingest_date={BATCH_DATE}"
)

HDFS_STAGING_DIR = (
    "/lol-data-platform/"
    "staging/riot_api/matches/"
    f"ingest_date={BATCH_DATE}"
)


# ============================================================
# Helper
# ============================================================

def run_command(command):

    print()
    print(
        "RUN:",
        " ".join(
            str(x)
            for x in command
        )
    )

    subprocess.run(
        [
            str(x)
            for x in command
        ],
        check=True
    )


# ============================================================
# Step 1 - Collect
# ============================================================

print("=" * 60)
print("STEP 1 - RIOT API COLLECTION")
print("=" * 60)

run_command([
    sys.executable,
    COLLECT_SCRIPT,
    "--batch-date",
    BATCH_DATE,
    "--target-new-matches",
    str(TARGET_NEW_MATCHES)
])


# ============================================================
# Step 2 - Prepare JSONL
# ============================================================

print()
print("=" * 60)
print("STEP 2 - PREPARE JSONL")
print("=" * 60)

run_command([
    sys.executable,
    PREPARE_SCRIPT,
    "--batch-date",
    BATCH_DATE
])


# ============================================================
# Step 3 - Load Batch Manifest
# ============================================================

with open(
    BATCH_STATE_FILE,
    "r",
    encoding="utf-8"
) as f:

    batch_state = json.load(f)


if (
    batch_state.get("status")
    != "completed"
):

    raise RuntimeError(
        "Batch state is not completed"
    )


raw_match_ids = (
    batch_state.get(
        "new_raw_match_ids",
        []
    )
)


# ============================================================
# Step 4 - Create HDFS Partitions
# ============================================================

print()
print("=" * 60)
print("STEP 3 - CREATE HDFS DIRECTORIES")
print("=" * 60)

run_command([
    HDFS_BIN,
    "dfs",
    "-mkdir",
    "-p",
    HDFS_RAW_DIR
])

run_command([
    HDFS_BIN,
    "dfs",
    "-mkdir",
    "-p",
    HDFS_STAGING_DIR
])


# ============================================================
# Step 5 - Upload Raw JSON
# ============================================================

print()
print("=" * 60)
print("STEP 4 - UPLOAD RAW MATCHES")
print("=" * 60)


for match_id in raw_match_ids:

    local_file = (
        RAW_DIR
        / f"{match_id}.json"
    )


    if not local_file.exists():

        raise FileNotFoundError(
            f"Raw file missing: "
            f"{local_file}"
        )


    run_command([
        HDFS_BIN,
        "dfs",
        "-put",
        "-f",
        local_file,
        HDFS_RAW_DIR
    ])


# ============================================================
# Step 6 - Upload JSONL Staging
# ============================================================

print()
print("=" * 60)
print("STEP 5 - UPLOAD STAGING JSONL")
print("=" * 60)


if not STAGING_FILE.exists():

    raise FileNotFoundError(
        f"Staging file missing: "
        f"{STAGING_FILE}"
    )


run_command([
    HDFS_BIN,
    "dfs",
    "-put",
    "-f",
    STAGING_FILE,
    HDFS_STAGING_DIR
])


# ============================================================
# Step 7 - Validation
# ============================================================

print()
print("=" * 60)
print("STEP 6 - VALIDATION")
print("=" * 60)


run_command([
    HDFS_BIN,
    "dfs",
    "-test",
    "-e",
    (
        f"{HDFS_STAGING_DIR}/"
        f"matches_{BATCH_DATE}.jsonl"
    )
])


for match_id in raw_match_ids:

    run_command([
        HDFS_BIN,
        "dfs",
        "-test",
        "-e",
        (
            f"{HDFS_RAW_DIR}/"
            f"{match_id}.json"
        )
    ])


# ============================================================
# Success
# ============================================================

print()
print("=" * 60)
print("DAILY INGESTION SUCCESS")
print("=" * 60)

print(
    "Batch date:",
    BATCH_DATE
)

print(
    "New raw files:",
    len(raw_match_ids)
)

print(
    "New valid PvP matches:",
    len(
        batch_state.get(
            "new_valid_match_ids",
            []
        )
    )
)

print(
    "HDFS Raw:",
    HDFS_RAW_DIR
)

print(
    "HDFS Staging:",
    HDFS_STAGING_DIR
)
