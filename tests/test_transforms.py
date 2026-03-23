"""Unit tests for transform layer calculations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from finance_data_platform.transforms.enrichment import (
    add_cumulative_returns,
    add_log_returns,
    add_rolling_correlations,
    add_simple_returns,
    build_curated_views,
)
from finance_data_platform.transforms.indicators import (
    add_bollinger_bands,
    add_ema,
    add_macd,
    add_rolling_volatility,
    add_rsi,
    add_sma,
    build_indicator_frame,
)


def _sample_prices() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=6, freq="D")
    return pd.DataFrame(
        {
            "symbol": ["AAPL"] * 6 + ["SPY"] * 6,
            "date": list(dates) * 2,
            "close": [
                100.0,
                101.0,
                102.0,
                104.0,
                103.0,
                105.0,
                200.0,
                202.0,
                201.0,
                203.0,
                204.0,
                206.0,
            ],
            "open": [
                99.0,
                100.0,
                101.0,
                103.0,
                102.0,
                104.0,
                199.0,
                201.0,
                200.0,
                202.0,
                203.0,
                205.0,
            ],
            "high": [
                101.0,
                102.0,
                103.0,
                105.0,
                104.0,
                106.0,
                201.0,
                203.0,
                202.0,
                204.0,
                205.0,
                207.0,
            ],
            "low": [
                98.5,
                99.5,
                100.5,
                102.5,
                101.5,
                103.5,
                198.5,
                200.5,
                199.5,
                201.5,
                202.5,
                204.5,
            ],
            "volume": [10, 11, 12, 13, 14, 15, 20, 21, 22, 23, 24, 25],
        }
    )


def test_add_sma_adds_expected_column() -> None:
    df = add_sma(_sample_prices(), [3])
    aapl_last = df[df["symbol"] == "AAPL"].iloc[-1]
    assert "sma_3" in df.columns
    assert round(aapl_last["sma_3"], 6) == round((104.0 + 103.0 + 105.0) / 3, 6)


def test_add_ema_adds_expected_column() -> None:
    df = add_ema(_sample_prices(), [3])
    assert "ema_3" in df.columns
    assert df[df["symbol"] == "AAPL"]["ema_3"].notna().any()


def test_add_rsi_adds_expected_column() -> None:
    df = add_rsi(_sample_prices(), window=3)
    assert "rsi_3" in df.columns
    assert df[df["symbol"] == "AAPL"]["rsi_3"].notna().any()


def test_add_macd_adds_expected_columns() -> None:
    df = add_macd(_sample_prices(), fast=2, slow=3, signal=2)
    assert {"macd_line", "macd_signal", "macd_hist"}.issubset(df.columns)


def test_add_bollinger_bands_adds_expected_columns() -> None:
    df = add_bollinger_bands(_sample_prices(), window=3)
    assert {"bb_middle_3", "bb_upper_3", "bb_lower_3"}.issubset(df.columns)


def test_add_rolling_volatility_adds_expected_column() -> None:
    df = add_rolling_volatility(_sample_prices(), window=3)
    assert "volatility_3" in df.columns


def test_build_indicator_frame_uses_config() -> None:
    config = yaml.safe_load(Path("config.yaml").read_text())
    df = build_indicator_frame(_sample_prices(), config)
    expected = {
        "sma_20",
        "sma_50",
        "sma_200",
        "ema_12",
        "ema_26",
        "rsi_14",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "bb_middle_20",
        "bb_upper_20",
        "bb_lower_20",
        "volatility_30",
    }
    assert expected.issubset(df.columns)


def test_enrichment_builds_returns_and_correlations() -> None:
    returns_df = add_simple_returns(_sample_prices())
    returns_df = add_log_returns(returns_df)
    returns_df = add_cumulative_returns(returns_df)
    returns_df = add_rolling_correlations(returns_df, benchmark_symbol="SPY", window=3)

    assert "return_1d" in returns_df.columns
    assert "log_return_1d" in returns_df.columns
    assert "cumulative_return" in returns_df.columns
    assert "rolling_corr_3_spy" in returns_df.columns


def test_build_curated_views_returns_expected_frames() -> None:
    curated = build_curated_views(_sample_prices(), benchmark_symbol="SPY", correlation_window=3)
    assert set(curated) == {"returns", "correlations", "curated_prices"}
    assert not curated["returns"].empty
    assert not curated["correlations"].empty
