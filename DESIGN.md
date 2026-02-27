# DESIGN.md

> Architecture rationale and technical trade-offs for `finance-data-platform`.
> This document explains *what was chosen*, *what was rejected*, and *why* — so a reader can evaluate the engineering thinking without running the code.

---

## 1. Scope and Intent

This platform is a **data engineering** project, not a data science or trading project. It exists to prove one thing to a recruiter: the author designs and ships layered, orchestrated, tested data pipelines in the finance domain.

**What it does:**
Ingests financial market data (OHLCV, dividends, splits, metadata) from yfinance, validates it against Pydantic schemas, stores it in a three-zone Parquet structure (raw → staged → curated), computes technical indicators and portfolio analytics, and produces a self-contained HTML report. The entire flow is orchestrated by an Airflow DAG and containerized with Docker.

**What it deliberately does not do:**
Train ML models, serve interactive dashboards, execute trades, or deploy to cloud infrastructure. Those are either out of scope permanently (ML, dashboards) or deferred to future iterations (cloud deployment, additional data sources). The line is strict: any feature not in the MVP table gets a GitHub issue labeled "post-MVP" and is not built.

---

## 2. Architecture Rationale

### Why layered zones?

The raw/staged/curated pattern mirrors how production data platforms in finance operate. Each zone has a distinct contract:

- **Raw** (`data/raw/`): Exact API response persisted as Parquet with an ingestion timestamp. No transformation. This guarantees reproducibility — if a downstream bug is found, the original data is intact and reprocessable.
- **Staged** (`data/staged/`): Cleaned data enriched with technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, rolling volatility). Schema-validated. This is the layer where data quality is enforced.
- **Curated** (`data/curated/`): Analysis-ready datasets — returns, correlations, portfolio metrics. Consumed by the analysis and reporting layers. Queryable via DuckDB SQL.

Zone separation prevents the common anti-pattern of mutating source data in place, which makes debugging and reprocessing impossible.

### Why Parquet + DuckDB?

Parquet is columnar, compressed, schema-aware, and cloud-compatible. It is the standard format for analytical data in modern DE pipelines. The local file structure (`data/raw/`, `data/staged/`, `data/curated/`) mirrors how data would be organized in S3 or GCS, making a future cloud migration straightforward without changing the code's storage abstraction.

DuckDB provides embedded analytical SQL directly on Parquet files with no server process. It avoids the operational overhead of Postgres (which would need a running server, connection management, and migrations) while delivering strong analytical query performance that SQLite cannot match on columnar workloads.

### Why Airflow?

Airflow is the most widely recognized orchestration tool in finance and banking DE teams. It demonstrates familiarity with DAG-based scheduling, task dependencies, retries, and monitoring — all things interviewers in the target roles expect. The pipeline is designed to work without Airflow (`make pipeline` runs the full chain), so Airflow is the packaging and scheduling layer, not a hard dependency.

---

## 3. Tech Stack Decisions

Each choice below follows a consistent evaluation: what was chosen, what was considered, and why the alternative was rejected.

### Language: Python ≥ 3.11

Industry standard for data engineering and finance. No alternative was seriously considered — the entire ecosystem (yfinance, pandas, Airflow, pytest) is Python-native.

### Ingestion: yfinance

Free, reliable, and provides OHLCV, dividends, splits, and metadata in a single API. Alpha Vantage was considered but has a rate-limited free tier. Finnhub was considered but deferred — one connector is sufficient to prove the pattern; additional sources are a post-MVP extension.

### Validation: Pydantic v2

Schema validation at the ingestion boundary is the data contract. Pydantic v2 is the standard in modern Python for structured validation. Pandera was considered but has less mainstream adoption. Manual validation checks were rejected as fragile and untestable.

### Storage: Parquet via pyarrow

Columnar, compressed, and cloud-compatible. CSV was rejected for lacking compression, schema enforcement, and efficient columnar reads. Delta Lake was considered but adds transactional complexity without MVP benefit — the platform doesn't need ACID transactions or time travel at this scale.

### Query: DuckDB

