"""Shared pytest fixtures for ingestion and raw-zone storage tests."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from finance_data_platform.ingestion.schemas import (
    DividendRecord,
    OHLCVRecord,
    SecurityMetadata,
    SplitRecord,
)
from finance_data_platform.ingestion.yfinance_connector import (
    IngestionConfig,
    RetryConfig,
    StorageConfig,
    TickerIngestionBatch,
    UniverseConfig,
)
from finance_data_platform.storage.parquet_store import write_raw_ticker_batch


@pytest.fixture
def sample_history_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.5, 100.5],
            "Close": [101.5, 102.5],
            "Adj Close": [101.4, 102.4],
            "Volume": [1_000_000, 1_100_000],
            "Dividends": [0.0, 0.0],
            "Stock Splits": [0.0, 0.0],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )


@pytest.fixture
def sample_dividends_series() -> pd.Series:
    return pd.Series([1.25], index=pd.to_datetime(["2024-01-15"]), name="Dividends")


@pytest.fixture
def sample_splits_series() -> pd.Series:
    return pd.Series([2.0], index=pd.to_datetime(["2024-01-20"]), name="Stock Splits")


@pytest.fixture
def sample_metadata_dict() -> dict[str, object]:
    return {
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
        "currency": "USD",
        "exchange": "NMS",
        "marketCap": 3_000_000_000_000,
        "sharesOutstanding": 15_600_000_000,
    }


@pytest.fixture
def ingestion_config(tmp_path: pytest.TempPathFactory) -> IngestionConfig:
    return IngestionConfig(
        universe=UniverseConfig(
            tickers=["AAPL", "MSFT"],
            benchmark="SPY",
            start_date="2024-01-01",
            end_date="2024-01-31",
        ),
        ingestion=RetryConfig(retry_attempts=3, retry_delay_seconds=0),
        storage=StorageConfig(base_path=str(tmp_path), format="parquet"),
    )


@pytest.fixture
def sample_ticker_batch() -> TickerIngestionBatch:
    return TickerIngestionBatch(
        ticker="AAPL",
        ohlcv=[
            OHLCVRecord(
                symbol="AAPL",
                date=date(2024, 1, 2),
                open=100.0,
                high=102.0,
                low=99.5,
                close=101.5,
                adj_close=101.4,
                volume=1_000_000,
            )
        ],
        dividends=[
            DividendRecord(
                symbol="AAPL",
                ex_date=date(2024, 1, 15),
                amount=1.25,
            )
        ],
        splits=[
            SplitRecord(
                symbol="AAPL",
                ex_date=date(2024, 1, 20),
                split_ratio=2.0,
            )
        ],
        metadata=SecurityMetadata(
            symbol="AAPL",
            short_name="Apple Inc.",
            exchange="NMS",
            market_cap=3_000_000_000_000,
            shares_outstanding=15_600_000_000,
            as_of_date=date(2024, 1, 31),
        ),
    )


@pytest.fixture
def raw_snapshot_dir(tmp_path: pytest.TempPathFactory, sample_ticker_batch: TickerIngestionBatch):
    raw_root = tmp_path / "raw_snapshots"
    write_raw_ticker_batch(sample_ticker_batch, base_path=str(raw_root))
    return raw_root
