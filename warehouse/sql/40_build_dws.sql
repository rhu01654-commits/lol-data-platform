USE lol_dw;

SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

CREATE TABLE IF NOT EXISTS dws_champion_day (
    patch_version STRING,
    queue_id INT,
    champion_id INT,
    champion_name STRING,

    match_count BIGINT,
    win_count BIGINT,
    loss_count BIGINT,

    total_kills BIGINT,
    total_deaths BIGINT,
    total_assists BIGINT,

    total_gold BIGINT,
    total_damage BIGINT
)
PARTITIONED BY (
    dt STRING
)
STORED AS ORC;


INSERT OVERWRITE TABLE dws_champion_day
PARTITION (dt)

SELECT
    p.patch_version,
    p.queue_id,
    p.champion_id,
    MAX(p.champion_name) AS champion_name,

    COUNT(*) AS match_count,

    SUM(
        CASE WHEN p.win = true THEN 1 ELSE 0 END
    ) AS win_count,

    SUM(
        CASE WHEN p.win = false THEN 1 ELSE 0 END
    ) AS loss_count,

    SUM(p.kills) AS total_kills,
    SUM(p.deaths) AS total_deaths,
    SUM(p.assists) AS total_assists,

    SUM(p.gold_earned) AS total_gold,

    SUM(
        p.total_damage_dealt_to_champions
    ) AS total_damage,

    p.dt

FROM dwd_player_match p

JOIN dwd_match m
    ON p.match_id = m.match_id

WHERE m.is_bot_match = 0
  AND m.is_early_surrender = 0

GROUP BY
    p.dt,
    p.patch_version,
    p.queue_id,
    p.champion_id;
