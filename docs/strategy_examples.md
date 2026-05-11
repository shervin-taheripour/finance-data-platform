# Strategy Examples

This document describes the first worked-example report built on top of the platform's curated data layer.

## Semiconductor Supply Chain Preset

Preset file:
- `config/universes/semiconductor_supply_chain.yaml`

The preset groups an AI infrastructure thesis into six buckets and uses `SPY` as the benchmark for CAPM-derived metrics.

### Bucket Layout

| Bucket ID | Label | Role | Tickers |
|---|---|---|---|
| `core_wfe` | Core Semiconductor Equipment | Long-term compounders with deep moats | `ASML`, `AMAT`, `KLAC` |
| `wfe_cycle` | WFE Cycle Exposure | Cyclical upside from fab spending | `LRCX`, `8035.T`, `ASMIY` |
| `packaging_osat` | Advanced Packaging and OSAT | Beneficiaries of chip complexity and AI packaging | `BESIY`, `AMKR`, `ASX` |
| `networking` | Data-Center Networking | AI cluster networking and hyperscaler build-outs | `ANET`, `2345.TW` |
| `power_cooling` | Power and Cooling | Electrical and thermal infrastructure for AI deployment | `VRT`, `ETN`, `SU.PA` |
| `platform_anchors` | Platform Anchors | Large-cap ecosystem anchors influencing AI capex | `NVDA`, `MSFT`, `GOOGL`, `TSM` |

Total preset tickers: `18`

Benchmark ticker used during analysis: `SPY`

## How the Strategy Report Works

The strategy report does not introduce a new analytics stack. It consumes the same curated outputs already produced by the platform:

- `data/curated/curated_prices/*.parquet`
- `data/curated/capm_metrics.parquet`
- `data/curated/sharpe_ratio.parquet`
- raw metadata from `data/raw/metadata/*.parquet`

For each bucket, the report shows:
- ticker coverage (`tickers with data / total tickers`)
- average cumulative return
- average volatility
- average Sharpe ratio
- average beta versus the configured benchmark

## Data Handling Rules

### Non-USD listings
Non-USD listings remain visible in the report and keep their currency tags.

Their:
- cumulative return
- volatility
- Sharpe ratio

still contribute to bucket averages.

Their beta is excluded from the aggregate bucket beta and the report calls this out explicitly with a `USD-only` note.

### Missing data
If a ticker does not have curated output, the report keeps the ticker row and marks it as `data not available`.

If an entire bucket has no data, the report renders the bucket anyway and displays an explicit empty-bucket message.

## Run Path

Shortcut path:

```bash
make PYTHON=.venv/bin/python3 strategy-semiconductor
```

Publish shortcut:

```bash
make PYTHON=.venv/bin/python3 strategy-semiconductor-publish
```

Output artifact:
- `output/strategy_semiconductor_supply_chain.html`

Committed sample artifact:
- `examples/sample_strategy_report.html`

Published path after upload:
- `https://d9m4ljhm4l3qi.cloudfront.net/reports/strategy_semiconductor_supply_chain.html`
