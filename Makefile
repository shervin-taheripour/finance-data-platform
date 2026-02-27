.RECIPEPREFIX := >

PYTHON ?= .venv/bin/python3

.PHONY: ingest transform analyze report pipeline test lint clean docker-up docker-down

ingest:
>PYTHONPATH=src $(PYTHON) -m finance_data_platform.ingestion.run_ingest

transform:
>echo "Stub target: transform step will be implemented in a later packet."

analyze:
>echo "Stub target: analysis step will be implemented in a later packet."

report:
>echo "Stub target: reporting step will be implemented in a later packet."

pipeline:
>$(MAKE) ingest
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
>echo "Stub target: docker orchestration will be implemented in a later packet."

docker-down:
>echo "Stub target: docker orchestration will be implemented in a later packet."
