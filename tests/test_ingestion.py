"""Schema validation tests for ingestion contracts."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from finance_data_platform.ingestion.schemas import (
    DividendRecord,
    OHLCVRecord,
    SecurityMetadata,
    SplitRecord,
)


def test_valid_ohlcv_record() -> None:
    record = OHLCVRecord(
        symbol="aapl",
        date=date(2024, 2, 1),
        open=184.2,
        high=186.1,
        low=183.8,
        close=185.7,
        adj_close=185.3,
        volume=1_234_567,
    )

    assert record.symbol == "AAPL"
    assert record.volume == 1_234_567


def test_ohlcv_rejects_invalid_range() -> None:
    with pytest.raises(ValidationError):
        OHLCVRecord(
            symbol="MSFT",
            date=date(2024, 2, 1),
            open=409.1,
            high=407.0,
            low=408.0,
            close=408.5,
            volume=500_000,
        )


def test_ohlcv_rejects_future_date() -> None:
    with pytest.raises(ValidationError):
        OHLCVRecord(
            symbol="GOOGL",
            date=date.today() + timedelta(days=1),
            open=140.0,
            high=141.0,
            low=139.5,
            close=140.6,
            volume=250_000,
        )


def test_valid_dividend_record() -> None:
    record = DividendRecord(symbol="jpm", ex_date=date(2024, 1, 3), amount=1.1)
    assert record.symbol == "JPM"
    assert record.amount == 1.1


def test_split_rejects_non_positive_ratio() -> None:
    with pytest.raises(ValidationError):
        SplitRecord(symbol="BAC", ex_date=date(2024, 1, 10), split_ratio=0)


def test_metadata_rejects_negative_market_cap() -> None:
    with pytest.raises(ValidationError):
        SecurityMetadata(
            symbol="GS",
            short_name="Goldman Sachs",
            market_cap=-1,
        )


def test_valid_metadata_record() -> None:
    record = SecurityMetadata(
        symbol="spy",
        long_name="SPDR S&P 500 ETF Trust",
        exchange="NYSE Arca",
        market_cap=500_000_000_000,
        shares_outstanding=900_000_000,
        as_of_date=date(2024, 2, 1),
    )

    assert record.symbol == "SPY"
    assert record.exchange == "NYSE Arca"
