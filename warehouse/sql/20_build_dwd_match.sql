USE lol_dw;

-- MapReduce resource settings
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m;

SET mapreduce.reduce.memory.mb=1024;
SET mapreduce.reduce.java.opts=-Xmx768m;

-- Dynamic partition settings
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

-- 如果 Staging 出现新的 ingest_date 分区，
-- 自动注册到 ODS
MSCK REPAIR TABLE ods_match_raw;

INSERT OVERWRITE TABLE dwd_match
PARTITION (dt)

SELECT
    get_json_object(
        raw_json,
        '$.metadata.matchId'
    ) AS match_id,

    CAST(
        get_json_object(
            raw_json,
            '$.info.gameId'
        ) AS BIGINT
    ) AS game_id,

    get_json_object(
        raw_json,
        '$.info.platformId'
    ) AS platform_id,

    FROM_UNIXTIME(
        CAST(
            get_json_object(
                raw_json,
                '$.info.gameStartTimestamp'
            ) AS BIGINT
        ) DIV 1000
    ) AS game_start_time,

    FROM_UNIXTIME(
        CAST(
            get_json_object(
                raw_json,
                '$.info.gameEndTimestamp'
            ) AS BIGINT
        ) DIV 1000
    ) AS game_end_time,

    CAST(
        get_json_object(
            raw_json,
            '$.info.gameDuration'
        ) AS INT
    ) AS game_duration,

    get_json_object(
        raw_json,
        '$.info.gameMode'
    ) AS game_mode,

    get_json_object(
        raw_json,
        '$.info.gameType'
    ) AS game_type,

    CAST(
        get_json_object(
            raw_json,
            '$.info.queueId'
        ) AS INT
    ) AS queue_id,

    CAST(
        get_json_object(
            raw_json,
            '$.info.mapId'
        ) AS INT
    ) AS map_id,

    get_json_object(
        raw_json,
        '$.info.gameVersion'
    ) AS game_version,

    REGEXP_EXTRACT(
        get_json_object(
            raw_json,
            '$.info.gameVersion'
        ),
        '^([0-9]+\\.[0-9]+)',
        1
    ) AS patch_version,

    CASE
        WHEN INSTR(
            raw_json,
            '"puuid":"BOT"'
        ) > 0
        THEN 1
        ELSE 0
    END AS is_bot_match,

    CASE
        WHEN INSTR(
            raw_json,
            '"gameEndedInEarlySurrender":true'
        ) > 0
        THEN 1
        ELSE 0
    END AS is_early_surrender,

    ingest_date AS source_ingest_date,

    FROM_UNIXTIME(
        CAST(
            get_json_object(
                raw_json,
                '$.info.gameStartTimestamp'
            ) AS BIGINT
        ) DIV 1000,
        'yyyy-MM-dd'
    ) AS dt

FROM ods_match_raw;
