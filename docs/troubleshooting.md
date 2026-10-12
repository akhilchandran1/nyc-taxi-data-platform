# Troubleshooting

## Python command not found on Windows

Use the Python launcher (`py -3.12`) or activate the virtual environment and run `python`.

## Docker cannot access its configuration

Make sure Docker Desktop is running and that your current user has access to its configuration directory. Run `docker info` to confirm the engine is reachable; `docker --version` only confirms the client is installed.

## Parquet import fails

Install the project into the active virtual environment with `python -m pip install -e ".[dev,dbt,dashboard]"`.

## PostgreSQL connection refused

Start the database with `docker compose up -d postgres` and verify its health with `docker compose ps`. For local connections, use host `localhost` and port 5432.

## dbt cannot connect

Copy `dbt/profiles.yml.example` to `dbt/profiles.yml`, start PostgreSQL, then run `dbt debug --profiles-dir .` from `dbt/`.

## Dashboard reports missing tables

Run the loader and `dbt build` before launching Streamlit. The dashboard reads from dbt marts rather than directly from raw tables.

## A 2026 month is missing

TLC publishes monthly trip files on its own schedule. Use `python -m taxi_pipeline.cli --latest` to discover the latest available yellow taxi file instead of assuming the current month has been published.
