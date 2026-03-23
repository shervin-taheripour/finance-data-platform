# finance-data-platform

[![CI](https://github.com/shervin-taheripour/finance-data-platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/shervin-taheripour/finance-data-platform/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A layered finance data platform that ingests market data, validates it, stores it across raw/staged/curated zones, computes portfolio analytics, and produces recruiter-friendly HTML reports.

This project is deliberately built to show data engineering judgment rather than notebook experimentation: explicit data contracts, partitioned Parquet storage, DuckDB analytical reads, Airflow orchestration, Docker reproducibility, and a final artifact that can be reviewed without running a web app.

## Why This Project Exists

This repo is the “production-minded rebuild” of an earlier finance analytics project. The goal was not to make the flashiest finance app; it was to prove that the same domain can be re-implemented as a disciplined data platform with clearer boundaries, stronger testing, and better operational packaging.

If a recruiter opens this repo without running anything, they should be able to understand:
- what the pipeline does
- why the architecture was chosen
- where data lives at each stage
- how to run it locally or with Airflow
- what engineering trade-offs were made

## What The Pipeline Does

1. Downloads OHLCV, dividends, splits, and metadata from yfinance
2. Validates records with Pydantic at the ingestion boundary
3. Writes ticker-partitioned Parquet files into the raw zone
4. Builds technical indicators and enriched return series
5. Computes CAPM and portfolio risk metrics
6. Renders self-contained HTML reports with embedded charts
7. Runs either locally through `make` targets or under Airflow via Docker Compose

## Architecture At A Glance

Text blueprint for the current architecture:

```text
yfinance
  -> ingestion + schema validation
  -> data/raw/*.parquet
  -> transforms (indicators + enrichment)
  -> data/staged/*.parquet
  -> analysis (CAPM, Sharpe, Treynor, variance)
  -> data/curated/*.parquet
  -> Jinja2 + matplotlib reporting
  -> output/*.html
```

Control plane:

```text
Local path:   make ingest -> make transform -> make analyze -> make report
Docker path:  Docker Compose -> Airflow DAG -> same Python entrypoints
```

Full architecture blueprint:
- [docs/architecture.md](docs/architecture.md)

Deep design rationale:
- [docs/DESIGN.md](docs/DESIGN.md)

## Tech Stack

| Area | Choice | Why this was chosen |
|---|---|---|
| Language | Python 3.11+ | Best fit for Airflow, analytics, validation, and recruiter expectations |
| Source data | yfinance | Fastest single-source path to OHLCV, dividends, splits, and metadata |
| Validation | Pydantic v2 | Explicit ingestion boundary and strong schema contracts |
| File format | Parquet / pyarrow | Columnar, compressed, analytics-friendly, cloud-ready |
| Query layer | DuckDB | SQL directly on Parquet without standing up a project database |
| Transforms | pandas + numpy | Readable and portable for MVP-scale analytical data |
| Analysis | pandas-based finance math | Sufficient for CAPM and portfolio metrics without overcomplicating the stack |
| Reporting | Jinja2 + matplotlib | Self-contained HTML artifact instead of a running dashboard |
| Orchestration | Apache Airflow | Strongest recruiter-recognized orchestration signal in finance DE |
| Containerization | Docker Compose | Reproducible local orchestration stack |
| Testing | pytest | Standard Python testing workflow |
| Linting | Ruff | Fast, simple, modern linting |
| CI | GitHub Actions | Visible and lightweight automation on every push |

## Storage Model

| Zone | Path | Purpose |
|---|---|---|
| Raw | `data/raw/` | Validated source records, preserved close to ingestion output |
| Staged | `data/staged/` | Indicator-enriched price series |
| Curated | `data/curated/` | Analysis-ready returns, correlations, and summary metrics |
| Output | `output/` | Generated HTML reports |
| Examples | `examples/` | Committed sample artifact for repo review |

Ticker-level partitioning is used intentionally. Re-running `AAPL` should not mutate `MSFT`, and debugging should be as simple as opening one parquet file for one ticker.

## Sample Output

Pre-generated sample report:
- [examples/sample_report.html](examples/sample_report.html)

Current report artifacts are also generated into `output/` when the pipeline runs.

## Quickstart

### Docker + Airflow

Prerequisites:
- Docker
- Docker Compose v2

Run the orchestration stack:

```bash
make docker-up
```

Then open:
- `http://localhost:8080`
- username: `admin`
- password: `admin`

Inside Airflow, trigger the DAG:
- `finance_data_platform_pipeline`

Stop the stack:

```bash
make docker-down
```

### Non-Docker Local Path

```bash
git clone git@github.com:shervin-taheripour/finance-data-platform.git
cd finance-data-platform
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run steps individually:

```bash
make ingest
make transform
make analyze
make report
```

Or run the raw-to-report flow after ingestion:

```bash
make pipeline
```

## Configuration Reference

All runtime configuration lives in [config.yaml](config.yaml).

Key sections:
- `universe`: tickers, benchmark, date window
- `ingestion`: retry attempts and delay
- `storage`: base path and file format
- `transforms.indicators`: SMA, EMA, RSI, MACD, Bollinger, volatility windows
- `transforms.enrichment`: rolling correlation window
- `analysis`: risk-free rate
- `reporting`: output path and template path

Example:

```yaml
universe:
  tickers: ["AAPL", "MSFT", "GOOGL", "JPM", "GS", "BAC"]
  benchmark: "SPY"
  start_date: "2020-01-01"
  end_date: null
```

## Project Structure

```text
finance-data-platform/
├── src/finance_data_platform/
│   ├── ingestion/
│   ├── storage/
│   ├── transforms/
│   ├── analysis/
│   └── reporting/
├── orchestration/dags/
├── tests/
├── data/
│   ├── raw/
│   ├── staged/
│   └── curated/
├── output/
├── examples/
├── docs/
├── config.yaml
├── Makefile
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Make Targets

```bash
make ingest       # Download and persist raw market data
make transform    # Build staged indicator datasets
make analyze      # Build curated analytical outputs
make report       # Render HTML reports
make pipeline     # Run transform -> analyze -> report
make test         # Run pytest
make lint         # Run Ruff
make docker-up    # Start PostgreSQL + Airflow stack
make docker-down  # Stop orchestration stack
```

## Testing And CI

The test suite is fully offline. It uses fixture data and integration checks rather than live API calls.

Coverage includes:
- schema validation
- ingestion/storage behavior
- technical indicators and enrichment
- portfolio analysis
- report generation
- orchestration asset smoke checks

CI runs lint + test on every push via GitHub Actions.

## Design Highlights

A few choices worth calling out directly:
- DuckDB is the project data query layer
- PostgreSQL is used only for Airflow metadata
- Airflow orchestrates existing Python entrypoints instead of owning business logic
- reports are generated as static artifacts, not dashboards
- the storage layout is cloud-friendly without pretending cloud deployment is part of the MVP

## Origin Story

This project grew out of an earlier stock analysis project and intentionally re-scoped the domain into a stronger engineering artifact. The result is less flashy, but much more representative of real data platform work: contracts, storage design, orchestration, testing, and shipping discipline.

## Release Notes

MVP release notes:
- [CHANGELOG.md](CHANGELOG.md)

## License

[MIT](LICENSE)