Embedded analytical SQL on Parquet with zero infrastructure. SQLite was rejected for poor analytical performance on columnar data. Postgres was rejected because it requires a running server and adds operational overhead without changing the signal for a portfolio project.

### Transforms: pandas + numpy

Portable, testable, and universally understood. Polars was considered — it is faster and has a cleaner API — but has less recruiter recognition in finance/banking DE. PySpark was rejected as overkill for the data volumes in this project.

### Analysis: statsmodels + scipy

Purpose-built for financial statistics: OLS regression for CAPM, statistical tests for significance. scikit-learn was considered but is positioned more toward ML than finance-domain statistics.

### Reporting: Jinja2 + matplotlib

Produces a self-contained HTML report with embedded base64 charts — no server required. Streamlit was rejected because an interactive dashboard sends a data science signal, not a data engineering signal. Jupyter was rejected because notebook outputs are not reproducible artifacts.

### Orchestration: Apache Airflow 2.x

Most recognized DE orchestrator, especially in finance and banking. Prefect was considered — it has a cleaner developer experience — but has less recruiter recognition in the target market. Cron was rejected as too primitive (no dependency management, no retries, no monitoring UI).

### Container: Docker + docker-compose

Full reproducibility with one-command startup. `docker-compose up` brings up the app container plus Airflow services (webserver, scheduler, worker). No alternative was considered — Docker is the baseline expectation.

### Testing: pytest

Standard Python testing framework. unittest was rejected for its verbose syntax and smaller plugin ecosystem.

### Linting: ruff

Single tool replacing flake8, isort, and black. Faster and simpler to configure. No reason to use the three-tool chain it replaces.

### CI: GitHub Actions

Free for public repos, standard in the industry, provides a visible badge. Jenkins was rejected (self-hosted overhead). GitLab CI was rejected (platform lock-in).

---

## 4. Data Contract Design

Data quality is enforced at the ingestion boundary using Pydantic v2 models defined in `schemas.py`. Every record downloaded from yfinance is validated before it reaches the raw zone.

The schemas define the expected structure for four data types: OHLCV bars, dividends, splits, and ticker metadata. Validation failures raise immediately — bad data never reaches Parquet.

This is a deliberate design choice: validate once, at the boundary, rather than scattering defensive checks throughout the pipeline. Downstream layers (transforms, analysis, reporting) can trust that if data exists in the raw zone, it conforms to the contract.

The contract also serves as documentation. A new developer reading `schemas.py` understands exactly what shape data takes at ingestion without tracing through connector code.

---

## 5. Orchestration Philosophy

The Airflow DAG defines the pipeline as a linear chain of tasks: `ingest → store (raw) → transform (staged) → enrich (curated) → analyze → report`. Each task maps to one pipeline step and one Makefile target.

Key design decisions:

**Airflow is a scheduling layer, not a dependency.** The pipeline runs identically via `make pipeline` without Airflow. This means local development doesn't require Docker or Airflow, and the DAG can be tested by running each step independently.

**Tasks are idempotent.** The ingestion connector skips already-fetched dates. Transforms and analysis overwrite staged/curated zones from the current raw data. Reports overwrite the previous output. Running the DAG twice produces the same result.

**No XCom abuse.** Tasks communicate through the filesystem (Parquet zones), not through Airflow's XCom mechanism. This keeps tasks decoupled and testable outside Airflow.

---

## 6. Known Boundaries

The following are intentionally excluded from this project. Each has a rationale tied to the project's strategic purpose.

