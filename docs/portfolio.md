# Demonstration notes

## Walkthrough outline (3–5 minutes)

1. Describe the dataset and the goal: turning monthly yellow taxi trip records into queryable analytics tables.
2. Run the tests and inspect the small input fixture, including invalid and flagged records.
3. Walk through `src/taxi_pipeline/` and the quality report produced by a local run.
4. Show a PostgreSQL load and rerun to demonstrate the uniqueness constraint (after verifying it locally).
5. Build dbt staging and mart models; explain the difference between raw fields and reported metrics.
6. Show the dashboard and date filters (after verifying the dashboard against database data).
7. Discuss limitations: full-file memory use, duplicate-detection trade-offs, and missing deployment verification.

## Resume / LinkedIn notes

When the project is demonstrated end-to-end, describe the technologies actually used and include measured outcomes only. Suitable examples after verification:

- Implemented a Python pipeline for NYC TLC Parquet data with record-level validation and reject/flag reporting.
- Modeled daily and hourly trip metrics in SQL/dbt on PostgreSQL.
- Added repeatable tests, database conflict handling, and a dashboard for trip/revenue trends.

Avoid publishing the suggested bullets as completed work until the corresponding tasks have been run and tested.
