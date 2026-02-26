# finance-data-platform — Project Initialization Brief

**Created:** 2026-02-24  
**Status:** Starting MVP build  
**Target completion:** ~3 weeks (mid-March 2026)  
**Author:** Shervin Taheripour

---

## 1. Project Identity

**Name:** `finance-data-platform`  
**Repo:** `https://github.com/shervin-taheripour/finance-data-platform` (to be created)  
**License:** MIT  
**Python:** ≥ 3.11

**One-line description:**  
A layered data platform for financial market data — from ingestion to automated reporting — built with modern Python DE practices.

**Origin story (for README and interviews):**  
Evolved from a certification capstone project (stock-analysis-tool, built with Dariya Sharonova). The original was notebook-heavy and exploratory. This repo re-engineers the valuable domain logic into a production-grade, modular platform with orchestration, testing, and reproducibility.

---

## 2. Strategic Context

**Role in portfolio:** This is the DE flagship project — the single strongest signal for finance/banking data engineering roles in the UK and Switzerland.

**What it must prove to a recruiter:**
1. You design layered data architectures (not just write scripts)
2. You build orchestrated, reproducible pipelines (not just notebooks)
3. You work in the finance domain with real financial data and metrics
4. You think about data contracts, validation, and zone separation
5. You ship: tests, CI, Docker, documentation

