"""Database loading and idempotency controls."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

logger = logging.getLogger(__name__)

metadata = MetaData(schema=None)

ingestion_runs = Table(
    "ingestion_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("dataset_name", String(128), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("status", String(32), nullable=False),
    Column("quality_report", JSON().with_variant(Text(), "sqlite")),
    UniqueConstraint("dataset_name", name="uq_ingestion_runs_dataset_name"),
)

raw_yellow_trips = Table(
    "raw_yellow_trips",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("dataset_name", String(128), nullable=False),
    Column("trip_hash", String(64), nullable=False),
    Column("vendor_id", Integer),
    Column("pickup_datetime", DateTime),
    Column("dropoff_datetime", DateTime),
    Column("passenger_count", Integer),
    Column("trip_distance", Float),
    Column("ratecode_id", Integer),
    Column("store_and_fwd_flag", String(8)),
    Column("request_source", String(64)),
    Column("pickup_location_id", Integer),
    Column("dropoff_location_id", Integer),
    Column("fare_amount", Float),
    Column("extra", Float),
    Column("mta_tax", Float),
    Column("tip_amount", Float),
    Column("tolls_amount", Float),
    Column("improvement_surcharge", Float),
    Column("congestion_surcharge", Float),
    Column("airport_fee", Float),
    Column("cbd_congestion_fee", Float),
    Column("total_amount", Float),
    Column("payment_type", Integer),
    Column("quality_status", String(32), nullable=False),
    Column("quality_issues", Text, nullable=False, default="[]"),
    Column("loaded_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("dataset_name", "trip_hash", name="uq_raw_yellow_trips_dataset_hash"),
)


def get_engine(database_url: str):
    return create_engine(database_url, future=True)


def create_tables(engine) -> None:
    metadata.create_all(engine)
    ensure_raw_trip_columns(engine)


def ensure_raw_trip_columns(engine) -> None:
    """Add nullable columns introduced after the original demo schema."""

    existing_columns = {column["name"] for column in inspect(engine).get_columns("raw_yellow_trips")}
    missing_columns = {
        "ratecode_id": "INTEGER",
        "store_and_fwd_flag": "VARCHAR(8)",
        "request_source": "VARCHAR(64)",
        "congestion_surcharge": "DOUBLE PRECISION",
        "airport_fee": "DOUBLE PRECISION",
        "cbd_congestion_fee": "DOUBLE PRECISION",
    }.items()
    with engine.begin() as connection:
        for column_name, postgres_type in missing_columns:
            if column_name in existing_columns:
                continue
            column_type = "FLOAT" if engine.dialect.name == "sqlite" and "DOUBLE" in postgres_type else postgres_type
            connection.execute(
                text(f"ALTER TABLE raw_yellow_trips ADD COLUMN {column_name} {column_type}")
            )


def load_trips(
    engine, dataset_name: str, records: list[dict[str, Any]], quality_report: dict[str, Any]
) -> int:
    """Load accepted records while preserving idempotency via dataset/hash uniqueness."""

    create_tables(engine)
    inserted = 0
    now = datetime.now(UTC)
    with engine.begin() as connection:
        existing_run = connection.execute(
            select(ingestion_runs.c.id).where(ingestion_runs.c.dataset_name == dataset_name)
        ).first()
        if existing_run is None:
            connection.execute(
                ingestion_runs.insert().values(
                    dataset_name=dataset_name,
                    started_at=now,
                    status="running",
                    quality_report=_json_payload(quality_report, engine),
                )
            )

        before_count = _dataset_row_count(connection, dataset_name)
        dialect = engine.dialect.name
        if dialect == "postgresql":
            insert_statement = pg_insert(raw_yellow_trips)
        elif dialect == "sqlite":
            insert_statement = sqlite_insert(raw_yellow_trips)
        else:
            raise ValueError(f"unsupported database dialect: {dialect}")

        statement = insert_statement.on_conflict_do_nothing(
            index_elements=["dataset_name", "trip_hash"]
        )
        # Keep individual SQL statements modest while letting the driver batch inserts.
        batch_size = 500
        for offset in range(0, len(records), batch_size):
            batch = [
                _map_record(dataset_name, record, now)
                for record in records[offset : offset + batch_size]
            ]
            connection.execute(statement, batch)

        inserted = _dataset_row_count(connection, dataset_name) - before_count

        connection.execute(
            ingestion_runs.update()
            .where(ingestion_runs.c.dataset_name == dataset_name)
            .values(
                finished_at=datetime.now(UTC),
                status="succeeded",
                quality_report=_json_payload(quality_report, engine),
            )
        )
    logger.info(
        "loaded records", extra={"taxi_dataset": dataset_name, "taxi_inserted_rows": inserted}
    )
    return inserted


def _dataset_row_count(connection, dataset_name: str) -> int:
    return int(
        connection.execute(
            select(func.count()).select_from(raw_yellow_trips).where(
                raw_yellow_trips.c.dataset_name == dataset_name
            )
        ).scalar_one()
    )


def _map_record(dataset_name: str, record: dict[str, Any], loaded_at: datetime) -> dict[str, Any]:
    return {
        "dataset_name": dataset_name,
        "trip_hash": record["trip_hash"],
        "vendor_id": _int(record.get("VendorID")),
        "pickup_datetime": _datetime(record.get("tpep_pickup_datetime")),
        "dropoff_datetime": _datetime(record.get("tpep_dropoff_datetime")),
        "passenger_count": _int(record.get("passenger_count")),
        "trip_distance": _float(record.get("trip_distance")),
        "ratecode_id": _int(record.get("RatecodeID")),
        "store_and_fwd_flag": _string(record.get("store_and_fwd_flag")),
        "request_source": _string(record.get("request_source")),
        "pickup_location_id": _int(record.get("PULocationID")),
        "dropoff_location_id": _int(record.get("DOLocationID")),
        "fare_amount": _float(record.get("fare_amount")),
        "extra": _float(record.get("extra")),
        "mta_tax": _float(record.get("mta_tax")),
        "tip_amount": _float(record.get("tip_amount")),
        "tolls_amount": _float(record.get("tolls_amount")),
        "improvement_surcharge": _float(record.get("improvement_surcharge")),
        "congestion_surcharge": _float(record.get("congestion_surcharge")),
        "airport_fee": _float(_first_present(record, "Airport_fee", "airport_fee")),
        "cbd_congestion_fee": _float(record.get("cbd_congestion_fee")),
        "total_amount": _float(record.get("total_amount")),
        "payment_type": _int(record.get("payment_type")),
        "quality_status": record.get("quality_status", "accepted"),
        "quality_issues": json.dumps(record.get("quality_issues", [])),
        "loaded_at": loaded_at,
    }


def _json_payload(payload: dict[str, Any], engine) -> Any:
    if engine.dialect.name == "sqlite":
        return json.dumps(payload)
    return payload


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _first_present(record: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = record.get(name)
        if value is not None and value != "":
            return value
    return None


def _datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
