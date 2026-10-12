# Airflow scheduling

The monthly DAG is in `dags/nyc_taxi_pipeline_dag.py`. It calls `taxi-pipeline --latest`, which discovers the latest published yellow taxi file before loading data. This avoids blindly requesting an unpublished calendar month. The Python package handles extraction and loading, and dbt builds the SQL models.

This repository does **not** include a preconfigured Airflow deployment. The DAG requires an Airflow 3 environment with these components available to task workers:

- `apache-airflow-providers-standard` and the matching constrained Airflow version
- the installed `taxi-pipeline` package and its runtime dependencies
- dbt Core with the PostgreSQL adapter
- `PROJECT_ROOT` pointing to a mounted checkout containing `dbt/`
- PostgreSQL connection settings and a configured `dbt/profiles.yml`

Follow the [official Airflow installation instructions](https://airflow.apache.org/docs/apache-airflow/stable/installation/index.html) and use the version-specific constraints file for your Python version. Do not install Airflow by combining an unconstrained pip install with this project's requirements.

For initial development, use the CLI directly rather than setting up Airflow. The DAG source has been syntax-checked and can be imported without Airflow installed, but it must be imported and run within a configured Airflow environment before claiming successful scheduled runs.