**What it must NOT become:**
- A data science showcase (no ML, no interactive dashboards)
- A trading strategy platform (that's project #4)
- Over-engineered (no Spark, no Kubernetes, no multi-cloud)

---

## 3. MVP Scope

### In scope

| Layer | Module | What it does | Key signal |
|---|---|---|---|
| **Ingestion** | `yfinance_connector.py` | Downloads OHLCV, dividends, splits, metadata for a configurable stock universe. Idempotent (skips already-fetched dates). Retry-aware. Returns validated Pydantic models. | Connector design, data contracts |
| **Validation** | `schemas.py` | Pydantic models defining the schema for each data type (OHLCV, dividends, splits, metadata). Used at ingestion boundary. | Data contract thinking |
| **Storage** | `parquet_store.py` | Writes validated data to Parquet files in a 3-zone structure (raw/staged/curated). Provides read interface via DuckDB SQL on top of Parquet. | Data lake pattern, zone separation |
| **Transforms** | `indicators.py` | SMA, EMA, RSI, MACD, Bollinger Bands, rolling volatility. Pure functions: DataFrame in → DataFrame out. | Modular, testable transforms |
| **Transforms** | `enrichment.py` | Daily returns, log returns, rolling correlations, cumulative returns. | Financial domain knowledge |
| **Analysis** | `portfolio.py` | CAPM regression (beta, alpha), Sharpe ratio, Treynor ratio, portfolio variance. Takes curated data as input. | Finance-specific analytics |
| **Reporting** | `generator.py` | Renders a Jinja2 HTML template with metrics, tables, and embedded charts (matplotlib → base64). Produces a self-contained HTML report file. | Artifact generation |
| **Orchestration** | `finance_pipeline_dag.py` | Airflow DAG: ingest → store (raw) → transform (staged) → enrich (curated) → analyze → report. Scheduled or trigger-based. | The crown jewel for DE signal |
| **Docker** | `docker-compose.yml` | Brings up full environment: app container + Airflow (webserver, scheduler, worker). One `docker-compose up` to run everything. | Reproducibility |
| **Tests** | `test_*.py` | Unit tests for ingestion schemas, transforms, and analysis. Integration test that runs the full pipeline on a small ticker universe. | Engineering discipline |
| **CI** | `ci.yml` | GitHub Actions: lint (ruff), test (pytest), on push/PR. | Visible quality signal |
| **Docs** | README, DESIGN.md, architecture.md | Architecture diagram (Mermaid), quickstart, tech stack rationale with "why X over Y" for each choice, sample output. | Senior-level communication |

### Out of scope (deferred)

| Feature | Deferred to | Rationale |
|---|---|---|
| Alpha Vantage connector | Project #4 or post-MVP iteration | One source proves the connector pattern |
| Finnhub connector | Project #4 or post-MVP iteration | Commonly used — worth adding to show multi-source capability, but not MVP |
| FRED macro data | Project #4 | Cross-asset enrichment is an extension |
| Options pricing / Monte Carlo VaR | Project #4 | DS-heavy, not DE MVP |
| ML models | Project #4 (hard boundary) | This project is infrastructure, not prediction |
| Streamlit dashboard | Never (for this project) | Wrong signal — report generation replaces it |
| dbt | Post-MVP iteration | Airflow first; dbt can layer on later |
| Spark | Never (for this project) | Overkill; mention in DESIGN.md as scaling path |
| Cloud deployment (real S3/GCS) | Post-MVP | Local structure mirrors cloud; actual deployment is stretch |
| Postgres | Post-MVP if needed | DuckDB on Parquet is sufficient; Postgres adds ops overhead without changing signal |

---

## 4. Tech Stack

| Layer | Tool | Version | Why this | Why not alternatives |
|---|---|---|---|---|
| **Language** | Python | ≥ 3.11 | Industry standard for DE and finance | — |
| **Ingestion** | yfinance | latest | Free, reliable OHLCV source | Alpha Vantage (rate-limited free tier), Finnhub (deferred) |
| **Validation** | Pydantic | v2 | Schema validation at ingestion boundary. Standard in modern Python DE | pandera (less mainstream), manual checks (fragile) |
| **Storage** | Parquet (via pyarrow) | latest | Columnar, compressed, cloud-compatible | CSV (no compression, no schema), Delta Lake (adds complexity without MVP benefit) |
| **Query** | DuckDB | latest | Embedded analytical SQL on Parquet. No server. Increasingly adopted in finance | SQLite (poor analytical performance), Postgres (needs server, ops overhead) |
| **Transforms** | pandas + numpy | latest | Portable, testable, no framework lock-in | Polars (strong but less recruiter recognition), PySpark (overkill) |
| **Analysis** | statsmodels + scipy | latest | CAPM regression, statistical tests | scikit-learn (more ML than finance stats) |
| **Reporting** | Jinja2 + matplotlib | latest | Templated HTML with embedded charts | Streamlit (wrong DE signal), Jupyter (not reproducible artifact) |
| **Orchestration** | Apache Airflow | 2.x (via Docker) | Most recognized DE orchestration tool, especially in finance/banking | Prefect (cleaner but less recruiter recognition), cron (too primitive) |
| **Container** | Docker + docker-compose | latest | Full reproducibility, one-command setup | — |
| **Testing** | pytest | latest | Standard | unittest (verbose, less ecosystem) |
| **Linting** | ruff | latest | Fast, replaces flake8+isort+black in one tool | flake8 (slower, multiple tools) |
| **CI** | GitHub Actions | — | Free, standard, visible badge | Jenkins (self-hosted), GitLab CI (platform lock-in) |
| **Diagrams** | Mermaid (in markdown) | — | Version-controlled, renders on GitHub natively | Lucidchart (upgrade option later for polished visuals) |

---

## 5. Architecture

### Data flow

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐     ┌────────────┐
│  yfinance    │────▶│  Ingestion   │────▶│  Raw Zone     │────▶│  Transforms  │────▶│  Analysis   │────▶│  Reporting  │
│  (API)       │     │  + Pydantic  │     │  (Parquet)    │     │  → Staged     │     │  (CAPM,     │     │  (Jinja2    │
│              │     │  validation  │     │               │     │  → Curated    │     │   Sharpe)   │     │   → HTML)   │
└─────────────┘     └─────────────┘     └──────────────┘     └──────────────┘     └────────────┘     └────────────┘
                                                                                                            │
                                         ┌──────────────┐                                                   │
                                         │   DuckDB      │◀── SQL queries on curated Parquet ───────────────┘
                                         └──────────────┘

                    └──────────────────── Orchestrated by Airflow DAG ──────────────────────────────────────┘
```

### Zone definitions

| Zone | Path | Contents | Write frequency |
|---|---|---|---|
| **Raw** | `data/raw/` | Exact API response, no transformation. Parquet with ingestion timestamp. | On each ingest run |
| **Staged** | `data/staged/` | Cleaned + indicator-enriched data. Validated schema. | After transform step |
| **Curated** | `data/curated/` | Analysis-ready datasets (returns, correlations, portfolio metrics). | After enrichment step |

### Repo structure

```
finance-data-platform/
├── src/
│   └── finance_data_platform/
│       ├── __init__.py
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── yfinance_connector.py    # Idempotent download, retry, logging
│       │   └── schemas.py               # Pydantic models for OHLCV, dividends, splits, meta
│       ├── storage/
│       │   ├── __init__.py
│       │   └── parquet_store.py         # Write to zones, read via DuckDB
│       ├── transforms/
│       │   ├── __init__.py
│       │   ├── indicators.py            # SMA, EMA, RSI, MACD, Bollinger, rolling vol
│       │   └── enrichment.py            # Returns, log returns, rolling corr, cumulative
│       ├── analysis/
│       │   ├── __init__.py
│       │   └── portfolio.py             # CAPM, beta, alpha, Sharpe, Treynor
│       └── reporting/
│           ├── __init__.py
│           ├── generator.py             # Jinja2 render → HTML report
│           └── templates/
│               └── report.html          # HTML template with placeholders
├── orchestration/
│   ├── dags/
│   │   └── finance_pipeline_dag.py      # Airflow DAG: full pipeline
│   └── docker-compose.airflow.yml       # Airflow services (webserver, scheduler, worker)
├── tests/
│   ├── conftest.py                      # Shared fixtures (sample dataframes, temp dirs)
│   ├── test_ingestion.py                # Schema validation, connector behavior
│   ├── test_transforms.py               # Indicator calculations, enrichment
│   ├── test_analysis.py                 # CAPM, ratio calculations
│   └── test_pipeline_integration.py     # End-to-end: ingest → report for 1–2 tickers
├── data/                                # .gitignored; created by pipeline runs
│   ├── raw/
│   ├── staged/
│   └── curated/
├── output/                              # .gitignored; generated reports
├── examples/
│   └── sample_report.html               # Pre-generated example output (committed)
├── docs/
│   ├── architecture.md                  # Mermaid diagram + layer descriptions
│   └── DESIGN.md                        # Trade-offs, rationale, known boundaries
├── .github/
│   └── workflows/
│       └── ci.yml                       # lint + test on push/PR
├── docker-compose.yml                   # Full stack: app + Airflow
├── Dockerfile                           # App container
├── pyproject.toml                       # Package metadata, dependencies, ruff config
├── Makefile                             # CLI shortcuts (see below)
├── README.md
├── CHANGELOG.md
└── LICENSE                              # MIT
```

### Makefile targets

```makefile
.PHONY: ingest transform analyze report pipeline test lint clean

ingest:          ## Run ingestion for configured universe
transform:       ## Run indicator + enrichment transforms
analyze:         ## Run CAPM and portfolio analysis
report:          ## Generate HTML report from curated data
pipeline:        ## Run full pipeline: ingest → transform → analyze → report
test:            ## Run pytest
lint:            ## Run ruff linter
clean:           ## Remove data/ and output/ contents
docker-up:       ## Start full stack (app + Airflow) via docker-compose
docker-down:     ## Stop all containers
```

---

## 6. Configuration

The pipeline uses a single config file for runtime parameters:

```yaml
# config.yaml
universe:
  tickers: ["AAPL", "MSFT", "GOOGL", "JPM", "GS", "BAC"]
  benchmark: "SPY"
  start_date: "2020-01-01"
  end_date: null  # null = today

ingestion:
  retry_attempts: 3
  retry_delay_seconds: 5

storage:
  base_path: "data"
  format: "parquet"

transforms:
  indicators:
    sma_windows: [20, 50, 200]
    ema_windows: [12, 26]
    rsi_window: 14
    macd_fast: 12
    macd_slow: 26
    macd_signal: 9
    bollinger_window: 20
    volatility_window: 30

analysis:
  risk_free_rate: 0.04  # annualized

reporting:
  output_path: "output"
  template: "src/finance_data_platform/reporting/templates/report.html"
```

---

## 7. Build Sequence

Recommended implementation order within the 3-week window. Each step produces testable, committable output.

### Week 1 — Foundation

| Day | Task | Deliverable |
|---|---|---|
| 1 | Create repo, pyproject.toml, Makefile, .gitignore, LICENSE, empty package structure, CI workflow | Skeleton repo that passes `make lint` and `make test` (with zero tests) |
| 1–2 | `schemas.py` — Pydantic models for OHLCV, dividends, splits, metadata | Validated data contracts |
| 2–3 | `yfinance_connector.py` — download, validate, return typed data | `make ingest` works, `test_ingestion.py` passes |
| 3–4 | `parquet_store.py` — write to raw zone, read via DuckDB | Data persists in `data/raw/`, queryable via SQL |
| 5 | `indicators.py` + `enrichment.py` — transform raw → staged → curated | `make transform` works, `test_transforms.py` passes |

### Week 2 — Analytics + Reporting

| Day | Task | Deliverable |
|---|---|---|
| 1–2 | `portfolio.py` — CAPM, beta, alpha, Sharpe, Treynor | `make analyze` works, `test_analysis.py` passes |
| 3–4 | `generator.py` + `report.html` template — Jinja2 report with metrics + charts | `make report` produces self-contained HTML |
| 5 | `make pipeline` end-to-end — chain all steps, integration test | `test_pipeline_integration.py` passes |

### Week 3 — Orchestration + Polish

| Day | Task | Deliverable |
|---|---|---|
| 1–2 | Dockerfile + docker-compose.yml + Airflow DAG | `docker-compose up` runs full pipeline |
| 3 | README.md — architecture diagram, quickstart, tech stack rationale, sample output screenshot | README is recruiter-ready |
| 4 | DESIGN.md — trade-offs, deferred features, scaling notes | Engineering narrative documented |
| 5 | Final pass: examples/sample_report.html committed, CHANGELOG, badges, edge case fixes | Ship-ready |

---

## 8. README Skeleton

```markdown
![CI](badge-url)
[![Python](badge-url)](pyproject-url)
[![License](badge-url)](LICENSE)

# finance-data-platform

A layered data platform for financial market data — from ingestion to automated 
reporting — built with modern Python data engineering practices.

## Architecture

[Mermaid diagram here]

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| ... | ... | ... |

## Quickstart

### With Docker (recommended)
docker-compose up

### Without Docker
make pipeline

## Data Zones

| Zone | Contents |
|---|---|
| raw/ | Unmodified API responses |
| staged/ | Cleaned + indicator-enriched |
| curated/ | Analysis-ready datasets |

## Sample Output

[Screenshot of generated report]

## Project Structure

[Tree view]

## Configuration

[config.yaml reference]

## Testing

pytest

## Design Decisions

See [DESIGN.md](docs/DESIGN.md) for architecture rationale and trade-offs.

## Origin

Evolved from a certification capstone project 
([stock-analysis-tool](https://github.com/shervin-taheripour/stock-analysis-tool), 
built with Dariya Sharonova, 2025). This repo re-engineers the domain logic into 
a production-grade platform with orchestration, testing, and reproducibility.

## License

MIT
```

---

## 9. DESIGN.md Skeleton

Key sections to include:

1. **Scope and Intent** — What this platform does and doesn't do
2. **Architecture Rationale** — Why layered zones, why Parquet + DuckDB, why Airflow
3. **Tech Stack Decisions** — For each tool: what was chosen, what was rejected, why
4. **Data Contract Design** — How Pydantic schemas enforce data quality at boundaries
5. **Orchestration Philosophy** — Why Airflow over cron/Prefect, DAG design choices
6. **Known Boundaries** — What's intentionally out of scope (ML, dashboards, cloud deploy)
7. **Scaling Path** — How this architecture extends: multi-source, dbt, Spark, cloud (shows you think beyond the MVP without building it)
8. **Future Considerations** — Alpha Vantage, Finnhub, Delta Lake, project #4 extension

---

## 10. Success Criteria

The MVP is done when:

- [ ] `make pipeline` runs end-to-end and produces an HTML report
- [ ] `docker-compose up` starts the full stack and Airflow triggers the DAG
- [ ] `make test` passes with unit + integration tests
- [ ] CI badge is green on GitHub
- [ ] README has architecture diagram, quickstart, tech stack table, and sample output
- [ ] DESIGN.md documents trade-offs for every major technical choice
- [ ] `examples/sample_report.html` is committed and viewable
- [ ] A finance DE recruiter can understand the project from the README alone without running anything

---

## 11. Risk Mitigation

| Risk | Mitigation |
|---|---|
| Airflow Docker setup takes too long | Start with `make pipeline` (no orchestration). Add Airflow in week 3. The pipeline works without it; Airflow is the packaging layer. |
| yfinance API changes or rate-limits | Retry logic in connector. For tests, use fixture data (saved Parquet snapshots) so tests don't hit the API. |
| Scope creep toward ML/dashboard | Hard rule: any feature not in the MVP table above gets a GitHub issue labeled "post-MVP" and is not worked on. |
| 3 weeks isn't enough | The build sequence is ordered so that partial completion still produces a credible project. After week 2 you have a working pipeline without orchestration — still impressive. Airflow + Docker + polish in week 3 are the upgrade, not the foundation. |
| Energy drops mid-project | Per LifeSystem_Master: freeze at last stable commit. A clean repo with ingestion + transforms + tests is better than a rushed full build. |

---

This document is the single briefing file for the finance-data-platform build.  
Use it to initialize the repo and guide daily implementation decisions.  
Review against the PortfolioProjectPlan at project completion.
