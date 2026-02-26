# Initial Packet Outline

## P-001 — Repo Skeleton + CI + Schemas

- **Objective:** Create the repo scaffold (pyproject.toml, Makefile, .gitignore, LICENSE, empty package structure, GitHub Actions CI) and implement Pydantic validation schemas for all data types.
- **Key deliverables:**
  - `pyproject.toml` with all MVP dependencies, ruff config
  - `Makefile` with all targets (initially stubs for unimplemented steps)
  - `.github/workflows/ci.yml` (ruff + pytest)
  - `src/finance_data_platform/` package structure with `__init__.py` files
  - `schemas.py` — Pydantic v2 models for OHLCV, dividends, splits, metadata
  - `tests/test_ingestion.py` — schema validation tests
  - `config.yaml` with default values
- **CLI thread:** `codex:repo-skeleton`
- **Dependencies:** None
- **Stop when:** `make lint` passes, `make test` passes (schema tests), CI workflow file exists, all directories from repo structure are present.

---

## P-002 — Ingestion + Storage (Raw Zone)

- **Objective:** Implement the yfinance connector (idempotent, retry-aware, returns validated Pydantic models) and the Parquet store (write to raw zone, read via DuckDB).
- **Key deliverables:**
  - `yfinance_connector.py` — download, validate, return typed data; config-driven universe
  - `parquet_store.py` — write validated data to `data/raw/` as Parquet; DuckDB read interface
  - `tests/test_ingestion.py` extended — connector behavior tests (using fixture data)
  - `conftest.py` — shared fixtures (sample DataFrames, temp dirs, saved Parquet snapshots)
  - `make ingest` target functional
- **CLI thread:** `codex:ingestion-storage`
- **Dependencies:** P-001
- **Stop when:** `make ingest` downloads data for configured universe and writes Parquet to `data/raw/`; `make test` passes all ingestion tests; DuckDB can query raw Parquet files.

---

## P-003 — Transforms + Analysis + Reporting

- **Objective:** Implement transform layer (indicators + enrichment), portfolio analysis, and HTML report generation. Wire the full `make pipeline` end-to-end.
- **Key deliverables:**
  - `indicators.py` — SMA, EMA, RSI, MACD, Bollinger Bands, rolling volatility (pure functions)
  - `enrichment.py` — daily/log returns, rolling correlations, cumulative returns
  - `portfolio.py` — CAPM regression, beta, alpha, Sharpe, Treynor, portfolio variance
  - `generator.py` + `report.html` template — Jinja2 HTML report with embedded matplotlib charts
  - `test_transforms.py`, `test_analysis.py` — unit tests for all calculations
  - `test_pipeline_integration.py` — end-to-end for 1–2 tickers
  - `make transform`, `make analyze`, `make report`, `make pipeline` all functional
- **CLI thread:** `codex:transforms-analysis-report`
- **Dependencies:** P-002
- **Stop when:** `make pipeline` runs end-to-end and produces a valid HTML report in `output/`; `make test` passes all unit + integration tests.

---

## P-004 — Docker + Airflow Orchestration

- **Objective:** Containerize the platform and implement the Airflow DAG so `docker-compose up` runs the full pipeline.
- **Key deliverables:**
  - `Dockerfile` — app container with all dependencies
  - `docker-compose.yml` — app + Airflow (webserver, scheduler, worker)
  - `orchestration/dags/finance_pipeline_dag.py` — Airflow DAG: ingest → raw → staged → curated → analyze → report
  - `make docker-up` / `make docker-down` functional
- **CLI thread:** `codex:docker-airflow`
- **Dependencies:** P-003
- **Stop when:** `docker-compose up` starts all services; Airflow DAG is visible in UI and triggers successfully; pipeline produces HTML report inside container.

---

## P-005 — Documentation + Polish + Ship

- **Objective:** Write recruiter-ready README, DESIGN.md, architecture.md; commit sample output; add CI badge; final CHANGELOG.
- **Key deliverables:**
  - `README.md` — architecture Mermaid diagram, quickstart (Docker + non-Docker), tech stack table with rationale, sample output screenshot, project structure, config reference, origin story
  - `docs/DESIGN.md` — scope, architecture rationale, tech decisions (what/why/why-not), data contracts, orchestration philosophy, known boundaries, scaling path
  - `docs/architecture.md` — Mermaid diagram + layer descriptions
  - `examples/sample_report.html` — pre-generated report committed
  - `CHANGELOG.md` — MVP release notes
  - CI badge in README
- **CLI thread:** `codex:docs-polish`
- **Dependencies:** P-004 (or P-003 minimum — docs can ship without Docker if needed)
- **Stop when:** README passes the "recruiter test" (understandable without running anything); DESIGN.md covers trade-offs for every major tech choice; `examples/sample_report.html` is committed and viewable; CI badge is green.
