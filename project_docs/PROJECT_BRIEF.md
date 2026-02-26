# PROJECT_BRIEF.md

## 1) Project Identity

- **Name:** `finance-data-platform`
- **One-line description:** A layered data platform for financial market data — from ingestion to automated reporting — built with modern Python DE practices.
- **Repo:** `https://github.com/shervin-taheripour/finance-data-platform` (to be created)
- **License:** MIT
- **Runtime:** Python ≥ 3.11
- **Owner:** Shervin Taheripour
- **Target completion:** ~3 weeks (mid-March 2026)

## 2) Strategic Context

- **Portfolio purpose:** DE flagship project — single strongest signal for finance/banking DE roles (UK & Switzerland).
- **Target roles:** Finance/banking data engineering.
- **What it must prove:**
  - Layered data architecture design (not just scripts)
  - Orchestrated, reproducible pipelines (not notebooks)
  - Finance domain fluency with real data and metrics
  - Data contracts, validation, zone separation
  - Ships: tests, CI, Docker, documentation
- **Hard non-goals / must NOT become:**
  - Data science showcase (no ML, no interactive dashboards)
  - Trading strategy platform (reserved for project #4)
  - Over-engineered (no Spark, no Kubernetes, no multi-cloud)

## 3) MVP Scope

### In-scope components

| Layer | Module(s) | Responsibility |
|---|---|---|
| Ingestion | `yfinance_connector.py`, `schemas.py` | Download OHLCV/dividends/splits/metadata; Pydantic validation at boundary; idempotent, retry-aware |
| Storage | `parquet_store.py` | Write to 3-zone Parquet structure (raw/staged/curated); DuckDB SQL read interface |
| Transforms | `indicators.py`, `enrichment.py` | Technical indicators (SMA, EMA, RSI, MACD, Bollinger, vol); returns, correlations, cumulative |
| Analysis | `portfolio.py` | CAPM regression (beta, alpha), Sharpe, Treynor, portfolio variance |
| Reporting | `generator.py` + Jinja2 template | Self-contained HTML report with metrics, tables, embedded matplotlib charts |
| Orchestration | `finance_pipeline_dag.py` | Airflow DAG: ingest → raw → staged → curated → analyze → report |
| Docker | `Dockerfile`, `docker-compose.yml` | Full stack: app + Airflow (webserver, scheduler, worker); one-command startup |
| Tests | `test_ingestion.py`, `test_transforms.py`, `test_analysis.py`, `test_pipeline_integration.py` | Unit + integration; fixture data (no live API in tests) |
| CI | `.github/workflows/ci.yml` | GitHub Actions: ruff lint + pytest on push/PR |
| Docs | README.md, DESIGN.md, architecture.md, CHANGELOG.md | Mermaid diagrams, quickstart, tech rationale, sample output |

### Out-of-scope / deferred

- Additional connectors (Alpha Vantage, Finnhub, FRED) → post-MVP / project #4
- Options pricing, Monte Carlo VaR, ML → project #4
- Streamlit dashboard → never for this project
- dbt → post-MVP iteration
- Spark, Kubernetes → never for this project
- Cloud deployment (real S3/GCS) → post-MVP stretch
- Postgres → post-MVP if needed

## 4) Architecture & Data Flow

### Zones

| Zone | Path | Contents |
|---|---|---|
| Raw | `data/raw/` | Exact API response, no transformation; Parquet with ingestion timestamp |
| Staged | `data/staged/` | Cleaned + indicator-enriched; validated schema |
| Curated | `data/curated/` | Analysis-ready datasets (returns, correlations, portfolio metrics) |

### Data flow

`yfinance API` → `Ingestion + Pydantic validation` → `Raw Zone (Parquet)` → `Transforms (indicators + enrichment)` → `Staged/Curated Zones` → `Analysis (CAPM, Sharpe)` → `Reporting (Jinja2 → HTML)`. DuckDB provides SQL query layer on curated Parquet. Entire flow orchestrated by Airflow DAG.

## 5) Tech Stack (MVP)

| Layer | Tool | Purpose |
|---|---|---|
| Language | Python ≥ 3.11 | Industry standard for DE + finance |
| Ingestion | yfinance | Free, reliable OHLCV source |
| Validation | Pydantic v2 | Schema enforcement at ingestion boundary |
| Storage | Parquet (pyarrow) | Columnar, compressed, cloud-compatible |
| Query | DuckDB | Embedded analytical SQL on Parquet, no server |
| Transforms | pandas + numpy | Portable, testable, no framework lock-in |
| Analysis | statsmodels + scipy | CAPM regression, statistical tests |
| Reporting | Jinja2 + matplotlib | Templated HTML with embedded base64 charts |
| Orchestration | Apache Airflow 2.x (Docker) | Most recognized DE orchestration, especially finance/banking |
| Container | Docker + docker-compose | Full reproducibility, one-command setup |
| Testing | pytest | Standard Python testing |
| Linting | ruff | Replaces flake8+isort+black |
| CI | GitHub Actions | Free, standard, visible badge |
| Diagrams | Mermaid | Version-controlled, renders on GitHub |

## 6) Configuration & Interfaces

- **Single config file:** `config.yaml` — controls universe (tickers, benchmark, dates), ingestion (retry), storage (base path, format), transform params (SMA/EMA/RSI/MACD/Bollinger windows), analysis (risk-free rate), reporting (output path, template path).
- **Makefile targets:** `ingest`, `transform`, `analyze`, `report`, `pipeline`, `test`, `lint`, `clean`, `docker-up`, `docker-down`.
- **Data contracts:** Pydantic models in `schemas.py` define OHLCV, dividends, splits, metadata schemas; enforced at ingestion boundary.
- **Transform interface:** Pure functions — DataFrame in → DataFrame out.

## 7) Delivery Plan (MVP)

### Build sequence

| Phase | Focus | Key deliverables |
|---|---|---|
| Week 1 | Foundation | Repo skeleton + CI, Pydantic schemas, yfinance connector, parquet store, transforms (indicators + enrichment) |
| Week 2 | Analytics + Reporting | Portfolio analysis, HTML report generator, end-to-end pipeline (`make pipeline`), integration test |
| Week 3 | Orchestration + Polish | Docker + Airflow DAG, README (recruiter-ready), DESIGN.md, sample report, CHANGELOG, badges |

### Success criteria (Definition of Done)

- `make pipeline` runs end-to-end and produces an HTML report
- `docker-compose up` starts full stack and Airflow triggers the DAG
- `make test` passes with unit + integration tests
- CI badge is green on GitHub
- README has architecture diagram, quickstart, tech stack table, sample output
- DESIGN.md documents trade-offs for every major technical choice
- `examples/sample_report.html` committed and viewable
- A finance DE recruiter can understand the project from README alone

## 8) Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Airflow Docker setup takes too long | Start with `make pipeline` (no orchestration). Add Airflow in week 3. Pipeline works without it. |
| yfinance API changes or rate-limits | Retry logic in connector. Tests use fixture data (saved Parquet snapshots), no live API. |
| Scope creep toward ML/dashboard | Hard rule: non-MVP features get GitHub issue labeled "post-MVP", not worked on. |
| 3 weeks insufficient | Build sequence ordered so partial completion is still credible. After week 2: working pipeline sans orchestration. |
| Energy drops mid-project | Freeze at last stable commit. Clean repo with ingestion + transforms + tests > rushed full build. |

## 9) Open Questions

None — the init file is comprehensive. All ambiguity is resolved within the document.
