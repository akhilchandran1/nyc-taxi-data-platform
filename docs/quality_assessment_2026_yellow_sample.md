# 2026 Yellow Taxi Bounded Data Quality Assessment

Assessment date: 2026-10-13

## Source and Sampling

- Source URL: `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2026-08.parquet`
- Dataset month: August 2026
- Official URL verification: `curl.exe -I` returned `HTTP/1.1 200 OK`; `Content-Length` was `59043961`, matching the local file size.
- Local file: `data/raw/yellow_tripdata_2026-08.parquet`
- Full Parquet row count: 3,336,716
- Sample size: 10,000 records
- Sampling method: first 10,000 records from the Parquet file using the existing bounded reader, `read_parquet(path, limit_rows=10000)`. This was not a random, stratified, or representative sample.
- Pipeline mode: validation/reporting only, with `--no-load`; no PostgreSQL load was performed.

## Validation Results

Definitions:

- Accepted: records in `ValidationResult.accepted`, eligible for downstream load. This includes flagged records.
- Rejected: records with at least one hard-failure rule.
- Flagged: accepted records with non-fatal quality issues.
- Clean accepted: accepted records with no flags.
- Duplicate: records rejected by the `duplicate_trip` rule.

| Metric | Count | Percent of Sample |
| --- | ---: | ---: |
| Input rows | 10,000 | 100.00% |
| Accepted for load | 9,839 | 98.39% |
| Clean accepted | 9,539 | 95.39% |
| Flagged, still accepted | 300 | 3.00% |
| Rejected | 161 | 1.61% |
| Duplicate rows | 0 | 0.00% |

Count reconciliation: 9,839 accepted rows plus 161 rejected rows equals 10,000 input rows. The 9,839 accepted rows consist of 9,539 clean accepted rows plus 300 flagged accepted rows.

Rule counts:

| Rule | Severity | Count | Percent of Sample | Interpretation |
| --- | --- | ---: | ---: | --- |
| `non_positive_duration` | reject | 159 | 1.59% | Dropoff timestamp equals pickup timestamp in all observed cases. |
| `zero_distance` | flag | 275 | 2.75% | Zero-mile trips, corrections, or unusual records. Seven also had `non_positive_duration` and were rejected. |
| `zero_passenger_count` | flag | 33 | 0.33% | Potential dispatch/correction records; still accepted. |
| `excessive_duration` | reject | 1 | 0.01% | Duration exceeded 24 hours. |
| `invalid_trip_distance` | reject | 1 | 0.01% | Distance exceeded 150 miles. |

Rejected issue combinations:

| Issue Combination | Count |
| --- | ---: |
| `non_positive_duration` | 152 |
| `non_positive_duration`, `zero_distance` | 7 |
| `excessive_duration` | 1 |
| `invalid_trip_distance` | 1 |

Flagged accepted issue combinations:

| Issue Combination | Count |
| --- | ---: |
| `zero_distance` | 267 |
| `zero_passenger_count` | 32 |
| `zero_passenger_count`, `zero_distance` | 1 |

## Null Counts

Important columns in the 10,000-row sample:

| Column | Nulls | Percent |
| --- | ---: | ---: |
| `VendorID` | 0 | 0.00% |
| `tpep_pickup_datetime` | 0 | 0.00% |
| `tpep_dropoff_datetime` | 0 | 0.00% |
| `passenger_count` | 0 | 0.00% |
| `trip_distance` | 0 | 0.00% |
| `RatecodeID` | 0 | 0.00% |
| `store_and_fwd_flag` | 0 | 0.00% |
| `PULocationID` | 0 | 0.00% |
| `DOLocationID` | 0 | 0.00% |
| `payment_type` | 0 | 0.00% |
| `fare_amount` | 0 | 0.00% |
| `extra` | 0 | 0.00% |
| `mta_tax` | 0 | 0.00% |
| `tip_amount` | 0 | 0.00% |
| `tolls_amount` | 0 | 0.00% |
| `improvement_surcharge` | 0 | 0.00% |
| `total_amount` | 0 | 0.00% |
| `congestion_surcharge` | 0 | 0.00% |
| `Airport_fee` | 0 | 0.00% |
| `cbd_congestion_fee` | 0 | 0.00% |
| `request_source` | 10,000 | 100.00% |

