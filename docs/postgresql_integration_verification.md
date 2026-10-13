# PostgreSQL Integration Verification

Date: 2026-10-13

## Objective and Environment

Verify that the existing NYC Taxi pipeline can validate and load a bounded sample of real August 2026 NYC TLC yellow taxi records into PostgreSQL without mixing the verification data with existing project data.

- Database: PostgreSQL 17 via the existing Docker Compose `postgres` service
- Source file: `data/raw/yellow_tripdata_2026-08.parquet`
- Dataset: August 2026 NYC TLC yellow taxi Parquet
- Temporary ingestion schema: `ingest_check_20261013_094948`
- Temporary rollback schema: `rollback_check_20261013_094948`

The existing `public` schema was inspected before the run and left unchanged. It already contained 981 `raw_yellow_trips` rows and 1 `ingestion_runs` row.

## Test Method

- Used exactly the first 1,000 records from the August 2026 Parquet file.
- Used the existing bounded-read, validation, and PostgreSQL loading pipeline.
- Verified `current_schema()` and `search_path` before ingestion.
- Loaded into the isolated schema `ingest_check_20261013_094948`.
- Re-ran the same ingestion against the same schema to verify idempotency.
- Used a separate isolated schema, `rollback_check_20261013_094948`, for a controlled transaction rollback test.

## First Run Results

| Metric | Count |
| --- | ---: |
| Input rows | 1,000 |
| Accepted rows | 981 |
| Rejected rows | 19 |
| Flagged rows | 15 |
| Loaded rows | 981 |

Flagged rows are included in accepted rows and were loaded with `quality_status = 'flagged'`.

## Direct SQL Verification

The isolated ingestion schema contained 981 loaded rows after the first run.

Quality status counts:

| `quality_status` | Count |
| --- | ---: |
| `accepted` | 966 |
| `flagged` | 15 |

Timestamp checks:

| Check | Value |
| --- | --- |
| Minimum pickup timestamp | `2026-07-31 23:42:23` |
| Maximum pickup timestamp | `2026-08-01 01:02:19` |
| Minimum dropoff timestamp | `2026-07-31 23:50:22` |
| Maximum dropoff timestamp | `2026-08-01 01:38:05` |
| Null pickup timestamps | 0 |
| Null dropoff timestamps | 0 |

Monetary checks:

| Field | Nulls | Minimum | Maximum | Sum |
| --- | ---: | ---: | ---: | ---: |
| `fare_amount` | 0 | -70 | 200 | 16,029.50 |
| `total_amount` | 0 | -74.75 | 203 | 24,411.11 |

Airport fee preservation:

| Check | Value |
| --- | ---: |
| `airport_fee` nulls | 0 |
| `airport_fee` nonzero rows | 26 |
| `airport_fee` minimum | 0 |
| `airport_fee` maximum | 2 |
| `airport_fee` sum | 52.00 |

## Idempotency

The same 1,000-row ingestion was run a second time against `ingest_check_20261013_094948`.

| Check | Result |
| --- | ---: |
| Second-run loaded rows | 0 |
| Rows after second run | 981 |
| `ingestion_runs` rows after second run | 1 |

The existing `(dataset_name, trip_hash)` conflict handling prevented duplicate inserts.

## Transaction Rollback

A controlled PostgreSQL transaction test was run in `rollback_check_20261013_094948`.

| Check | Result |
| --- | ---: |
| Rows before transaction | 0 |
| Rows visible inside transaction before controlled failure | 1 |
| Rows after rollback | 0 |
| Probe rows after rollback | 0 |

The inserted probe record was rolled back after a deliberate exception inside a database transaction. This confirms basic PostgreSQL transaction rollback behavior in the isolated schema, but it does not yet test every possible failure path of the actual loader.

## Checks

- `py -m pytest`: 21 passed
- `py -m ruff check .`: all checks passed

## Limitations

- The sample was the first 1,000 records, not a random or representative sample.
- Full-volume ingestion was not verified.
- dbt models were not run as part of this verification.
- Airflow orchestration was not verified.
- Dashboard behavior was not verified.
- Temporary schemas were retained for traceability and later cleanup review.
