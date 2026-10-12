"""Environment-based configuration for the taxi pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TAXI_YEAR = 2026
DEFAULT_TAXI_MONTH = 8


@dataclass(frozen=True)
class PipelineConfig:
    """Runtime settings with safe local defaults."""

    database_url: str = "postgresql+psycopg://taxi:taxi@localhost:5432/nyc_taxi"
    source_base_url: str = "https://d37ci6vzurychx.cloudfront.net/trip-data"
    taxi_type: str = "yellow"
    year: int = DEFAULT_TAXI_YEAR
    month: int = DEFAULT_TAXI_MONTH
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")
    rejected_data_dir: Path = Path("data/rejected")
    log_level: str = "INFO"
    max_trip_distance_miles: float = 150.0
    max_trip_duration_hours: float = 24.0
    max_passenger_count: int = 8
    suspicious_distance_miles: float = 75.0
    suspicious_total_amount: float = 500.0

    @classmethod
    def from_env(cls) -> PipelineConfig:
        """Build config from environment variables and an optional local .env file."""

        from dotenv import load_dotenv

        load_dotenv(override=False)
        config = cls(
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            source_base_url=os.getenv("TAXI_DATA_BASE_URL", cls.source_base_url),
            taxi_type=os.getenv("TAXI_TYPE", cls.taxi_type),
            year=int(os.getenv("TAXI_YEAR", cls.year)),
            month=int(os.getenv("TAXI_MONTH", cls.month)),
            raw_data_dir=Path(os.getenv("RAW_DATA_DIR", str(cls.raw_data_dir))),
            processed_data_dir=Path(os.getenv("PROCESSED_DATA_DIR", str(cls.processed_data_dir))),
            rejected_data_dir=Path(os.getenv("REJECTED_DATA_DIR", str(cls.rejected_data_dir))),
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
        )
        if not 1 <= config.month <= 12:
            raise ValueError("TAXI_MONTH must be between 1 and 12")
        if not 2009 <= config.year <= 2100:
            raise ValueError("TAXI_YEAR is outside the supported range")
        if config.taxi_type != "yellow":
            raise ValueError("this pipeline currently supports yellow taxis only")
        return config

    @property
    def dataset_name(self) -> str:
        return f"{self.taxi_type}_tripdata_{self.year}-{self.month:02d}.parquet"

    @property
    def source_url(self) -> str:
        return f"{self.source_base_url.rstrip('/')}/{self.dataset_name}"

    @property
    def local_raw_path(self) -> Path:
        return self.raw_data_dir / self.dataset_name
