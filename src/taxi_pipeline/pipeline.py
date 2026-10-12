"""End-to-end pipeline orchestration for local and Airflow execution."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from taxi_pipeline.config import PipelineConfig
from taxi_pipeline.extract import extract
from taxi_pipeline.load import get_engine, load_trips
from taxi_pipeline.logging_config import configure_logging
from taxi_pipeline.validate import dataframe_to_records, validate_records

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineRunSummary:
    dataset_name: str
    accepted_rows: int
    rejected_rows: int
    flagged_rows: int
    loaded_rows: int
    quality_report_path: str
    rejected_records_path: str


def run_pipeline(
    config: PipelineConfig | None = None,
    *,
    source_path: Path | None = None,
    database_url: str | None = None,
    load_to_database: bool = True,
    limit_rows: int | None = None,
) -> PipelineRunSummary:
    """Run extraction, validation, quality reporting, and optional database load."""

    config = config or PipelineConfig.from_env()
    dataset_name = source_path.name if source_path is not None else config.dataset_name
    configure_logging(config.log_level)
    frame = extract(config, source_path=source_path, limit_rows=limit_rows)
    records = dataframe_to_records(frame)
    result = validate_records(
        records,
        max_trip_distance_miles=config.max_trip_distance_miles,
        max_trip_duration_hours=config.max_trip_duration_hours,
        max_passenger_count=config.max_passenger_count,
        suspicious_distance_miles=config.suspicious_distance_miles,
        suspicious_total_amount=config.suspicious_total_amount,
    )
    quality_report_path = _write_json(
        config.processed_data_dir / f"{dataset_name}.quality.json",
        result.report.as_dict(),
    )
    rejected_records_path = _write_json(
        config.rejected_data_dir / f"{dataset_name}.rejected.json",
        result.rejected,
    )
    loaded_rows = 0
    if load_to_database:
        engine = get_engine(database_url or config.database_url)
        try:
            loaded_rows = load_trips(
                engine, dataset_name, result.accepted, result.report.as_dict()
            )
        finally:
            engine.dispose()

    summary = PipelineRunSummary(
        dataset_name=dataset_name,
        accepted_rows=result.report.accepted_rows,
        rejected_rows=result.report.rejected_rows,
        flagged_rows=result.report.flagged_rows,
        loaded_rows=loaded_rows,
        quality_report_path=str(quality_report_path),
        rejected_records_path=str(rejected_records_path),
    )
    logger.info("pipeline completed", extra={"taxi_summary": asdict(summary)})
    return summary


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path
