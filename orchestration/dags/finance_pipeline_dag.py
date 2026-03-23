"""Airflow DAG for the finance data platform pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {
    "owner": "finance-data-platform",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="finance_data_platform_pipeline",
    description="Run raw ingestion, transforms, analysis, and HTML reporting.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["finance", "portfolio", "pipeline"],
) as dag:
    ingest = BashOperator(
        task_id="ingest_raw",
        cwd="/opt/airflow/app",
        bash_command="PYTHONPATH=src python3 -m finance_data_platform.ingestion.run_ingest",
    )

    transform = BashOperator(
        task_id="transform_staged",
        cwd="/opt/airflow/app",
        bash_command="PYTHONPATH=src python3 -m finance_data_platform.transforms.run_transform",
    )

    analyze = BashOperator(
        task_id="analyze_curated",
        cwd="/opt/airflow/app",
        bash_command="PYTHONPATH=src python3 -m finance_data_platform.analysis.run_analyze",
    )

    report = BashOperator(
        task_id="render_reports",
        cwd="/opt/airflow/app",
        bash_command="PYTHONPATH=src python3 -m finance_data_platform.reporting.run_report",
    )

    ingest >> transform >> analyze >> report
