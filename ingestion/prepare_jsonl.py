import argparse
import json
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

args = parser.parse_args()

BATCH_DATE = args.batch_date


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

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "matches"
)

STATE_FILE = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "batches"
    / f"{BATCH_DATE}.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "staging"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / f"matches_{BATCH_DATE}.jsonl"
)


# ============================================================
# Load Batch Manifest
# ============================================================

if not STATE_FILE.exists():

    raise FileNotFoundError(
        f"Batch state not found: "
        f"{STATE_FILE}"
    )


with open(
    STATE_FILE,
    "r",
    encoding="utf-8"
) as f:

    batch_state = json.load(f)


if (
    batch_state.get("status")
    != "completed"
):

    raise RuntimeError(
        "Batch is not completed. "
        f"Current status: "
        f"{batch_state.get('status')}"
    )


match_ids = (
    batch_state.get(
        "new_raw_match_ids",
        []
    )
)


# ============================================================
# Build JSONL
# ============================================================

count = 0


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as fout:

    for match_id in match_ids:

        file_path = (
            RAW_DIR
            / f"{match_id}.json"
        )


        if not file_path.exists():

            raise FileNotFoundError(
                f"Raw match missing: "
                f"{file_path}"
            )


        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as fin:

            data = json.load(fin)


        actual_match_id = (
            data
            .get("metadata", {})
            .get("matchId")
        )


        if (
            actual_match_id
            and
            actual_match_id != match_id
        ):

            raise ValueError(
                "Match ID mismatch: "
                f"filename={match_id}, "
                f"json={actual_match_id}"
            )


        json_line = json.dumps(
            data,
            ensure_ascii=False,
            separators=(",", ":")
        )


        fout.write(
            json_line + "\n"
        )

        count += 1


# ============================================================
# Validation
# ============================================================

if count != len(match_ids):

    raise RuntimeError(
        "JSONL count mismatch: "
        f"expected={len(match_ids)}, "
        f"actual={count}"
    )


print(
    "Batch date:",
    BATCH_DATE
)

print(
    "JSON files processed:",
    count
)

print(
    "Output:",
    OUTPUT_FILE
)
