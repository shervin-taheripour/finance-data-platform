# Design

This document explains the engineering decisions behind `finance-data-platform`.
It is written to explain what the system does, why the architecture was chosen, and where its boundaries are.

## 1. Scope

This is a finance-domain data engineering project.
Its purpose is to provide a layered, tested, orchestrated pipeline for finance-domain data rather than a trading strategy or machine learning product.

The platform:
- ingests market data from yfinance
- validates records at the ingestion boundary
- stores data across raw, staged, and curated zones
- computes technical indicators and portfolio analytics
- renders self-contained HTML reports
- runs locally or under Airflow with Docker

The platform does not:
- train ML models
- run interactive dashboards
- execute trades
- depend on cloud infrastructure
- optimize for large-scale distributed workloads

Those omissions are intentional. The goal is a focused MVP with clear boundaries and maintainable scope.

## 2. Architecture Rationale

### Why a layered zone model?

The raw -> staged -> curated pattern creates clean contracts between pipeline steps.

- Raw preserves validated source records in ticker-partitioned Parquet files.
- Staged holds transformed price data with technical indicators.
- Curated holds analysis-ready outputs and summary metrics.

This separation improves traceability, reprocessing, and debugging. It also mirrors how production analytical platforms are commonly organized.

### Why ticker-level partitioning?

Ticker-level files are the right MVP granularity.

Examples:
- `data/raw/ohlcv/AAPL.parquet`
- `data/staged/indicators/AAPL.parquet`
- `data/curated/returns/AAPL.parquet`

Pros:
- re-running AAPL does not mutate MSFT
- files are easy to inspect manually
- DuckDB can query a whole layer with simple globs
- complexity stays low compared with date partitioning

Why not date partitioning yet?
- daily equity MVP volumes are too small to justify it
- partition management becomes more complex
- it weakens the debugging simplicity that matters most at this stage

## 3. Major Technology Choices

### Python 3.11+

Chosen because it is the dominant language across data engineering, Airflow, analytics, and finance scripting.

Why not another language?
- the surrounding ecosystem for this project is strongest in Python

### yfinance

Chosen because it provides OHLCV, dividends, splits, and metadata through one widely understood interface.

Why not Alpha Vantage or Finnhub first?
- they are good follow-on connectors
- they add API surface and rate-limit concerns without changing the core architecture for MVP

### Pydantic v2 at the ingestion boundary

Chosen because the platform needs a clear data contract where external data enters the system.

Pros:
- explicit schemas
- strong validation
- self-documenting data shapes
- downstream code can trust validated records

Why not manual validation?
- brittle
- repeated across the codebase
- harder to test and reason about

Why not Pandera?
- strong tool, but Pydantic fits this repo well as an explicit typed validation boundary

### Parquet + pyarrow

Chosen because Parquet is columnar, compressed, analytical, and cloud-friendly.

Why not CSV?
- poor typing
- larger files
- slower analytical reads
- weak contract story

Why not Delta Lake?
- useful at larger scale or where ACID/time travel matter
- unnecessary complexity for MVP volumes

### DuckDB for analytical reads

Chosen because it queries Parquet directly with SQL and no server process.

Pros:
- simple local workflow
- strong analytical performance
- excellent match for Parquet zone architecture

Why not SQLite?
- not a natural fit for columnar analytical workloads

Why not Postgres for project data?
- would add a server dependency without improving the data engineering story for this use case
- project data is better represented as analytical files than as rows in an OLTP database

### pandas + numpy for transforms

Chosen because the data volumes are modest and pandas keeps the implementation straightforward at this scale.

Why not Polars?
- technically attractive
- a less necessary dependency at the current project scale

Why not Spark?
- not justified by dataset size
- would add operational ceremony without strengthening the MVP

### Jinja2 + matplotlib for reporting

Chosen because they produce static, shareable output artifacts.

Pros:
- no running web app needed
- reports can be committed and inspected directly
- charts embed cleanly as base64 assets

Why not Streamlit?
- introduces a dashboard-oriented interaction layer that is outside the current scope
- requires a serving layer
- less aligned with the static-report artifact model used here

