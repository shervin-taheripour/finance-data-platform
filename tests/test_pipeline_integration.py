"""Offline integration test for the staged/curated/report pipeline."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from finance_data_platform.analysis.run_analyze import main as analyze_main
from finance_data_platform.ingestion.schemas import OHLCVRecord, SecurityMetadata
from finance_data_platform.ingestion.yfinance_connector import TickerIngestionBatch
from finance_data_platform.reporting.run_report import main as report_main
from finance_data_platform.storage.parquet_store import (
    read_partitioned_dataset,
    read_table_dataset,
    write_raw_ticker_batch,
)
from finance_data_platform.transforms.run_transform import main as transform_main


def _write_sample_raw_zone(data_root: Path) -> None:
    aapl_batch = TickerIngestionBatch(
        ticker="AAPL",
        ohlcv=[
            OHLCVRecord(
                symbol="AAPL",
                date=date(2024, 1, day),
                open=100.0 + day,
                high=101.0 + day,
                low=99.0 + day,
                close=100.5 + day,
                adj_close=100.4 + day,
                volume=1_000_000 + day,
            )
            for day in range(1, 9)
        ],
        dividends=[],
        splits=[],
        metadata=SecurityMetadata(
            symbol="AAPL",
            long_name="Apple Inc.",
            sector="Technology",
            currency="USD",
            exchange="NMS",
            as_of_date=date(2024, 1, 8),
        ),
    )
    spy_batch = TickerIngestionBatch(
        ticker="SPY",
        ohlcv=[
            OHLCVRecord(
                symbol="SPY",
                date=date(2024, 1, day),
                open=200.0 + day,
                high=201.0 + day,
                low=199.0 + day,
                close=200.4 + day,
                adj_close=200.3 + day,
                volume=2_000_000 + day,
            )
            for day in range(1, 9)
        ],
        dividends=[],
        splits=[],
        metadata=SecurityMetadata(
            symbol="SPY",
            long_name="SPDR S&P 500 ETF Trust",
            sector="ETF",
            currency="USD",
            exchange="ARCX",
            as_of_date=date(2024, 1, 8),
        ),
    )
    write_raw_ticker_batch(aapl_batch, base_path=str(data_root / "raw"))
    write_raw_ticker_batch(spy_batch, base_path=str(data_root / "raw"))


def test_pipeline_entrypoints_produce_curated_outputs_and_report(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    output_root = tmp_path / "output"
    _write_sample_raw_zone(data_root)

    config = {
        "universe": {
            "tickers": ["AAPL"],
            "benchmark": "SPY",
            "start_date": "2024-01-01",
            "end_date": None,
        },
        "ingestion": {"retry_attempts": 1, "retry_delay_seconds": 0},
        "storage": {"base_path": str(data_root), "format": "parquet"},
        "transforms": {
            "indicators": {
                "sma_windows": [3],
                "ema_windows": [3],
                "rsi_window": 3,
                "macd_fast": 2,
                "macd_slow": 3,
                "macd_signal": 2,
                "bollinger_window": 3,
                "volatility_window": 3,
            },
            "enrichment": {"correlation_window": 3},
        },
        "analysis": {"risk_free_rate": 0.0},
        "reporting": {
            "output_path": str(output_root),
            "template": "src/finance_data_platform/reporting/templates/report.html",
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    transform_main(str(config_path))
    analyze_main(str(config_path))
    report_main(str(config_path))

    staged_indicators = read_partitioned_dataset(
        "indicators",
        zone="staged",
        base_path=str(data_root),
    )
    curated_returns = read_partitioned_dataset(
        "returns",
        zone="curated",
        base_path=str(data_root),
    )
    capm_metrics = read_table_dataset(
        "capm_metrics",
        zone="curated",
        base_path=str(data_root),
    )

    assert not staged_indicators.empty
    assert not curated_returns.empty
    assert not capm_metrics.empty

    report_path = output_root / "aapl_report.html"
    assert report_path.exists()
    html = report_path.read_text(encoding="utf-8")
    assert "AAPL Market Report" in html
    assert "Apple Inc." in html
    assert "data:image/png;base64," in html
