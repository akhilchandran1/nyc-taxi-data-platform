from __future__ import annotations

import urllib.error
from email.message import Message

import pandas as pd
import pytest

from taxi_pipeline.extract import build_dataset_url, discover_available_datasets, read_parquet


class FakeResponse:
    def __init__(self, status: int, size: int) -> None:
        self.status = status
        self.headers = Message()
        self.headers["Content-Length"] = str(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_build_dataset_url_uses_official_pattern() -> None:
    url = build_dataset_url("https://d37ci6vzurychx.cloudfront.net/trip-data", 2026, 8)

    assert url == (
        "https://d37ci6vzurychx.cloudfront.net/trip-data/"
        "yellow_tripdata_2026-08.parquet"
    )


def test_discover_available_datasets_skips_unpublished_months(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        url = request.full_url
        if url.endswith("2026-01.parquet"):
            return FakeResponse(200, 123)
        if url.endswith("2026-02.parquet"):
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        if url.endswith("2026-03.parquet"):
            return FakeResponse(200, 456)
        raise AssertionError(url)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    available = discover_available_datasets(
        year=2026,
        base_url="https://d37ci6vzurychx.cloudfront.net/trip-data",
        start_month=1,
        end_month=3,
    )

    assert [(item.year, item.month, item.size_bytes) for item in available] == [
        (2026, 1, 123),
        (2026, 3, 456),
    ]


def test_read_parquet_respects_limit_rows(tmp_path) -> None:
    path = tmp_path / "sample.parquet"
    pd.DataFrame({"trip_id": [1, 2, 3], "total_amount": [10.0, 20.0, 30.0]}).to_parquet(
        path,
        index=False,
    )

    frame = read_parquet(path, limit_rows=2)

    assert len(frame) == 2
    assert frame["trip_id"].tolist() == [1, 2]


@pytest.mark.parametrize("limit_rows", [0, -1])
def test_read_parquet_rejects_non_positive_limit(tmp_path, limit_rows: int) -> None:
    path = tmp_path / "sample.parquet"
    pd.DataFrame({"trip_id": [1]}).to_parquet(path, index=False)

    with pytest.raises(ValueError, match="limit_rows must be positive"):
        read_parquet(path, limit_rows=limit_rows)


def test_read_parquet_allows_limit_larger_than_file(tmp_path) -> None:
    path = tmp_path / "sample.parquet"
    pd.DataFrame({"trip_id": [1, 2], "total_amount": [10.0, 20.0]}).to_parquet(
        path,
        index=False,
    )

    frame = read_parquet(path, limit_rows=10)

    assert len(frame) == 2
    assert frame["trip_id"].tolist() == [1, 2]
