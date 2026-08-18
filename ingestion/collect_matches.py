import argparse
import json
import os
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# 1. Parameters
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
    default=20,
    help="Number of NEW valid PvP matches to collect"
)

parser.add_argument(
    "--matches-per-player",
    type=int,
    default=20,
    help="Number of recent matches queried per player"
)

args = parser.parse_args()

BATCH_DATE = args.batch_date
TARGET_NEW_MATCHES = args.target_new_matches
MATCHES_PER_PLAYER = args.matches_per_player


try:
    datetime.strptime(
        BATCH_DATE,
        "%Y-%m-%d"
    )
except ValueError:
    raise ValueError(
        "--batch-date must use YYYY-MM-DD"
    )

if TARGET_NEW_MATCHES < 0:
    raise ValueError(
        "--target-new-matches must be >= 0"
    )


# ============================================================
# 2. Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_MATCH_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "matches"
)

STATE_DIR = (
    PROJECT_ROOT
    / "data"
    / "state"
)

BATCH_STATE_DIR = (
    STATE_DIR
    / "batches"
)

RAW_MATCH_DIR.mkdir(
    parents=True,
    exist_ok=True
)

STATE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

BATCH_STATE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

STATE_FILE = (
    STATE_DIR
    / "collector_state.json"
)

BATCH_STATE_FILE = (
    BATCH_STATE_DIR
    / f"{BATCH_DATE}.json"
)


# ============================================================
# 3. Riot Configuration
# ============================================================

SEED_MATCH_ID = "TW2_439101259"

REGIONAL_HOST = (
    "https://sea.api.riotgames.com"
)

load_dotenv(
    PROJECT_ROOT / ".env"
)

API_KEY = os.getenv(
    "RIOT_API_KEY"
)

if not API_KEY:
    raise ValueError(
        "RIOT_API_KEY not found. "
        "Please check .env"
    )

HEADERS = {
    "X-Riot-Token": API_KEY
}


# ============================================================
# 4. Helpers
# ============================================================

def utc_now():

    return (
        datetime.now(timezone.utc)
        .isoformat()
    )


def write_json_atomic(
    path,
    data
):

    temp_path = Path(
        str(path) + ".tmp"
    )

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp_path.replace(path)


# ============================================================
# 5. Riot API Request
# ============================================================

def riot_get(
    url,
    params=None,
    max_retries=5
):

    for attempt in range(
        max_retries
    ):

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=15
            )

        except requests.RequestException as e:

            print(
                "Network error:",
                e
            )

            time.sleep(3)

            continue


        if response.status_code == 200:

            return response


        if response.status_code == 429:

            retry_after = (
                response.headers.get(
                    "Retry-After",
                    "5"
                )
            )

            try:

                wait_seconds = int(
                    retry_after
                )

            except ValueError:

                wait_seconds = 5


            print(
                "Rate limited (429). "
                f"Waiting {wait_seconds} seconds..."
            )

            time.sleep(
                wait_seconds + 1
            )

            continue


        if response.status_code in (
            401,
            403
        ):

            raise RuntimeError(
                "Riot API authorization failed "
                f"with HTTP {response.status_code}. "
                "Please refresh/check RIOT_API_KEY."
            )


        print(
            "Request failed:",
            response.status_code,
            url
        )

        return None


    print(
        "Max retries reached:",
        url
    )

    return None


# ============================================================
# 6. Save / Read Raw Match
# ============================================================

def save_match(
    match_id,
    match_data
):

    output_file = (
        RAW_MATCH_DIR
        / f"{match_id}.json"
    )

    if output_file.exists():

        return False


    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            match_data,
            f,
            ensure_ascii=False,
            indent=2
        )


    return True


def fetch_match_detail(
    match_id
):

    local_file = (
        RAW_MATCH_DIR
        / f"{match_id}.json"
    )


    if local_file.exists():

        with open(
            local_file,
            "r",
            encoding="utf-8"
        ) as f:

            return (
                json.load(f),
                False
            )


    url = (
        f"{REGIONAL_HOST}"
        f"/lol/match/v5/matches/"
        f"{match_id}"
    )

    response = riot_get(url)

    if response is None:

        return None, False


    match_data = (
        response.json()
    )

    created = save_match(
        match_id,
        match_data
    )


    return match_data, created


# ============================================================
# 7. PvP Validation
# ============================================================

def is_valid_pvp(
    match_data
):

    info = match_data.get(
        "info",
        {}
    )

    participants = info.get(
        "participants",
        []
    )


    if len(participants) != 10:
        return False


    if any(
        p.get("puuid") == "BOT"
        for p in participants
    ):
        return False


    if info.get("mapId") != 11:
        return False


    return True


# ============================================================
# 8. Extract Human Players
# ============================================================

