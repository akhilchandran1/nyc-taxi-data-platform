# Engineering decisions

## Keep orchestration separate from business logic

The extraction, validation, and load code runs through a CLI. The Airflow DAG invokes that same CLI before running dbt, rather than embedding transformations inside Airflow tasks.

## Separate rejected records from quality flags

Invalid timestamps, extreme distances, and missing required values are rejected. Records with unusual but plausible values remain available for analysis with a quality flag. Rule thresholds are initial assumptions and should be revisited against actual TLC distributions.

## Avoid rerun duplicates

The loader uses `ON CONFLICT DO NOTHING` against the `(dataset_name, trip_hash)` constraint. The hash covers the modeled input fields after normalizing numeric and datetime representations. It is a duplicate-detection heuristic, **not** a TLC trip identifier: two distinct trips with identical source attributes may still have the same hash. For analytical completeness, row-level source identifiers or a source row offset would be preferable.

## Do not store raw monthly datasets in Git

The raw Parquet files are fetched on demand and ignored by Git. Tests use a small checked-in JSON fixture. Secrets and local service configuration also stay out of version control.

## Processing memory and performance

The default extractor loads a monthly Parquet file into a pandas DataFrame, then creates a list of dictionaries. That simplifies the first implementation but may use substantial memory for multi-million-row data. The `--limit-rows` option exists for bounded smoke checks against genuine TLC files; chunked production ingestion and a load benchmark are planned before scaling to multiple full months.
