# Architecture

The project is split into a small Python package plus service-specific layers. The package does extraction, validation, and loading. dbt owns analytical transformations. Airflow owns scheduling. Streamlit only reads already-modeled tables.

## Flow

1. Resolve the configured TLC monthly Parquet file.
2. Download the file to `data/raw/` if it is missing.
3. Read Parquet into records.
4. Validate schema and row-level quality rules.
5. Write a JSON quality report and rejected-record file.
6. Load accepted and flagged records into PostgreSQL.
7. Run dbt staging and mart models.
8. Read mart tables in Streamlit.

## Why This Shape

Keeping validation in Python makes it testable without a warehouse. Keeping metrics in dbt makes business logic visible in SQL and gives us dbt tests for modeled tables. Keeping Airflow thin avoids a common beginner mistake: hiding core logic inside DAG files where it is hard to test.

## Operational Notes

- The pipeline is rerunnable. The raw table has a unique constraint on `dataset_name` and `trip_hash`; the fingerprint is a best-effort duplicate heuristic and cannot uniquely identify trips that have exactly the same input values.
- Rejected records are persisted as JSON so they can be inspected after a failed or suspicious run.
- The monthly file name is generated from `taxi_type`, `year`, and `month`. The CLI can discover the latest published 2026 month and can run a bounded row sample for smoke checks.
- The dashboard should be treated as a read-only consumer of dbt marts.
