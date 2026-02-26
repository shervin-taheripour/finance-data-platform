.RECIPEPREFIX := >

.PHONY: ingest transform analyze report pipeline test lint clean docker-up docker-down

ingest:
>echo "Stub target: ingestion step will be implemented in a later packet."

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
>PYTHONPATH=src python -m pytest -q

lint:
>PYTHONPATH=src python -m ruff check .

clean:
>find data -mindepth 1 ! -name ".gitkeep" -delete 2>/dev/null || true
>find output -mindepth 1 ! -name ".gitkeep" -delete 2>/dev/null || true
>rm -rf .pytest_cache .ruff_cache

docker-up:
>echo "Stub target: docker orchestration will be implemented in a later packet."

docker-down:
>echo "Stub target: docker orchestration will be implemented in a later packet."
