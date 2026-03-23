"""Pure technical indicator transforms for OHLCV price data."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _prepare_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize ordering and required columns before indicator calculation."""

    required = {"symbol", "date", "close"}
    missing = required - set(df.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns: {missing_cols}")

    prepared = df.copy()
    prepared["date"] = pd.to_datetime(prepared["date"], errors="coerce")
    prepared = prepared.sort_values(["symbol", "date"]).reset_index(drop=True)
    return prepared


def add_sma(df: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    """Add simple moving average columns for each configured window."""

    enriched = _prepare_price_frame(df)
    for window in windows:
        enriched[f"sma_{window}"] = enriched.groupby("symbol")["close"].transform(
            lambda s, w=window: s.rolling(w).mean()
        )
    return enriched


def add_ema(df: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    """Add exponential moving average columns for each configured window."""

    enriched = _prepare_price_frame(df)
    for window in windows:
        enriched[f"ema_{window}"] = enriched.groupby("symbol")["close"].transform(
            lambda s, w=window: s.ewm(span=w, adjust=False).mean()
        )
    return enriched


def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """Add relative strength index using Wilder-style exponential smoothing."""

    enriched = _prepare_price_frame(df)

    def _rsi(series: pd.Series) -> pd.Series:
        delta = series.diff()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)
        avg_gain = gains.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
        avg_loss = losses.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        return 100 - (100 / (1 + rs))

    enriched[f"rsi_{window}"] = enriched.groupby("symbol")["close"].transform(_rsi)
    return enriched


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Add MACD line, signal, and histogram columns."""

    enriched = _prepare_price_frame(df)
    grouped = enriched.groupby("symbol")["close"]
    ema_fast = grouped.transform(lambda s: s.ewm(span=fast, adjust=False).mean())
    ema_slow = grouped.transform(lambda s: s.ewm(span=slow, adjust=False).mean())
    enriched["macd_line"] = ema_fast - ema_slow
    enriched["macd_signal"] = enriched.groupby("symbol")["macd_line"].transform(
        lambda s: s.ewm(span=signal, adjust=False).mean()
    )
    enriched["macd_hist"] = enriched["macd_line"] - enriched["macd_signal"]
    return enriched


def add_bollinger_bands(
    df: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Add Bollinger middle, upper, and lower bands."""

    enriched = _prepare_price_frame(df)
    rolling_mean = enriched.groupby("symbol")["close"].transform(
        lambda s: s.rolling(window).mean()
    )
    rolling_std = enriched.groupby("symbol")["close"].transform(
        lambda s: s.rolling(window).std()
    )
    enriched[f"bb_middle_{window}"] = rolling_mean
    enriched[f"bb_upper_{window}"] = rolling_mean + (num_std * rolling_std)
    enriched[f"bb_lower_{window}"] = rolling_mean - (num_std * rolling_std)
    return enriched


def add_rolling_volatility(
    df: pd.DataFrame,
    window: int = 30,
    annualization: int = 252,
) -> pd.DataFrame:
    """Add annualized rolling volatility based on close-to-close returns."""

    enriched = _prepare_price_frame(df)

    def _volatility(series: pd.Series) -> pd.Series:
        returns = series.pct_change()
        return returns.rolling(window).std() * (annualization**0.5)

    enriched[f"volatility_{window}"] = enriched.groupby("symbol")["close"].transform(
        _volatility
    )
    return enriched


def build_indicator_frame(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Apply the full indicator stack using transform config from config.yaml."""

    indicators_cfg = config["transforms"]["indicators"]
    enriched = _prepare_price_frame(df)
    enriched = add_sma(enriched, indicators_cfg["sma_windows"])
    enriched = add_ema(enriched, indicators_cfg["ema_windows"])
    enriched = add_rsi(enriched, indicators_cfg["rsi_window"])
    enriched = add_macd(
        enriched,
        fast=indicators_cfg["macd_fast"],
        slow=indicators_cfg["macd_slow"],
        signal=indicators_cfg["macd_signal"],
    )
    enriched = add_bollinger_bands(enriched, indicators_cfg["bollinger_window"])
    enriched = add_rolling_volatility(enriched, indicators_cfg["volatility_window"])
    return enriched


__all__ = [
    "add_bollinger_bands",
    "add_ema",
    "add_macd",
    "add_rolling_volatility",
    "add_rsi",
    "add_sma",
    "build_indicator_frame",
]
