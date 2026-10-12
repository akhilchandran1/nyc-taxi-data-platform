"""Regression coverage for malformed and duplicated taxi records."""

from __future__ import annotations

import json
from pathlib import Path

from taxi_pipeline.validate import stable_trip_hash, validate_records

FIXTURE = Path(__file__).parent / "fixtures/yellow_trips_synthetic.json"


def rows():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_non_finite_values_are_rejected_without_crashing():
    record = rows()[0]
    record["trip_distance"] = float("inf")
    record["fare_amount"] = float("nan")
    result = validate_records([record])
    assert result.report.rejected_rows == 1
    assert "invalid_trip_distance" in result.report.rule_counts
    assert "missing_fare_amount" in result.report.rule_counts


def test_fractional_passenger_count_is_invalid():
    record = rows()[0]
    record["passenger_count"] = 1.5
    assert validate_records([record]).report.rule_counts["invalid_passenger_count"] == 1


def test_hash_uses_all_relevant_source_fields():
    left = rows()[0]
    right = {**left, "passenger_count": 2}
    assert stable_trip_hash(left) != stable_trip_hash(right)


def test_missing_tokens_are_consistently_rejected():
    record = rows()[0]
    record["tpep_pickup_datetime"] = "NaT"
    record["PULocationID"] = "<NA>"
    result = validate_records([record])
    assert result.report.rejected_rows == 1
    assert result.report.rule_counts["invalid_timestamp"] == 1
    assert result.report.rule_counts["invalid_location_id"] == 1


def test_mixed_timezone_timestamps_are_rejected():
    record = rows()[0]
    record["tpep_dropoff_datetime"] = "2026-08-01T08:18:00+00:00"
    result = validate_records([record])
    assert result.report.rejected_rows == 1
    assert result.report.rule_counts["invalid_timestamp"] == 1
