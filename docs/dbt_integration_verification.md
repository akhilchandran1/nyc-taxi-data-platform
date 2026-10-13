# Isolated dbt Integration Verification

Date: 2026-10-13

## Objective

Verify the existing dbt transformations against 981 real August 2026 NYC TLC yellow taxi records that were already loaded into PostgreSQL by the ingestion pipeline.

## Environment

- Database: PostgreSQL 17 via Docker Compose
- Source dataset: August 2026 NYC TLC yellow taxi Parquet, loaded through the Python pipeline
- Source schema: `ingest_check_20261013_094948`
- Source table: `raw_yellow_trips`
- Temporary dbt project copy: outside the tracked repository
- Temporary dbt profile: outside the tracked repository
- Isolated dbt staging schema: `dbt_check_20261013_094948_staging`
- Isolated dbt marts schema: `dbt_check_20261013_094948_marts`

## Isolation Checks

Before executing transformations:

- Confirmed the source schema contained 981 records.
- Confirmed the isolated dbt output schemas did not contain project tables.
- Confirmed no project hooks, macros, or model configuration targeted `public`, existing analytics schemas, or unrelated database objects.
- `dbt debug` passed using the temporary project and profile.
- `dbt compile` passed using the temporary project and profile.
- The compiled manifest was inspected before execution:
  - Source relations pointed to `ingest_check_20261013_094948`.
  - Model outputs pointed only to `dbt_check_20261013_094948_staging` and `dbt_check_20261013_094948_marts`.

## Model Results

`dbt run` completed successfully:

| Model | Materialization | Output Schema | Rows |
| --- | --- | --- | ---: |
| `stg_yellow_trips` | view | `dbt_check_20261013_094948_staging` | 981 |
| `dim_date` | table | `dbt_check_20261013_094948_marts` | 2 |
| `fct_yellow_trips` | table | `dbt_check_20261013_094948_marts` | 981 |
| `daily_trip_metrics` | table | `dbt_check_20261013_094948_marts` | 2 |
| `hourly_pickup_metrics` | table | `dbt_check_20261013_094948_marts` | 3 |

Summary: 5 of 5 models built successfully.

## dbt Tests

`dbt test` completed successfully.

| Result | Count |
| --- | ---: |
| Passed | 17 |
| Warnings | 0 |
| Errors | 0 |
| Skipped | 0 |

## Direct SQL Verification

Row counts:

| Relation | Rows |
| --- | ---: |
| `stg_yellow_trips` | 981 |
| `fct_yellow_trips` | 981 |
| `dim_date` | 2 |
| `daily_trip_metrics` | 2 |
| `hourly_pickup_metrics` | 3 |

Fact quality statuses:

| `quality_status` | Rows |
| --- | ---: |
| `accepted` | 966 |
| `flagged` | 15 |

Monetary preservation:

| Metric | Raw Source | Staging | Fact |
| --- | ---: | ---: | ---: |
| `sum(total_amount)` | 24,411.11 | 24,411.11 | 24,411.11 |
| `sum(airport_fee)` | 52.00 | 52.00 | 52.00 |

Airport fee detail:

| Check | Count |
| --- | ---: |
| Nonzero `airport_fee` fact records | 26 |

Daily aggregation checks:

| Trip Date | Trip Count | Gross Revenue | Flagged Trips |
| --- | ---: | ---: | ---: |
| `2026-07-31` | 5 | 165.63 | 0 |
| `2026-08-01` | 976 | 24,245.48 | 15 |

Hourly aggregation checks:

| Trip Date | Pickup Hour | Trip Count | Average Total Amount |
| --- | ---: | ---: | ---: |
| `2026-07-31` | 23 | 5 | 33.1260 |
| `2026-08-01` | 0 | 975 | 24.8371 |
| `2026-08-01` | 1 | 1 | 29.3000 |

## Existing Public Tables

Existing `public` tables were not modified by the isolated dbt run:

| Table | Rows After Verification |
| --- | ---: |
| `public.raw_yellow_trips` | 981 |
| `public.ingestion_runs` | 1 |

## Limitations

- The source records came from the first 1,000 rows of the August 2026 TLC yellow taxi Parquet file; 981 accepted or flagged rows were loaded and transformed.
- The sample is not random or representative.
- dbt was run from a temporary project copy and temporary profile, not the tracked dbt project in place.
- Full-volume dbt execution was not verified.
- Airflow orchestration was not verified.
- Dashboard behavior was not verified.
- Temporary PostgreSQL schemas were retained for traceability and later cleanup review.
