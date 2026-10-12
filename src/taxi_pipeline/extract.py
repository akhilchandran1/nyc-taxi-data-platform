"""Dataset extraction utilities for NYC TLC Parquet files."""

from __future__ import annotations

import logging
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from taxi_pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class ExtractionError(RuntimeError):
    """Raised when source data cannot be fetched or read."""


@dataclass(frozen=True)
class AvailableDataset:
    year: int
    month: int
    url: str
    size_bytes: int | None

    @property
    def dataset_name(self) -> str:
        return f"yellow_tripdata_{self.year}-{self.month:02d}.parquet"


def build_dataset_url(base_url: str, year: int, month: int, taxi_type: str = "yellow") -> str:
    return f"{base_url.rstrip('/')}/{taxi_type}_tripdata_{year}-{month:02d}.parquet"


def discover_available_datasets(
    *,
    year: int,
    base_url: str,
    taxi_type: str = "yellow",
    start_month: int = 1,
    end_month: int = 12,
    timeout_seconds: int = 20,
) -> list[AvailableDataset]:
    """Return official monthly Parquet files that respond to HEAD requests."""

    if taxi_type != "yellow":
        raise ValueError("discovery currently supports yellow taxi files only")
    if not 1 <= start_month <= end_month <= 12:
        raise ValueError("month range must be within 1..12")

    available: list[AvailableDataset] = []
    for month in range(start_month, end_month + 1):
        url = build_dataset_url(base_url, year, month, taxi_type)
        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                if response.status == 200:
                    size_header = response.headers.get("Content-Length")
                    available.append(
                        AvailableDataset(
                            year=year,
                            month=month,
                            url=url,
                            size_bytes=int(size_header) if size_header else None,
                        )
                    )
        except urllib.error.HTTPError as exc:
            if exc.code in {403, 404}:
                logger.info("dataset is not published", extra={"taxi_url": url})
                continue
            raise ExtractionError(f"failed to check dataset availability: {url}") from exc
        except Exception as exc:
            raise ExtractionError(f"failed to check dataset availability: {url}") from exc
    return available


def latest_available_dataset(config: PipelineConfig) -> AvailableDataset:
    available = discover_available_datasets(
        year=config.year,
        base_url=config.source_base_url,
        taxi_type=config.taxi_type,
    )
    if not available:
        raise ExtractionError(f"no published {config.taxi_type} taxi files found for {config.year}")
    return available[-1]


def download_dataset(config: PipelineConfig, overwrite: bool = False) -> Path:
    """Download the configured TLC Parquet file if it is not already present."""

    destination = config.local_raw_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        logger.info("raw dataset already exists", extra={"taxi_path": str(destination)})
        return destination

    tmp_path = destination.with_suffix(".tmp")
    logger.info("downloading dataset", extra={"taxi_url": config.source_url})
    try:
        with (
            urllib.request.urlopen(config.source_url, timeout=60) as response,
            tmp_path.open("wb") as output,
        ):
            shutil.copyfileobj(response, output, length=1024 * 1024)
        tmp_path.replace(destination)
    except Exception as exc:  # pragma: no cover - network not used in unit tests
        if tmp_path.exists():
            tmp_path.unlink()
        raise ExtractionError(f"failed to download {config.source_url}") from exc
    return destination


def read_parquet(path: Path, limit_rows: int | None = None):
    """Read a Parquet file into a pandas DataFrame.

    Pandas and PyArrow are imported lazily so lightweight unit tests can run before
    runtime dependencies are installed.
    """

    try:
        import pandas as pd
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - exercised only on missing deps
        raise ExtractionError("pandas and pyarrow are required to read Parquet data") from exc

    logger.info("reading parquet file", extra={"taxi_path": str(path)})
    if limit_rows is not None:
        if limit_rows < 1:
            raise ValueError("limit_rows must be positive")
        parquet_file = pq.ParquetFile(path)
        tables = []
        remaining = limit_rows
        for row_group_index in range(parquet_file.num_row_groups):
            table = parquet_file.read_row_group(row_group_index)
            if table.num_rows > remaining:
                table = table.slice(0, remaining)
            tables.append(table)
            remaining -= table.num_rows
            if remaining <= 0:
                break
        if not tables:
            return pd.DataFrame()
        return pd.concat([table.to_pandas() for table in tables], ignore_index=True)
    return pd.read_parquet(path)


def extract(
    config: PipelineConfig, source_path: Path | None = None, limit_rows: int | None = None
):
    """Return trip records from a local override or the configured TLC source."""

    path = source_path if source_path else download_dataset(config)
    return read_parquet(path, limit_rows=limit_rows)