def extract_human_puuids(
    match_data
):

    puuids = []

    participants = (
        match_data
        .get("info", {})
        .get("participants", [])
    )


    for participant in participants:

        puuid = participant.get(
            "puuid"
        )

        if (
            puuid
            and puuid != "BOT"
        ):

            puuids.append(
                puuid
            )


    return puuids


# ============================================================
# 9. Fetch Recent Match IDs
# ============================================================

def fetch_match_ids(
    puuid
):

    url = (
        f"{REGIONAL_HOST}"
        f"/lol/match/v5/matches/"
        f"by-puuid/{puuid}/ids"
    )

    params = {
        "start": 0,
        "count": MATCHES_PER_PLAYER
    }


    response = riot_get(
        url,
        params=params
    )


    if response is None:
        return []


    return response.json()


# ============================================================
# 10. Global Collector State
# ============================================================

def save_state(
    player_queue,
    seen_players,
    seen_matches,
    valid_matches
):

    state = {

        "player_queue":
            list(player_queue),

        "seen_players":
            sorted(seen_players),

        "seen_matches":
            sorted(seen_matches),

        "valid_matches":
            sorted(valid_matches)
    }


    write_json_atomic(
        STATE_FILE,
        state
    )


def load_state():

    if not STATE_FILE.exists():

        return None


    with open(
        STATE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# 11. Batch State
# ============================================================

def save_batch_state(
    status,
    started_at,
    batch_raw_match_ids,
    batch_valid_match_ids
):

    data = {

        "batch_date":
            BATCH_DATE,

        "status":
            status,

        "target_new_matches":
            TARGET_NEW_MATCHES,

        "new_raw_match_ids":
            sorted(
                batch_raw_match_ids
            ),

        "new_valid_match_ids":
            sorted(
                batch_valid_match_ids
            ),

        "started_at":
            started_at,

        "updated_at":
            utc_now()
    }


    if status == "completed":

        data["completed_at"] = (
            utc_now()
        )


    write_json_atomic(
        BATCH_STATE_FILE,
        data
    )


def load_batch_state():

    if not BATCH_STATE_FILE.exists():

        return None


    with open(
        BATCH_STATE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# 12. Initialize Batch
# ============================================================

existing_batch = (
    load_batch_state()
)


if existing_batch:

    existing_target = (
        existing_batch.get(
            "target_new_matches"
        )
    )


    if (
        existing_target
        != TARGET_NEW_MATCHES
    ):

        raise ValueError(
            "Existing batch state uses "
            f"target_new_matches={existing_target}, "
            f"but current run requested "
            f"{TARGET_NEW_MATCHES}."
        )


    batch_started_at = (
        existing_batch.get(
            "started_at"
        )
        or utc_now()
    )


    batch_raw_match_ids = set(
        existing_batch.get(
            "new_raw_match_ids",
            []
        )
    )


    batch_valid_match_ids = set(
        existing_batch.get(
            "new_valid_match_ids",
            []
        )
    )


    if (
        existing_batch.get("status")
        == "completed"
    ):

        print(
            "Batch already completed:",
            BATCH_DATE
        )

        print(
            "New raw matches:",
            len(
                batch_raw_match_ids
            )
        )

        print(
            "New valid PvP matches:",
            len(
                batch_valid_match_ids
            )
        )

        sys.exit(0)


    print(
        "Resuming incomplete batch:",
        BATCH_DATE
    )


else:

    batch_started_at = (
        utc_now()
    )

    batch_raw_match_ids = set()

    batch_valid_match_ids = set()

    save_batch_state(
        "in_progress",
        batch_started_at,
        batch_raw_match_ids,
        batch_valid_match_ids
    )


# ============================================================
# 13. Initialize Global Collector
# ============================================================

state = load_state()


if state:

    print(
        "Existing collector state found."
    )

    print(
        "Resuming previous collection..."
    )


    player_queue = deque(
        state["player_queue"]
    )

    seen_players = set(
        state["seen_players"]
    )

    seen_matches = set(
        state["seen_matches"]
    )

    valid_matches = set(
        state["valid_matches"]
    )


else:

    print(
        "Starting new collection..."
    )


    seed_file = (
        RAW_MATCH_DIR
        / f"{SEED_MATCH_ID}.json"
    )


    if not seed_file.exists():

        raise FileNotFoundError(
            f"Seed match not found: "
            f"{seed_file}"
        )


    with open(
        seed_file,
        "r",
        encoding="utf-8"
    ) as f:

        seed_match = json.load(f)


    seed_players = (
        extract_human_puuids(
            seed_match
        )
    )


    player_queue = deque(
        seed_players
    )

    seen_players = set()

    seen_matches = set()

    valid_matches = {
        SEED_MATCH_ID
    }


print()
print("=" * 60)

print(
    "Batch date:",
    BATCH_DATE
)

print(
    "Historical valid PvP matches:",
    len(valid_matches)
)

print(
    "New valid matches already in batch:",
    len(batch_valid_match_ids)
)

print(
    "Target new valid matches:",
    TARGET_NEW_MATCHES
)

print(
    "Players waiting:",
    len(player_queue)
)

print("=" * 60)


# ============================================================
# 14. Main Incremental Collection Loop
# ============================================================

while (
    player_queue
    and
    len(batch_valid_match_ids)
    < TARGET_NEW_MATCHES
):

    puuid = (
        player_queue.popleft()
    )


    if puuid in seen_players:
        continue


    seen_players.add(
        puuid
    )


    print()
    print("=" * 60)

    print(
        "Checking player",
        len(seen_players)
    )

    print("=" * 60)


    match_ids = fetch_match_ids(
        puuid
    )


    print(
        "Recent match IDs:",
        len(match_ids)
    )


    for match_id in match_ids:

        if (
            len(batch_valid_match_ids)
            >= TARGET_NEW_MATCHES
        ):
            break


        if match_id in seen_matches:
            continue


        match_data, newly_downloaded = (
            fetch_match_detail(
                match_id
            )
        )


        if match_data is None:
            continue


        # Only mark as seen after
        # match detail was obtained successfully.
        seen_matches.add(
            match_id
        )


        # Raw file newly downloaded during
        # this batch.
        if newly_downloaded:

            batch_raw_match_ids.add(
                match_id
            )

            save_batch_state(
                "in_progress",
                batch_started_at,
                batch_raw_match_ids,
                batch_valid_match_ids
            )


        info = match_data.get(
            "info",
            {}
        )

        participants = info.get(
            "participants",
            []
        )

        has_bot = any(
            p.get("puuid") == "BOT"
            for p in participants
        )


        print(
            match_id,
            "| players:",
            len(participants),
            "| bot:",
            has_bot,
            "| map:",
            info.get("mapId"),
            "| mode:",
            info.get("gameMode"),
            "| queue:",
            info.get("queueId")
        )


        valid_pvp = (
            is_valid_pvp(
                match_data
            )
        )


        if valid_pvp:

            new_global_valid = (
                match_id
                not in valid_matches
            )


            if new_global_valid:

                valid_matches.add(
                    match_id
                )


                # Only count matches that belong
                # to this new ingestion batch.
                if (
                    newly_downloaded
                    or
                    match_id
                    in batch_raw_match_ids
                ):

                    batch_valid_match_ids.add(
                        match_id
                    )


                print(
                    "NEW VALID PVP:",
                    len(
                        batch_valid_match_ids
                    ),
                    "/",
                    TARGET_NEW_MATCHES
                )


            new_players = (
                extract_human_puuids(
                    match_data
                )
            )


            for new_puuid in new_players:

                if (
                    new_puuid
                    not in seen_players
                    and
                    new_puuid
                    not in player_queue
                ):

                    player_queue.append(
                        new_puuid
                    )


        # Save after every successfully
        # processed match.
        save_state(
            player_queue,
            seen_players,
            seen_matches,
            valid_matches
        )


        save_batch_state(
            "in_progress",
            batch_started_at,
            batch_raw_match_ids,
            batch_valid_match_ids
        )


        time.sleep(0.2)


# ============================================================
# 15. Final Validation
# ============================================================

save_state(
    player_queue,
    seen_players,
    seen_matches,
    valid_matches
)


if (
    len(batch_valid_match_ids)
    < TARGET_NEW_MATCHES
):

    save_batch_state(
        "incomplete",
        batch_started_at,
        batch_raw_match_ids,
        batch_valid_match_ids
    )

    raise RuntimeError(
        "Collection stopped before target "
        "was reached. "
        f"Expected new valid matches="
        f"{TARGET_NEW_MATCHES}, "
        f"actual="
        f"{len(batch_valid_match_ids)}"
    )


save_batch_state(
    "completed",
    batch_started_at,
    batch_raw_match_ids,
    batch_valid_match_ids
)


# ============================================================
# 16. Summary
# ============================================================

print()
print("=" * 60)
print("Collection finished.")
print("=" * 60)

print(
    "Batch date:",
    BATCH_DATE
)

print(
    "New raw matches:",
    len(
        batch_raw_match_ids
    )
)

print(
    "New valid PvP matches:",
    len(
        batch_valid_match_ids
    )
)

print(
    "Total valid PvP matches:",
    len(valid_matches)
)

print(
    "Matches checked overall:",
    len(seen_matches)
)

print(
    "Players checked overall:",
    len(seen_players)
)

print(
    "Players waiting:",
    len(player_queue)
)

print(
    "Collector state:",
    STATE_FILE
)

print(
    "Batch state:",
    BATCH_STATE_FILE
)

print(
    "Raw directory:",
    RAW_MATCH_DIR
)