**ML models** — Hard boundary. This is an infrastructure project, not a prediction project. ML is reserved for a separate portfolio project (#4).

**Streamlit / interactive dashboards** — Wrong signal. A dashboard suggests data science or analytics engineering. This project generates reports as reproducible artifacts, which is the DE pattern.

**Spark / Kubernetes** — Overkill. The data volumes (6 tickers, ~5 years of daily bars) don't justify distributed compute. Mentioning Spark as a scaling path in this document is sufficient to show awareness.

**Cloud deployment (S3/GCS)** — Deferred. The local Parquet structure mirrors cloud storage conventions. Actual deployment adds infrastructure cost and ops complexity without changing the engineering signal.

**dbt** — Deferred to post-MVP. Airflow demonstrates orchestration competency. dbt can layer on top later to show SQL-based transformation patterns.

**Postgres** — Deferred. DuckDB on Parquet is sufficient for analytical queries. Postgres would add a running server, migrations, and operational overhead without strengthening the portfolio signal.

---

## 7. Scaling Path

The architecture is designed so that scaling does not require rewriting — it requires replacing components.

**Multi-source ingestion:** The connector pattern (download → validate → return typed models) is source-agnostic. Adding Alpha Vantage or Finnhub means writing a new connector module that conforms to the same interface. No changes to storage, transforms, or downstream layers.

**dbt for transforms:** The staged and curated zones map naturally to dbt models. The current pandas transforms could be replaced by or supplemented with dbt SQL models running against DuckDB, preserving the zone structure.

**Spark for volume:** If data volumes grew beyond what pandas handles comfortably (millions of rows, real-time streaming), the transform layer could be replaced with PySpark. The zone structure and Parquet format are already Spark-compatible.

**Cloud storage:** Replacing local `data/` paths with S3 or GCS URIs requires changes only in `parquet_store.py` and `config.yaml`. pyarrow and DuckDB both support remote Parquet natively.

**Delta Lake:** For use cases requiring ACID transactions, time travel, or schema evolution, the Parquet store could be upgraded to Delta Lake. The zone structure remains identical.

---

## 8. Future Considerations

These are concrete extensions identified during design, documented here so they can be picked up without re-discovering the context.

**Alpha Vantage connector** — Adds a second data source, proving the multi-source connector pattern. Rate-limited free tier requires careful throttling logic.

**Finnhub connector** — Commonly used in finance DE. Worth adding to demonstrate multi-source capability and real-time data handling.

**FRED macro data** — Enables cross-asset enrichment (interest rates, GDP, unemployment alongside equity data). Extension of the curated zone.

**Options pricing / Monte Carlo VaR** — DS-heavy features reserved for project #4. Not appropriate for this project's DE focus.

**Delta Lake migration** — Replaces raw Parquet with Delta tables for ACID semantics. Valuable if the platform evolves toward incremental processing or schema evolution.

**Project #4 integration** — This platform's curated zone is designed to serve as the data layer for a future trading strategy project. The interface is Parquet files and DuckDB queries — no coupling to this project's internals.

---

## 9. Dataclass Design Choice and OOP Position

### Why dataclasses are used in this project

For ingestion and storage orchestration, this project uses Python `dataclass` types for internal models such as runtime config and per-ticker ingestion batches. This is intentional:

- **Clear, typed domain objects:** Dataclasses give explicit fields and types for in-process objects (`IngestionConfig`, `TickerIngestionBatch`) without writing constructor/repr/equality boilerplate.
- **Immutability for safety:** Using frozen dataclasses for config objects prevents accidental mutation during pipeline execution.
- **Separation of concerns:** Pydantic models remain the external **data-contract boundary** (validation of market records), while dataclasses represent trusted internal state after validation/config load.
- **Low ceremony for MVP:** Dataclasses provide structure without introducing inheritance-heavy frameworks that do not add value at current scope.

### Can we claim to be object-oriented?

Yes, with accurate wording.

- The codebase uses **object-oriented modeling** through class-based domain models (Pydantic schemas and dataclass config/batch models).
- The codebase is also intentionally **functional in transform flow** (DataFrame in -> DataFrame out) for deterministic, testable processing.
- It does **not** depend on deep inheritance/polymorphic trees; this is a deliberate simplicity trade-off, not a gap.

Recommended wording:

> The platform uses object-oriented domain modeling for data contracts and typed runtime state, combined with functional transformation steps for deterministic pipeline behavior.

### References

- Python docs: `dataclasses` — https://docs.python.org/3/library/dataclasses.html
- PEP 557 (Data Classes) — https://peps.python.org/pep-0557/
- Pydantic docs — https://docs.pydantic.dev/latest/
