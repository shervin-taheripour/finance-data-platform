"""Schema and ingestion/storage behavior tests."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest
from pydantic import ValidationError

from finance_data_platform.ingestion.schemas import (
    DividendRecord,
    OHLCVRecord,
    SecurityMetadata,
    SplitRecord,
)
from finance_data_platform.ingestion.yfinance_connector import (
    IngestionConfig,
    fetch_ticker_data,
    fetch_universe,
)
from finance_data_platform.storage.parquet_store import query_raw, write_raw_ticker_batch


class _FakeTicker:
    def __init__(
        self,
        symbol: str,
        history_df: pd.DataFrame,
        dividends_series: pd.Series,
        splits_series: pd.Series,
        metadata: dict[str, object],
    ) -> None:
        self.symbol = symbol
        self._history_df = history_df
        self._dividends_series = dividends_series
        self._splits_series = splits_series
        self._metadata = metadata

    def history(self, **_: object) -> pd.DataFrame:
        return self._history_df.copy()

    @property
    def dividends(self) -> pd.Series:
        return self._dividends_series.copy()

    @property
    def splits(self) -> pd.Series:
        return self._splits_series.copy()

    def get_info(self) -> dict[str, object]:
        return dict(self._metadata)


# -----------------------------
# Pydantic schema tests (P-001)
# -----------------------------


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


# -----------------------------
# Ingestion + raw storage tests
# -----------------------------


def test_fetch_ticker_data_normalizes_and_validates(
    monkeypatch: pytest.MonkeyPatch,
    ingestion_config: IngestionConfig,
    sample_history_df: pd.DataFrame,
    sample_dividends_series: pd.Series,
    sample_splits_series: pd.Series,
    sample_metadata_dict: dict[str, object],
) -> None:
    monkeypatch.setattr(
        "finance_data_platform.ingestion.yfinance_connector.yf.Ticker",
        lambda symbol: _FakeTicker(
            symbol,
            sample_history_df,
            sample_dividends_series,
            sample_splits_series,
            sample_metadata_dict,
        ),
    )

    batch = fetch_ticker_data("aapl", ingestion_config)

    assert batch.ticker == "AAPL"
    assert len(batch.ohlcv) == 2
    assert batch.ohlcv[0].symbol == "AAPL"
    assert len(batch.dividends) == 1
    assert batch.dividends[0].amount == 1.25
    assert len(batch.splits) == 1
    assert batch.splits[0].split_ratio == 2.0
    assert batch.metadata is not None
    assert batch.metadata.symbol == "AAPL"


def test_fetch_ticker_data_retries_once_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    ingestion_config: IngestionConfig,
    sample_history_df: pd.DataFrame,
    sample_dividends_series: pd.Series,
    sample_splits_series: pd.Series,
    sample_metadata_dict: dict[str, object],
) -> None:
    state = {"calls": 0}

    class _FlakyTicker(_FakeTicker):
        def history(self, **_: object) -> pd.DataFrame:
            state["calls"] += 1
            if state["calls"] == 1:
                raise RuntimeError("temporary history failure")
            return super().history()

    monkeypatch.setattr(
        "finance_data_platform.ingestion.yfinance_connector.yf.Ticker",
        lambda symbol: _FlakyTicker(
            symbol,
            sample_history_df,
            sample_dividends_series,
            sample_splits_series,
            sample_metadata_dict,
        ),
    )

    batch = fetch_ticker_data("AAPL", ingestion_config)

    assert state["calls"] == 2
    assert len(batch.ohlcv) == 2


def test_fetch_universe_includes_benchmark_without_duplicates(
    monkeypatch: pytest.MonkeyPatch,
    ingestion_config: IngestionConfig,
    sample_history_df: pd.DataFrame,
    sample_dividends_series: pd.Series,
    sample_splits_series: pd.Series,
    sample_metadata_dict: dict[str, object],
) -> None:
    seen: list[str] = []

    def _factory(symbol: str) -> _FakeTicker:
        seen.append(symbol)
        return _FakeTicker(
            symbol,
            sample_history_df,
            sample_dividends_series,
            sample_splits_series,
            sample_metadata_dict,
        )

    monkeypatch.setattr("finance_data_platform.ingestion.yfinance_connector.yf.Ticker", _factory)

    batches = fetch_universe(ingestion_config)

    assert [batch.ticker for batch in batches] == ["AAPL", "MSFT", "SPY"]
    assert seen == ["AAPL", "MSFT", "SPY"]


def test_write_raw_ticker_batch_writes_ticker_partition_files(
    tmp_path: pytest.TempPathFactory,
    sample_ticker_batch,
) -> None:
    raw_root = tmp_path / "raw"
    write_raw_ticker_batch(sample_ticker_batch, base_path=str(raw_root))

    assert (raw_root / "ohlcv" / "AAPL.parquet").exists()
    assert (raw_root / "dividends" / "AAPL.parquet").exists()
    assert (raw_root / "splits" / "AAPL.parquet").exists()
    assert (raw_root / "metadata" / "AAPL.parquet").exists()


def test_query_raw_can_read_ticker_partitioned_parquet(raw_snapshot_dir) -> None:
    result = query_raw(
        "SELECT symbol, close FROM ohlcv WHERE symbol='AAPL'",
        base_path=str(raw_snapshot_dir),
    )

    assert len(result) == 1
    assert result.iloc[0]["symbol"] == "AAPL"
    assert float(result.iloc[0]["close"]) == 101.5
