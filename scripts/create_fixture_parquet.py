"""Convert the checked-in test records to a small Parquet file for local runs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "tests/fixtures/yellow_trips_synthetic.json"
target = ROOT / "data/raw/sample_yellow_trips.parquet"
records = json.loads(source.read_text(encoding="utf-8"))
target.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame.from_records(records).to_parquet(target, index=False)
print(f"Created {target}")
