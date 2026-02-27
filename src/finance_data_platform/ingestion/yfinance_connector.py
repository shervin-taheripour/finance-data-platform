"""Config-driven yfinance connector with retry and schema validation."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
import yfinance as yf

from finance_data_platform.ingestion.schemas import (
    DividendRecord,
    OHLCVRecord,
    SecurityMetadata,
    SplitRecord,
)


@dataclass(frozen=True, slots=True)
class UniverseConfig:
    """Universe controls for ingestion runs."""

    tickers: list[str]
    benchmark: str
    start_date: str
    end_date: str | None


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Retry behavior for upstream connector calls."""

    retry_attempts: int
    retry_delay_seconds: int


@dataclass(frozen=True, slots=True)
class StorageConfig:
    """Storage options relevant to ingestion output."""

    base_path: str
    format: str


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    """Typed subset of runtime configuration used by ingestion/storage."""

    universe: UniverseConfig
    ingestion: RetryConfig
    storage: StorageConfig


@dataclass(frozen=True, slots=True)
class TickerIngestionBatch:
    """Validated records for a single ticker and ingestion window."""

    ticker: str
    ohlcv: list[OHLCVRecord]
    dividends: list[DividendRecord]
    splits: list[SplitRecord]
    metadata: SecurityMetadata | None


def load_ingestion_config(config_path: str = "config.yaml") -> IngestionConfig:
    """Load ingestion+storage configuration from the repository config file."""

    config_file = Path(config_path)
    with config_file.open("r", encoding="utf-8") as fh:
        payload: dict[str, Any] = yaml.safe_load(fh) or {}

    universe_payload = payload.get("universe", {})
    ingestion_payload = payload.get("ingestion", {})
    storage_payload = payload.get("storage", {})

    return IngestionConfig(
        universe=UniverseConfig(
            tickers=[str(t).upper() for t in universe_payload.get("tickers", [])],
            benchmark=str(universe_payload.get("benchmark", "SPY")).upper(),
            start_date=str(universe_payload.get("start_date", "2020-01-01")),
            end_date=(
                None
                if universe_payload.get("end_date") is None
                else str(universe_payload.get("end_date"))
            ),
        ),
        ingestion=RetryConfig(
            retry_attempts=int(ingestion_payload.get("retry_attempts", 3)),
            retry_delay_seconds=int(ingestion_payload.get("retry_delay_seconds", 5)),
        ),
        storage=StorageConfig(
            base_path=str(storage_payload.get("base_path", "data")),
            format=str(storage_payload.get("format", "parquet")),
        ),
    )


def _with_retry(cfg: IngestionConfig, op_name: str, fn: Callable[[], Any]) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, cfg.ingestion.retry_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == cfg.ingestion.retry_attempts:
                break
            time.sleep(cfg.ingestion.retry_delay_seconds)

    msg = f"{op_name} failed after {cfg.ingestion.retry_attempts} attempts"
    raise RuntimeError(msg) from last_error


def _to_datetime_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.date


def _normalize_ohlcv_df(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "symbol",
                "date",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
            ]
        )

    normalized = df.reset_index().rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )

    if "date" not in normalized.columns and len(normalized.columns) > 0:
        normalized = normalized.rename(columns={normalized.columns[0]: "date"})

    normalized["symbol"] = ticker.upper()
    normalized["date"] = _to_datetime_date(normalized["date"])

    for col in ["open", "high", "low", "close", "adj_close", "volume"]:
        if col in normalized.columns:
            normalized[col] = pd.to_numeric(normalized[col], errors="coerce")

    required = ["symbol", "date", "open", "high", "low", "close", "volume"]
    normalized = normalized.dropna(subset=required)

    normalized = normalized[
        (normalized["high"] >= normalized["low"])
        & (normalized["open"] >= normalized["low"])
        & (normalized["open"] <= normalized["high"])
        & (normalized["close"] >= normalized["low"])
        & (normalized["close"] <= normalized["high"])
        & (normalized["open"] >= 0)
        & (normalized["high"] >= 0)
        & (normalized["low"] >= 0)
        & (normalized["close"] >= 0)
        & (normalized["volume"] >= 0)
    ]

    if "adj_close" not in normalized.columns:
        normalized["adj_close"] = pd.NA

    return normalized[
        ["symbol", "date", "open", "high", "low", "close", "adj_close", "volume"]
    ]


