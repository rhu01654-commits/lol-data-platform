USE lol_dw;

SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

CREATE TABLE IF NOT EXISTS ads_champion_day_metrics (
    patch_version STRING,
    queue_id INT,
    champion_id INT,
    champion_name STRING,

    match_count BIGINT,
    win_count BIGINT,

    win_rate DOUBLE,

    avg_kills DOUBLE,
    avg_deaths DOUBLE,
    avg_assists DOUBLE,

    kda_ratio DOUBLE,

    avg_gold DOUBLE,
    avg_damage DOUBLE
)
PARTITIONED BY (
    dt STRING
)
STORED AS ORC;


INSERT OVERWRITE TABLE ads_champion_day_metrics
PARTITION (dt)

SELECT
    patch_version,
    queue_id,
    champion_id,
    champion_name,

    match_count,
    win_count,

    CAST(win_count AS DOUBLE)
        / match_count AS win_rate,

    CAST(total_kills AS DOUBLE)
        / match_count AS avg_kills,

    CAST(total_deaths AS DOUBLE)
        / match_count AS avg_deaths,

    CAST(total_assists AS DOUBLE)
        / match_count AS avg_assists,

    CASE
        WHEN total_deaths = 0
        THEN CAST(total_kills + total_assists AS DOUBLE)
        ELSE CAST(total_kills + total_assists AS DOUBLE)
             / total_deaths
    END AS kda_ratio,

    CAST(total_gold AS DOUBLE)
        / match_count AS avg_gold,

    CAST(total_damage AS DOUBLE)
        / match_count AS avg_damage,

    dt

FROM dws_champion_day

WHERE match_count > 0;
