"""Run the orchestration code offline with a deterministic fixture."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, func, select

from taxi_pipeline.config import PipelineConfig
from taxi_pipeline.load import raw_yellow_trips
from taxi_pipeline.pipeline import run_pipeline

FIXTURE = Path(__file__).parent / "fixtures/yellow_trips_synthetic.json"


def test_end_to_end_fixture_to_sqlite(tmp_path, monkeypatch):
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        "taxi_pipeline.pipeline.extract",
        lambda config, source_path=None, limit_rows=None: pd.DataFrame.from_records(records),
    )
    db = tmp_path / "fixture.db"
    url = f"sqlite+pysqlite:///{db}"
    config = PipelineConfig(
        processed_data_dir=tmp_path / "processed",
        rejected_data_dir=tmp_path / "rejected",
    )

    first = run_pipeline(config, database_url=url)
    rerun = run_pipeline(config, database_url=url)

    assert (first.accepted_rows, first.rejected_rows, first.flagged_rows) == (2, 2, 1)
    assert first.loaded_rows == 2
    assert rerun.loaded_rows == 0
    assert json.loads(Path(first.quality_report_path).read_text())["input_rows"] == 4
    assert len(json.loads(Path(first.rejected_records_path).read_text())) == 2
    with create_engine(url).connect() as conn:
        assert conn.scalar(select(func.count()).select_from(raw_yellow_trips)) == 2


def test_source_override_keeps_sample_separate(tmp_path, monkeypatch):
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        "taxi_pipeline.pipeline.extract",
        lambda config, source_path=None, limit_rows=None: pd.DataFrame.from_records(records),
    )
    config = PipelineConfig(
        processed_data_dir=tmp_path / "processed",
        rejected_data_dir=tmp_path / "rejected",
    )
    summary = run_pipeline(
        config, source_path=Path("sample_yellow_trips.parquet"), load_to_database=False
    )
    assert summary.dataset_name == "sample_yellow_trips.parquet"
    assert "sample_yellow_trips.parquet.quality.json" in summary.quality_report_path