### Airflow for orchestration

Chosen because it provides explicit task dependencies, retries, scheduling, and run-state visibility for the pipeline.

Pros:
- DAG-based dependency management
- retries and task state visibility
- a mature operational model with clear task state, retries, and scheduling semantics

Why not Prefect?
- cleaner developer experience in many ways
- a different trade-off profile that is less aligned with the current stack choice

Why not cron?
- too primitive
- lacks task graph visibility, retries, and operational state

### Docker Compose

Chosen because it packages the working project together with Airflow and its metadata backend.

Pros:
- reproducible onboarding
- clear separation between local and orchestrated paths
- easy to run repeatedly on a single machine

Why not cloud deployment now?
- it would add infrastructure cost and complexity
- it does not materially improve the MVP at the current stage

## 4. Data Contracts

The project has two contract layers.

### External data contract

Defined by Pydantic schemas for:
- OHLCV records
- dividend events
- split events
- security metadata

This is the strict trust boundary. If source data fails validation, it does not enter storage.

### Internal pipeline contract

After validation, internal processing uses typed runtime models and DataFrame-based transformations.

This design intentionally separates:
- record validation and boundary enforcement
- transformation and analysis logic

That keeps downstream code simpler and avoids repeated defensive checks.

## 5. Orchestration Philosophy

Airflow is the control plane, not the business logic host.

The real pipeline logic lives in Python modules that can be run directly:
- `finance_data_platform.ingestion.run_ingest`
- `finance_data_platform.transforms.run_transform`
- `finance_data_platform.analysis.run_analyze`
- `finance_data_platform.reporting.run_report`

This matters because:
- the pipeline stays testable outside Airflow
- local development is fast
- Airflow remains a thin orchestration layer
- task behavior can be debugged without DAG indirection

Why this matters architecturally:
- no XCom-heavy design
- no logic hidden in DAG definitions
- no lock-in between orchestration and transformation code

## 6. PostgreSQL vs DuckDB

This is the key distinction that often causes confusion.

### DuckDB
DuckDB is the project data query engine.
It operates over raw, staged, and curated Parquet datasets.

### PostgreSQL
PostgreSQL exists only for Airflow metadata.
It stores:
- DAG run history
- task states
- retries
- scheduler metadata
- Airflow users

This is not duplication. These two tools serve completely different responsibilities.

## 7. Known Boundaries

This project intentionally stops short of a number of tempting extensions.

### No machine learning
The project scope is data engineering, not forecasting or quant modeling.

### No interactive dashboard
Static reports are more appropriate for versioned outputs and repeatable generation.

### No dbt yet
The staged/curated model would support dbt later, but Airflow + Python is enough for MVP.

### No distributed compute
The current data size does not justify Spark or cluster orchestration.

### No live cloud deployment
The storage layout is cloud-ready in concept, but deployment is deferred.

## 8. Scaling Path

The architecture was chosen so scaling changes components, not the overall shape.

Potential next steps:
- add more connectors using the same validated schema interface
- migrate transform logic toward dbt SQL models
- move storage paths to S3 or GCS
- add Delta Lake if transactional semantics become valuable
- replace pandas with Spark if data volume grows significantly

The important point is that raw/staged/curated contracts remain stable under these changes.

## 9. Dataclasses and OOP Position

The project uses class-based modeling where it adds clarity and uses functional transforms where that improves determinism.

### Why dataclasses are used
- typed internal runtime objects
- low boilerplate
- clear config and batch ownership
- safe, explicit structure after validation has already occurred

### Can this be described as object-oriented?
Yes, accurately, but with precision.

Recommended wording:

> The platform uses object-oriented domain modeling for validated records and typed runtime state, combined with functional transformation steps for deterministic data processing.

That is more honest than claiming a deeply object-oriented architecture, and it better matches how modern data systems are often built.

## 10. Trade-off Summary

The project consistently favors:
- clarity over cleverness
- reproducibility over convenience
- analytical file storage over server-heavy infrastructure
- thin orchestration over framework-heavy coupling
- clear boundaries over novelty for novelty’s sake

That is the central design principle of the entire repo.
