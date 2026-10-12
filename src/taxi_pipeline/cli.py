"""Command-line entrypoint for local pipeline execution."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from taxi_pipeline.config import PipelineConfig
from taxi_pipeline.extract import discover_available_datasets, latest_available_dataset
from taxi_pipeline.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NYC Taxi ETL pipeline")
    parser.add_argument("--source-path", type=Path, help="Local Parquet file override")
    parser.add_argument("--database-url", help="SQLAlchemy database URL override")
    parser.add_argument("--year", type=int, help="TLC dataset year")
    parser.add_argument("--month", type=int, help="TLC dataset month")
    parser.add_argument("--latest", action="store_true", help="Use the latest published month")
    parser.add_argument(
        "--all-available",
        action="store_true",
        help="Run every published month in the selected year/range",
    )
    parser.add_argument("--start-month", type=int, default=1, help="First month for discovery")
    parser.add_argument("--end-month", type=int, default=12, help="Last month for discovery")
    parser.add_argument(
        "--limit-rows",
        type=int,
        help="Read only the first N rows from each selected Parquet file",
    )
    parser.add_argument(
        "--no-load",
        action="store_true",
        help="Validate and write reports without loading a database",
    )
    args = parser.parse_args()

    config = PipelineConfig.from_env()
    if args.year is not None:
        config = replace(config, year=args.year)
    if args.month is not None:
        config = replace(config, month=args.month)

    if args.source_path and (args.latest or args.all_available):
        raise SystemExit("--source-path cannot be combined with --latest or --all-available")
    if args.latest and args.all_available:
        raise SystemExit("--latest and --all-available are mutually exclusive")

    configs = [config]
    if args.latest:
        latest = latest_available_dataset(config)
        configs = [replace(config, year=latest.year, month=latest.month)]
    elif args.all_available:
        available = discover_available_datasets(
            year=config.year,
            base_url=config.source_base_url,
            taxi_type=config.taxi_type,
            start_month=args.start_month,
            end_month=args.end_month,
        )
        if not available:
            raise SystemExit(f"no published yellow taxi files found for {config.year}")
        configs = [replace(config, year=item.year, month=item.month) for item in available]

    for selected_config in configs:
        summary = run_pipeline(
            selected_config,
            source_path=args.source_path,
            database_url=args.database_url,
            load_to_database=not args.no_load,
            limit_rows=args.limit_rows,
        )
        print(summary)


if __name__ == "__main__":
    main()
