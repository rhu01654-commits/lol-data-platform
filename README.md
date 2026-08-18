# League of Legends Data Platform

An end-to-end batch data engineering project that collects League of Legends match data from the Riot Games API, builds a layered offline data warehouse, performs automated data quality checks, publishes analytical data to a MySQL serving layer, and visualizes the results in Apache Superset.

## Project Overview

This project demonstrates a complete data engineering workflow from API ingestion to BI visualization.

Key engineering features include:

- Incremental and idempotent API ingestion
- Persistent collector state and per-batch manifests
- Raw data preservation
- HDFS date-partitioned storage
- Layered Hive data warehouse modeling
- Spark-based transformation and data quality validation
- DolphinScheduler workflow orchestration
- MySQL serving layer for low-latency BI queries
- Superset dashboard with interactive filters

---

## Architecture

```text
Riot Games API
      |
      v
Python Incremental Ingestion
      |
      +--------------------+
      |                    |
      v                    v
Local Raw JSON      State / Batch Manifest
      |
      v
HDFS Raw Layer
      |
      v
HDFS Staging JSONL
      |
      v
Hive ODS
      |
      v
DWD
├── dwd_match
└── dwd_player_match
      |
      v
DIM
├── dim_champion
├── dim_queue
└── dim_patch
      |
      v
DWS
└── dws_champion_day
      |
      v
ADS
└── ads_champion_day_metrics
      |
      v
Data Quality Gate
      |
      v
Spark JDBC Publish
      |
      v
MySQL Serving Layer
└── ads_champion_day_metrics_serving
      |
      v
Apache Superset Dashboard
