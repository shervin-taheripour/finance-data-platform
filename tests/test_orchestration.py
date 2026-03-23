"""Offline smoke tests for Docker and Airflow orchestration assets."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_docker_compose_defines_expected_services() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))

    assert set(compose["services"]) == {
        "postgres",
        "airflow-init",
        "airflow-webserver",
        "airflow-scheduler",
    }
    assert compose["services"]["airflow-webserver"]["ports"] == ["8080:8080"]


def test_dockerfile_uses_airflow_base_image() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "FROM apache/airflow:" in dockerfile
    assert "pip install --no-cache-dir -e ." in dockerfile


def test_airflow_dag_file_is_valid_python_and_references_pipeline_steps() -> None:
    dag_path = Path("orchestration/dags/finance_pipeline_dag.py")

    dag_source = dag_path.read_text(encoding="utf-8")
    compile(dag_source, str(dag_path), "exec")
    assert "finance_data_platform_pipeline" in dag_source
    assert "finance_data_platform.ingestion.run_ingest" in dag_source
    assert "finance_data_platform.transforms.run_transform" in dag_source
    assert "finance_data_platform.analysis.run_analyze" in dag_source
    assert "finance_data_platform.reporting.run_report" in dag_source
