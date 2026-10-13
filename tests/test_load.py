from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, select

from taxi_pipeline.load import load_trips, raw_yellow_trips
from taxi_pipeline.validate import validate_records

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "yellow_trips_synthetic.json"


def test_load_trips_is_idempotent_for_dataset_hash() -> None:
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    result = validate_records(records)
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    first_insert = load_trips(
        engine, "yellow_tripdata_2026-08.parquet", result.accepted, result.report.as_dict()
    )
    second_insert = load_trips(
        engine, "yellow_tripdata_2026-08.parquet", result.accepted, result.report.as_dict()
    )

    with engine.connect() as connection:
        row_count = connection.execute(select(raw_yellow_trips.c.id)).all()

    assert first_insert == 2
    assert second_insert == 0
    assert len(row_count) == 2


def test_load_trips_preserves_2026_optional_columns() -> None:
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    nonzero_airport_fee = records[0] | {
        "RatecodeID": 1,
        "store_and_fwd_flag": "N",
        "congestion_surcharge": 2.5,
        "Airport_fee": 2.0,
        "cbd_congestion_fee": 0.75,
        "request_source": "street_hail",
    }
    zero_airport_fee = records[0] | {
        "tpep_pickup_datetime": "2026-08-01T08:30:00",
        "tpep_dropoff_datetime": "2026-08-01T08:48:00",
        "RatecodeID": 1,
        "store_and_fwd_flag": "N",
        "congestion_surcharge": 2.5,
        "Airport_fee": 0.0,
        "cbd_congestion_fee": 0.75,
        "request_source": "street_hail",
    }
    result = validate_records([nonzero_airport_fee, zero_airport_fee])
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    load_trips(engine, "yellow_tripdata_2026-08.parquet", result.accepted, result.report.as_dict())

    with engine.connect() as connection:
        rows = connection.execute(
            select(
                raw_yellow_trips.c.ratecode_id,
                raw_yellow_trips.c.store_and_fwd_flag,
                raw_yellow_trips.c.request_source,
                raw_yellow_trips.c.congestion_surcharge,
                raw_yellow_trips.c.airport_fee,
                raw_yellow_trips.c.cbd_congestion_fee,
            ).order_by(raw_yellow_trips.c.pickup_datetime)
        ).all()

    assert result.report.accepted_rows == 2
    assert "Airport_fee" in result.report.optional_columns_present
    assert [tuple(row) for row in rows] == [
        (1, "N", "street_hail", 2.5, 2.0, 0.75),
        (1, "N", "street_hail", 2.5, 0.0, 0.75),
    ]


def test_load_trips_preserves_lowercase_airport_fee() -> None:
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    records[0].update(
        {
            "RatecodeID": 1,
            "store_and_fwd_flag": "N",
            "congestion_surcharge": 2.5,
            "airport_fee": 2.0,
            "cbd_congestion_fee": 0.75,
            "request_source": "street_hail",
        }
    )
    result = validate_records([records[0]])
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    load_trips(engine, "yellow_tripdata_2026-08.parquet", result.accepted, result.report.as_dict())

    with engine.connect() as connection:
        row = connection.execute(
            select(
                raw_yellow_trips.c.ratecode_id,
                raw_yellow_trips.c.store_and_fwd_flag,
                raw_yellow_trips.c.request_source,
                raw_yellow_trips.c.congestion_surcharge,
                raw_yellow_trips.c.airport_fee,
                raw_yellow_trips.c.cbd_congestion_fee,
            )
        ).one()

    assert result.report.optional_columns_present == [
        "RatecodeID",
        "airport_fee",
        "cbd_congestion_fee",
        "congestion_surcharge",
        "request_source",
        "store_and_fwd_flag",
    ]
    assert tuple(row) == (1, "N", "street_hail", 2.5, 2.0, 0.75)
