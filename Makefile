.RECIPEPREFIX := >

PYTHON ?= python3

.PHONY: ingest transform analyze report pipeline test lint clean docker-up docker-down

ingest:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.ingestion.run_ingest

transform:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.transforms.run_transform

analyze:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.analysis.run_analyze

report:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.reporting.run_report

pipeline:
>$(MAKE) transform
>$(MAKE) analyze
>$(MAKE) report

test:
>PYTHONPATH=src $(PYTHON) -m pytest -q

lint:
>PYTHONPATH=src $(PYTHON) -m ruff check .

clean:
>find data -mindepth 1 ! -name ".gitkeep" -delete 2>/dev/null || true
>find output -mindepth 1 ! -name ".gitkeep" -delete 2>/dev/null || true
>rm -rf .pytest_cache .ruff_cache

docker-up:
>docker compose up airflow-init
>docker compose up -d postgres airflow-scheduler airflow-webserver

docker-down:
>docker compose down --volumes --remove-orphans
