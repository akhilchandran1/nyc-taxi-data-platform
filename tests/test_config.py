from taxi_pipeline.config import PipelineConfig


def test_config_builds_tlc_dataset_url() -> None:
    config = PipelineConfig()

    assert config.dataset_name == "yellow_tripdata_2026-08.parquet"
    assert config.source_url.endswith("/yellow_tripdata_2026-08.parquet")


def test_config_supports_explicit_2026_month() -> None:
    config = PipelineConfig(year=2026, month=3)

    assert config.dataset_name == "yellow_tripdata_2026-03.parquet"
    assert config.source_url.endswith("/yellow_tripdata_2026-03.parquet")
