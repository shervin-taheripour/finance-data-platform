# Architecture Blueprint

This file is the diagram-ready blueprint for `finance-data-platform`.
It is intentionally written as a flow specification so it can be converted later into Mermaid, Excalidraw, Figma, Lucidchart, or another visual tool.

## System Flow

```text
[External Source]
    yfinance
        |
        v
[Ingestion Layer]
    finance_data_platform.ingestion.yfinance_connector
    - downloads OHLCV, dividends, splits, metadata
    - normalizes payloads
    - validates records with Pydantic
        |
        v
[Raw Zone]
    data/raw/
    - ohlcv/{TICKER}.parquet
    - dividends/{TICKER}.parquet
    - splits/{TICKER}.parquet
    - metadata/{TICKER}.parquet
        |
        v
[Transform Layer]
    finance_data_platform.transforms.indicators
    finance_data_platform.transforms.enrichment
    - adds technical indicators
    - computes returns and rolling correlations
        |
        v
[Staged Zone]
    data/staged/
    - indicators/{TICKER}.parquet
        |
        v
[Analysis Layer]
    finance_data_platform.analysis.portfolio
    - CAPM beta/alpha
    - Sharpe ratio
    - Treynor ratio
    - portfolio variance
        |
        v
[Curated Zone]
    data/curated/
    - returns/{TICKER}.parquet
    - correlations/{TICKER}.parquet
    - curated_prices/{TICKER}.parquet
    - capm_metrics.parquet
    - sharpe_ratio.parquet
    - treynor_ratio.parquet
    - latest_cumulative_returns.parquet
    - portfolio_summary.parquet
        |
        v
[Reporting Layer]
    finance_data_platform.reporting.generator
    - Jinja2 HTML rendering
    - base64-embedded matplotlib charts
        |
        v
[Output Artifacts]
    output/{ticker}_report.html
    examples/sample_report.html
```

## Control Flow

There are two supported execution modes.

### Local Developer Path

```text
make ingest
make transform
make analyze
make report
make pipeline
```

This mode is the fastest loop for development, testing, and debugging.

### Orchestrated Path

```text
Docker Compose
    -> PostgreSQL (Airflow metadata only)
    -> Airflow init
    -> Airflow webserver
    -> Airflow scheduler
        -> DAG: finance_data_platform_pipeline
            -> ingest_raw
            -> transform_staged
            -> analyze_curated
            -> render_reports
```

This mode is for reproducibility, scheduling, and repeatable orchestration.

## Layer Contracts

### 1. Ingestion
- Input: ticker universe + benchmark + date window from `config.yaml`
- Output: validated typed records
- Failure boundary: invalid market records fail before persistence

### 2. Raw Zone
- Contract: preserve validated source records without analytical enrichment
- Format: Parquet
- Partitioning: one file per ticker and data type
- Reason: reprocessability and simple debugging

### 3. Transform Layer
- Contract: pure DataFrame transforms
- Side effects: none inside transform functions
- Outputs: staged indicators and curated return/correlation frames

### 4. Analysis Layer
- Contract: pure analytical functions over curated return data
- Outputs: metric tables and summary objects
- Reason: keeps report rendering separate from finance math

### 5. Reporting Layer
- Contract: consumes prepared datasets and metrics, produces self-contained HTML
- Output: shareable artifact that works without a running app server

## Storage Philosophy

### Project Data
- Storage/query layer: Parquet + DuckDB
- Purpose: analytical workloads, low operational overhead, cloud-friendly format

### Orchestration Metadata
- Storage/query layer: PostgreSQL
- Purpose: Airflow metadata only
- Includes: DAG runs, task instances, retry history, scheduler state

This split is intentional. PostgreSQL is not used for market data; it exists only because Airflow expects a proper metadata backend.

## Runtime Paths and Ownership

### Filesystem mounts
- `./data` is mounted into Airflow containers so task runs write real project artifacts to the host
- `./output` is mounted so generated reports persist outside containers
- `./src`, `./config.yaml`, and `./orchestration/dags` are mounted so code and DAG edits are reflected immediately

### Permission model
- Airflow services run as host UID `1000` via `.env` and Compose user binding
- Reason: mounted Parquet files must remain writable across local and containerized execution paths

## Extension Points

### Add a second connector
- New ingestion module that returns the same validated schema models
- No required redesign of downstream storage or reporting

### Replace pandas transforms with dbt or Spark
- Raw/staged/curated boundaries remain stable
- Only the transform implementation changes

### Replace local storage with S3/GCS
- Preserve Parquet zone contracts
- Swap storage path handling, not analytical contracts

## Diagram Notes for Tomorrow

If you convert this into a visual architecture diagram later, the most important relationships to keep are:
- source -> ingestion -> raw -> transform -> staged -> analysis -> curated -> report
- DuckDB attached to Parquet zones, not as a separate storage server
- Airflow shown as orchestration/control plane, not as data plane
- PostgreSQL shown as Airflow metadata backend only