def _normalize_event_series(series: pd.Series, value_col: str, ticker: str) -> pd.DataFrame:
    if series is None or series.empty:
        return pd.DataFrame(columns=["symbol", "ex_date", value_col])

    normalized = series.reset_index()
    if len(normalized.columns) < 2:
        return pd.DataFrame(columns=["symbol", "ex_date", value_col])

    normalized = normalized.rename(
        columns={
            normalized.columns[0]: "ex_date",
            normalized.columns[1]: value_col,
        }
    )
    normalized["symbol"] = ticker.upper()
    normalized["ex_date"] = _to_datetime_date(normalized["ex_date"])
    normalized[value_col] = pd.to_numeric(normalized[value_col], errors="coerce")
    normalized = normalized.dropna(subset=["symbol", "ex_date", value_col])
    normalized = normalized[normalized[value_col] > 0]
    return normalized[["symbol", "ex_date", value_col]]


def _normalize_metadata(ticker: str, info: dict[str, Any]) -> dict[str, Any]:
    def _non_negative_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            cast_value = int(value)
        except (TypeError, ValueError):
            return None
        return cast_value if cast_value >= 0 else None

    return {
        "symbol": ticker.upper(),
        "short_name": info.get("shortName"),
        "long_name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
        "market_cap": _non_negative_int(info.get("marketCap")),
        "shares_outstanding": _non_negative_int(info.get("sharesOutstanding")),
        "as_of_date": date.today(),
    }


def _validate_ohlcv(rows: pd.DataFrame) -> list[OHLCVRecord]:
    return [OHLCVRecord(**record) for record in rows.to_dict(orient="records")]


def _validate_dividends(rows: pd.DataFrame) -> list[DividendRecord]:
    return [DividendRecord(**record) for record in rows.to_dict(orient="records")]


def _validate_splits(rows: pd.DataFrame) -> list[SplitRecord]:
    return [SplitRecord(**record) for record in rows.to_dict(orient="records")]


def fetch_ticker_data(ticker: str, cfg: IngestionConfig) -> TickerIngestionBatch:
    """Download and validate records for one ticker."""

    symbol = ticker.upper()
    tk = yf.Ticker(symbol)

    history_df = _with_retry(
        cfg,
        f"{symbol} history",
        lambda: tk.history(start=cfg.universe.start_date, end=cfg.universe.end_date, actions=True),
    )
    dividends_series = _with_retry(cfg, f"{symbol} dividends", lambda: tk.dividends)
    splits_series = _with_retry(cfg, f"{symbol} splits", lambda: tk.splits)
    info_payload = _with_retry(
        cfg,
        f"{symbol} metadata",
        lambda: tk.get_info() if hasattr(tk, "get_info") else tk.info,
    )

    normalized_ohlcv = _normalize_ohlcv_df(history_df, symbol)
    normalized_dividends = _normalize_event_series(dividends_series, "amount", symbol)
    normalized_splits = _normalize_event_series(splits_series, "split_ratio", symbol)

    metadata_record: SecurityMetadata | None = None
    if isinstance(info_payload, dict) and info_payload:
        metadata_record = SecurityMetadata(**_normalize_metadata(symbol, info_payload))

    return TickerIngestionBatch(
        ticker=symbol,
        ohlcv=_validate_ohlcv(normalized_ohlcv),
        dividends=_validate_dividends(normalized_dividends),
        splits=_validate_splits(normalized_splits),
        metadata=metadata_record,
    )


def fetch_universe(cfg: IngestionConfig) -> list[TickerIngestionBatch]:
    """Download and validate records for all configured universe tickers."""

    ordered_symbols = [*cfg.universe.tickers]
    if cfg.universe.benchmark not in ordered_symbols:
        ordered_symbols.append(cfg.universe.benchmark)

    unique_symbols = list(dict.fromkeys(symbol.upper() for symbol in ordered_symbols))
    return [fetch_ticker_data(symbol, cfg) for symbol in unique_symbols]


__all__ = [
    "IngestionConfig",
    "RetryConfig",
    "StorageConfig",
    "TickerIngestionBatch",
    "UniverseConfig",
    "fetch_ticker_data",
    "fetch_universe",
    "load_ingestion_config",
]
