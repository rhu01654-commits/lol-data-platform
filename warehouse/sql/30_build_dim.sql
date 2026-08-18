USE lol_dw;

-- ========================================
-- DIM Champion
-- ========================================

INSERT OVERWRITE TABLE dim_champion
SELECT
    champion_id,
    MAX(champion_name) AS champion_name,
    MIN(dt) AS first_seen_dt,
    MAX(dt) AS last_seen_dt
FROM dwd_player_match
WHERE champion_id IS NOT NULL
GROUP BY champion_id;


-- ========================================
-- DIM Queue
-- ========================================

INSERT OVERWRITE TABLE dim_queue
SELECT
    queue_id,
    MAX(game_mode) AS game_mode,
    MIN(dt) AS first_seen_dt,
    MAX(dt) AS last_seen_dt
FROM dwd_match
WHERE queue_id IS NOT NULL
GROUP BY queue_id;


-- ========================================
-- DIM Patch
-- ========================================

INSERT OVERWRITE TABLE dim_patch
SELECT
    patch_version,
    MIN(dt) AS first_seen_dt,
    MAX(dt) AS last_seen_dt
FROM dwd_match
WHERE patch_version IS NOT NULL
  AND patch_version <> ''
GROUP BY patch_version;
