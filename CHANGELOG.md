# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-03-23

Initial MVP release.

### Added
- Repository scaffold, packaging, CI workflow, and project configuration
- Pydantic v2 ingestion schemas for OHLCV, dividends, splits, and metadata
- Config-driven yfinance ingestion with retry behavior and typed validation
- Raw-zone ticker-partitioned Parquet storage
- DuckDB raw query interface
- Transform layer for indicators and return/correlation enrichment
- Analysis layer for CAPM, Sharpe, Treynor, and portfolio variance
- Self-contained HTML reporting with Jinja2 and matplotlib
- Staged and curated parquet datasets
- Docker containerization and Docker Compose orchestration
- Airflow DAG for end-to-end pipeline execution
- Offline unit and integration test coverage across all major layers

### Notes
- DuckDB is used for project data querying
- PostgreSQL is used only as the Airflow metadata backend
- A committed sample HTML report is included under `examples/`
