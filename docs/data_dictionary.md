# Data Dictionary

## Raw Table: `raw_yellow_trips`

| Column | Meaning |
| --- | --- |
| `dataset_name` | Source TLC monthly file name. |
| `trip_hash` | Stable hash used for idempotency. |
| `vendor_id` | TLC vendor identifier. |
| `pickup_datetime` | Trip pickup timestamp. |
| `dropoff_datetime` | Trip dropoff timestamp. |
| `passenger_count` | Reported passenger count. |
| `trip_distance` | Trip distance in miles. |
| `ratecode_id` | TLC rate code when provided. |
| `store_and_fwd_flag` | Store-and-forward indicator when provided. |
| `request_source` | TLC request source field present in newer files. |
| `pickup_location_id` | TLC pickup zone identifier. |
| `dropoff_location_id` | TLC dropoff zone identifier. |
| `fare_amount` | Metered fare before extras, tolls, and tips. |
| `tip_amount` | Tip amount. |
| `tolls_amount` | Toll amount. |
| `congestion_surcharge` | Congestion surcharge when present in the TLC file. |
| `airport_fee` | Airport fee when present in the TLC file; mapped from `Airport_fee` in the 2026 source. |
| `cbd_congestion_fee` | Central Business District congestion fee present in newer TLC schemas. |
| `total_amount` | Total passenger charge. |
| `payment_type` | TLC payment type code. |
| `quality_status` | `accepted` or `flagged`. |
| `quality_issues` | JSON list of non-fatal quality rule names. |
| `loaded_at` | Ingestion timestamp. |

## Mart: `fct_yellow_trips`

Trip-level fact table derived from accepted and flagged rows. Revenue metrics use `total_amount` as gross revenue and keep `fare_amount`, `tip_amount`, and tolls separate for analysis.

## Mart: `daily_trip_metrics`

Daily aggregate table with trip counts, gross revenue, average fare, average total amount, average trip distance, average duration, and flagged trip counts.

## Mart: `hourly_pickup_metrics`

Daily pickup-hour aggregates for demand analysis, keyed by `trip_date` and `pickup_hour` so dashboard date filters apply.
