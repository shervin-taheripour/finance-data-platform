.RECIPEPREFIX := >

PYTHON ?= python3

.PHONY: ingest transform analyze report report-strategy strategy-semiconductor strategy-semiconductor-publish strategy-semiconductor-url publish publish-dry-run pipeline test lint clean docker-up docker-down

ingest:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.ingestion.run_ingest

transform:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.transforms.run_transform

analyze:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.analysis.run_analyze

report:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.reporting.run_report

report-strategy:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.reporting.run_strategy_report

strategy-semiconductor:
>UNIVERSE_PRESET=semiconductor_supply_chain $(MAKE) PYTHON=$(PYTHON) ingest
>UNIVERSE_PRESET=semiconductor_supply_chain $(MAKE) PYTHON=$(PYTHON) transform
>UNIVERSE_PRESET=semiconductor_supply_chain $(MAKE) PYTHON=$(PYTHON) analyze
>UNIVERSE_PRESET=semiconductor_supply_chain $(MAKE) PYTHON=$(PYTHON) report-strategy

strategy-semiconductor-publish:
>UNIVERSE_PRESET=semiconductor_supply_chain $(MAKE) PYTHON=$(PYTHON) strategy-semiconductor
>$(MAKE) PYTHON=$(PYTHON) publish

strategy-semiconductor-url:
>$(PYTHON) -c "import yaml; c=yaml.safe_load(open('config.yaml', encoding='utf-8')); base=c.get('publishing', {}).get('cloudfront', {}).get('distribution_url'); print('Local report: output/strategy_semiconductor_supply_chain.html'); print(f'Published report (after make strategy-semiconductor-publish): {base}/reports/strategy_semiconductor_supply_chain.html' if base else 'Published report: configure publishing.cloudfront.distribution_url in config.yaml')"

publish:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.publishing.run_publish $(PUBLISH_ARGS)

publish-dry-run:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.publishing.run_publish --dry-run

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
