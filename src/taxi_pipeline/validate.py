"""Schema profiling and record-level quality checks for yellow taxi trips."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

REQUIRED_COLUMNS = {
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "PULocationID",
    "DOLocationID",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "payment_type",
}

OPTIONAL_COLUMNS = {
    "RatecodeID",
    "store_and_fwd_flag",
    "congestion_surcharge",
    "Airport_fee",
    "airport_fee",
    "cbd_congestion_fee",
    "request_source",
}

KNOWN_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS

MONEY_COLUMNS = {
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
}

OPTIONAL_MONEY_COLUMNS = {
    "congestion_surcharge",
    "Airport_fee",
    "airport_fee",
    "cbd_congestion_fee",
}


@dataclass(frozen=True)
class QualityIssue:
    row_number: int
    severity: str
    rule: str
    message: str


@dataclass
class QualityReport:
    input_rows: int = 0
    accepted_rows: int = 0
    rejected_rows: int = 0
    flagged_rows: int = 0
    duplicate_rows: int = 0
    null_counts: dict[str, int] = field(default_factory=dict)
    rule_counts: dict[str, int] = field(default_factory=dict)
    optional_columns_present: list[str] = field(default_factory=list)
    unexpected_columns: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    accepted: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    flagged: list[dict[str, Any]]
    issues: list[QualityIssue]
    report: QualityReport


def validate_schema(columns: Iterable[str]) -> None:
    """Raise ValueError when required TLC fields are missing."""

    column_set = set(columns)
    missing = REQUIRED_COLUMNS.difference(column_set)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")


def dataframe_to_records(frame: Any) -> list[dict[str, Any]]:
    """Convert a pandas-like frame into dictionaries."""

    validate_schema(frame.columns)
    return frame.to_dict(orient="records")


def profile_records(records: list[dict[str, Any]]) -> QualityReport:
    report = QualityReport(input_rows=len(records))
    if records:
        column_set = set(records[0].keys())
        report.optional_columns_present = sorted(OPTIONAL_COLUMNS.intersection(column_set))
        report.unexpected_columns = sorted(column_set.difference(KNOWN_COLUMNS))
    null_counts: Counter[str] = Counter()
    for record in records:
        for column in REQUIRED_COLUMNS | OPTIONAL_COLUMNS.intersection(record.keys()):
            if _is_missing(record.get(column)):
                null_counts[column] += 1
    report.null_counts = dict(sorted(null_counts.items()))
    return report


def validate_records(
    records: list[dict[str, Any]],
    *,
    max_trip_distance_miles: float = 150.0,
    max_trip_duration_hours: float = 24.0,
    max_passenger_count: int = 8,
    suspicious_distance_miles: float = 75.0,
    suspicious_total_amount: float = 500.0,
) -> ValidationResult:
    """Validate rows and split them into accepted, rejected, and flagged sets."""

    if records:
        validate_schema(records[0].keys())

    report = profile_records(records)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    issues: list[QualityIssue] = []
    seen_hashes: set[str] = set()

    for row_number, raw_record in enumerate(records, start=1):
        record = dict(raw_record)
        record_issues: list[QualityIssue] = []
        row_hash = stable_trip_hash(record)
        record["trip_hash"] = row_hash

        if row_hash in seen_hashes:
            record_issues.append(
                _issue(row_number, "reject", "duplicate_trip", "duplicate trip row")
            )
        else:
            seen_hashes.add(row_hash)

        pickup = _parse_datetime(record.get("tpep_pickup_datetime"))
        dropoff = _parse_datetime(record.get("tpep_dropoff_datetime"))
        if pickup is None or dropoff is None:
            record_issues.append(
                _issue(row_number, "reject", "invalid_timestamp", "missing or invalid timestamp")
            )
        elif (pickup.tzinfo is None) != (dropoff.tzinfo is None):
            record_issues.append(
                _issue(row_number, "reject", "invalid_timestamp", "mixed timezone information")
            )
        elif dropoff <= pickup:
            record_issues.append(
                _issue(row_number, "reject", "non_positive_duration", "dropoff is not after pickup")
            )
        else:
            duration_hours = (dropoff - pickup).total_seconds() / 3600
            record["trip_duration_minutes"] = round(duration_hours * 60, 2)
            if duration_hours > max_trip_duration_hours:
                record_issues.append(
                    _issue(
                        row_number, "reject", "excessive_duration", "trip duration exceeds limit"
                    )
                )

        passenger_count = _to_int(record.get("passenger_count"))
        if passenger_count is None or passenger_count < 0 or passenger_count > max_passenger_count:
            record_issues.append(
                _issue(
                    row_number,
                    "reject",
                    "invalid_passenger_count",
                    "passenger count outside expected range",
                )
            )
        elif passenger_count == 0:
            record_issues.append(
                _issue(
                    row_number,
                    "flag",
                    "zero_passenger_count",
                    "zero passengers may be correction or dispatch record",
                )
            )

        distance = _to_decimal(record.get("trip_distance"))
        if distance is None or distance < 0 or distance > Decimal(str(max_trip_distance_miles)):
            record_issues.append(
                _issue(
                    row_number,
                    "reject",
                    "invalid_trip_distance",
                    "trip distance outside expected range",
                )
            )
        elif distance == 0:
            record_issues.append(
                _issue(
                    row_number,
                    "flag",
                    "zero_distance",
                    "zero distance may be cancellation or correction",
                )
            )
        elif distance > Decimal(str(suspicious_distance_miles)):
            record_issues.append(
                _issue(row_number, "flag", "suspicious_distance", "trip distance is unusually high")
            )

        for column in MONEY_COLUMNS | OPTIONAL_MONEY_COLUMNS.intersection(record.keys()):
            amount = _to_decimal(record.get(column))
            if column in OPTIONAL_MONEY_COLUMNS and amount is None:
                continue
            if amount is None:
                record_issues.append(
                    _issue(row_number, "reject", f"missing_{column}", f"{column} is missing")
                )
            elif amount < Decimal("-500"):
                record_issues.append(
                    _issue(
                        row_number,
                        "reject",
                        f"invalid_{column}",
                        f"{column} is below correction threshold",
                    )
                )

        total_amount = _to_decimal(record.get("total_amount"))
        if total_amount is not None and total_amount > Decimal(str(suspicious_total_amount)):
            record_issues.append(
                _issue(
                    row_number, "flag", "suspicious_total_amount", "total amount is unusually high"
                )
            )

        location_fields_ok = all(
            _to_int(record.get(column)) is not None for column in ("PULocationID", "DOLocationID")
        )
        if not location_fields_ok:
            record_issues.append(
                _issue(
                    row_number,
                    "reject",
                    "invalid_location_id",
                    "pickup or dropoff location is missing",
                )
            )

        hard_failures = [issue for issue in record_issues if issue.severity == "reject"]
        if hard_failures:
            record["quality_status"] = "rejected"
            record["quality_issues"] = [issue.rule for issue in record_issues]
            rejected.append(record)
        else:
            record["quality_status"] = "flagged" if record_issues else "accepted"
            record["quality_issues"] = [issue.rule for issue in record_issues]
            accepted.append(record)
            if record_issues:
                flagged.append(record)
        issues.extend(record_issues)

    rule_counts = Counter(issue.rule for issue in issues)
    report.accepted_rows = len(accepted)
    report.rejected_rows = len(rejected)
    report.flagged_rows = len(flagged)
    report.duplicate_rows = rule_counts.get("duplicate_trip", 0)
    report.rule_counts = dict(sorted(rule_counts.items()))
    return ValidationResult(accepted, rejected, flagged, issues, report)


def stable_trip_hash(record: dict[str, Any]) -> str:
    # Compare the complete business record; this is a duplicate heuristic, not a trip ID.
    fields = sorted(KNOWN_COLUMNS)
    parts = []
    for name in fields:
        value = record.get(name)
        if name in {"tpep_pickup_datetime", "tpep_dropoff_datetime"}:
            parsed = _parse_datetime(value)
            parts.append(parsed.isoformat() if parsed else "")
        elif name in MONEY_COLUMNS or name in OPTIONAL_MONEY_COLUMNS or name == "trip_distance":
            number = _to_decimal(value)
            parts.append(str(number.normalize()) if number is not None else "")
        elif name in {"VendorID", "passenger_count", "PULocationID", "DOLocationID", "payment_type"}:
            count = _to_int(value)
            parts.append(str(count) if count is not None else "")
        else:
            parts.append(str(value) if not _is_missing(value) else "")
    return sha256("|".join(parts).encode("utf-8")).hexdigest()


def _issue(row_number: int, severity: str, rule: str, message: str) -> QualityIssue:
    return QualityIssue(row_number=row_number, severity=severity, rule=rule, message=message)


def _parse_datetime(value: Any) -> datetime | None:
    if _is_missing(value):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None


def _to_decimal(value: Any) -> Decimal | None:
    if _is_missing(value):
        return None
    try:
        parsed = Decimal(str(value))
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(value: Any) -> int | None:
    if _is_missing(value):
        return None
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number != number.to_integral_value():
            return None
        return int(number)
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return None


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    # Handles pandas.NA/NaT as well as Python/NumPy NaN, without boolean ambiguity.
    return str(value).strip().lower() in {"", "nan", "nat", "none", "<na>"}
