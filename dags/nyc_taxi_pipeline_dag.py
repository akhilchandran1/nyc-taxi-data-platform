"""Monthly NYC TLC ingestion and analytics refresh.

Requires Airflow 3, the standard provider, the taxi package and dbt to be
installed in the worker environment. Configure PROJECT_ROOT for dbt commands.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

try:
    from airflow.providers.standard.operators.bash import BashOperator
    from airflow.sdk import DAG
except ImportError:
    dag = None
else:
    with DAG(
        dag_id="nyc_taxi_monthly_pipeline",
        description="Ingest the latest published yellow taxi data and refresh analytics.",
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        schedule="@monthly",
        catchup=False,
        max_active_runs=1,
        default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
        tags=["nyc-taxi", "data-quality"],
    ) as dag:
        ingest = BashOperator(
            task_id="extract_validate_load",
            bash_command="taxi-pipeline --latest",
            execution_timeout=timedelta(hours=2),
        )
        transform = BashOperator(
            task_id="dbt_build",
            bash_command=(
                'cd "${PROJECT_ROOT:-/opt/airflow/project}/dbt" && dbt build --profiles-dir .'
            ),
            execution_timeout=timedelta(hours=2),
        )
        ingest >> transform