The generated quality report records only non-zero null counts, so `request_source` is the only null entry in `data/processed/yellow_tripdata_2026-08.parquet.quality.json`.

## Schema Comparison

Actual Parquet columns:

| Column | Parquet Type | Pipeline Classification |
| --- | --- | --- |
| `VendorID` | `int32` | required |
| `tpep_pickup_datetime` | `timestamp[us]` | required |
| `tpep_dropoff_datetime` | `timestamp[us]` | required |
| `passenger_count` | `int64` | required |
| `trip_distance` | `double` | required |
| `RatecodeID` | `int64` | optional |
| `store_and_fwd_flag` | `large_string` | optional |
| `PULocationID` | `int32` | required |
| `DOLocationID` | `int32` | required |
| `payment_type` | `int64` | required |
| `fare_amount` | `double` | required |
| `extra` | `double` | required |
| `mta_tax` | `double` | required |
| `tip_amount` | `double` | required |
| `tolls_amount` | `double` | required |
| `improvement_surcharge` | `double` | required |
| `total_amount` | `double` | required |
| `congestion_surcharge` | `double` | optional |
| `Airport_fee` | `double` | optional |
| `cbd_congestion_fee` | `double` | optional |
| `request_source` | `large_string` | optional |

Measured differences:

- Missing required columns: none.
- Unexpected columns outside `KNOWN_COLUMNS`: none.
- Optional columns present: `Airport_fee`, `RatecodeID`, `cbd_congestion_fee`, `congestion_surcharge`, `request_source`, `store_and_fwd_flag`.
- Optional columns absent: `airport_fee`, the lowercase variant. The real file uses `Airport_fee`. This is a schema-name discrepancy only; this assessment did not verify any data-loss impact from the casing difference.

## Rejection Review

Definite data-quality problems:

- 159 rows had equal pickup and dropoff timestamps. All `non_positive_duration` cases in the sample were equal timestamps; none had dropoff before pickup.
- Seven of those 159 also had zero distance.
- One row had a 57.72-hour duration for a 5.9-mile trip, which triggered `excessive_duration`.
- One row had `trip_distance = 229.74` miles over about 35.6 minutes from pickup zone 132 to dropoff zone 37, which triggered `invalid_trip_distance`.

Potentially recoverable rejected records:

- 152 rejected rows had equal pickup and dropoff timestamps but positive distance and positive total amount. Representative examples include:
  - Row 11: pickup/dropoff `2026-08-01 00:45:02`, distance `1.89`, total `19.25`.
  - Row 19: pickup/dropoff `2026-08-01 00:11:39`, distance `1.57`, total `17.45`.
  - Row 101: pickup/dropoff `2026-08-01 00:02:11`, distance `1.32`, total `18.90`.
- These records have impossible durations under the current timestamp rule, but the positive distance and fare fields suggest they may be recoverable for metrics that do not depend on duration. They are not confirmed valid trips; additional TLC business-rule review would be needed before reclassifying them.

Suspicious but potentially legitimate accepted records:

- 267 accepted rows had `zero_distance` only. Some look like short same-zone trips, cancellations, or correction pairs.
- 33 accepted rows had `zero_passenger_count`; 32 had only that issue, and one also had `zero_distance`.
- Negative fare correction rows were present among zero-distance flagged records. They were not rejected because current money validation only rejects missing values and values below `-500`.

## Limitations

- The sample is the first 10,000 records, not a random, stratified, or representative sample.
- Results may be biased toward trips early in August 1, 2026.
- The assessment used existing validation thresholds exactly as implemented.
- The local raw file already existed before this assessment; its size matched the official URL's `Content-Length`.

## Recommended Next Actions

1. Add a small diagnostic report field that distinguishes clean accepted rows from flagged accepted rows, so downstream readers do not confuse `accepted_rows` with issue-free rows.
2. Add a bounded-sample regression fixture or documented command for periodically checking official TLC schema drift.
3. Review whether `non_positive_duration` should remain a hard reject for rows with positive distance and fare, or whether those rows should be quarantined separately for metrics that do not depend on duration.
