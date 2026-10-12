from __future__ import annotations

import json
from pathlib import Path

import pytest

from taxi_pipeline.validate import validate_records, validate_schema

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "yellow_trips_synthetic.json"


def load_fixture() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_validate_records_splits_accepted_flagged_and_rejected_rows() -> None:
    result = validate_records(load_fixture())

    assert result.report.input_rows == 4
    assert result.report.accepted_rows == 2
    assert result.report.flagged_rows == 1
    assert result.report.rejected_rows == 2
    assert result.report.duplicate_rows == 1
    assert result.report.rule_counts["zero_distance"] == 1
    assert result.report.rule_counts["zero_passenger_count"] == 1
    assert result.report.rule_counts["non_positive_duration"] == 1


def test_validate_schema_reports_missing_required_columns() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        validate_schema({"VendorID", "trip_distance"})


def test_validate_records_reports_optional_2026_columns() -> None:
    record = load_fixture()[0]
    record.update(
        {
            "RatecodeID": 1,
            "store_and_fwd_flag": "N",
            "congestion_surcharge": 2.5,
            "Airport_fee": 0.0,
            "cbd_congestion_fee": 0.75,
            "request_source": "street_hail",
        }
    )

    result = validate_records([record])

    assert result.report.accepted_rows == 1
    assert result.report.optional_columns_present == [
        "Airport_fee",
        "RatecodeID",
        "cbd_congestion_fee",
        "congestion_surcharge",
        "request_source",
        "store_and_fwd_flag",
    ]
