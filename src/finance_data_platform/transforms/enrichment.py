"""Pure enrichment transforms for returns and correlation analytics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prepare_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    required = {"symbol", "date", "close"}
    missing = required - set(df.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns: {missing_cols}")

    prepared = df.copy()
    prepared["date"] = pd.to_datetime(prepared["date"], errors="coerce")
    prepared = prepared.sort_values(["symbol", "date"]).reset_index(drop=True)
    return prepared


def add_simple_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add close-to-close simple returns per symbol."""

    enriched = _prepare_price_frame(df)
    enriched["return_1d"] = enriched.groupby("symbol")["close"].pct_change()
    return enriched


def add_log_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add close-to-close log returns per symbol."""

    enriched = _prepare_price_frame(df)
    ratios = enriched.groupby("symbol")["close"].transform(lambda s: s / s.shift(1))
    ratios = ratios.where(ratios > 0)
    enriched["log_return_1d"] = np.log(ratios)
    return enriched


def add_cumulative_returns(df: pd.DataFrame, return_col: str = "return_1d") -> pd.DataFrame:
    """Add cumulative returns from a simple-return column."""

    if return_col not in df.columns:
        raise ValueError(f"Missing required return column: {return_col}")

    enriched = _prepare_price_frame(df)
    enriched[return_col] = df[return_col].values
    enriched["cumulative_return"] = enriched.groupby("symbol")[return_col].transform(
        lambda s: (1 + s.fillna(0)).cumprod() - 1
    )
    return enriched


def add_rolling_correlations(
    df: pd.DataFrame,
    benchmark_symbol: str,
    window: int = 60,
) -> pd.DataFrame:
    """Add rolling correlation of each symbol's returns to the benchmark."""

    working = add_simple_returns(df)
    returns_wide = working.pivot(index="date", columns="symbol", values="return_1d").sort_index()

    if benchmark_symbol not in returns_wide.columns:
        raise ValueError(f"Benchmark symbol not found in returns frame: {benchmark_symbol}")

    correlations = []
    benchmark_returns = returns_wide[benchmark_symbol]
    for symbol in returns_wide.columns:
        series = returns_wide[symbol].rolling(window).corr(benchmark_returns)
        correlations.append(
            pd.DataFrame(
                {
                    "date": series.index,
                    "symbol": symbol,
                    f"rolling_corr_{window}_{benchmark_symbol.lower()}": series.values,
                }
            )
        )

    corr_df = pd.concat(correlations, ignore_index=True)
    enriched = working.merge(corr_df, on=["date", "symbol"], how="left")
    return enriched.sort_values(["symbol", "date"]).reset_index(drop=True)


def build_curated_views(
    df: pd.DataFrame,
    benchmark_symbol: str,
    correlation_window: int = 60,
) -> dict[str, pd.DataFrame]:
    """Build the main curated views used downstream by analysis/reporting."""

    with_returns = add_simple_returns(df)
    with_log_returns = add_log_returns(with_returns)
    with_cumulative_returns = add_cumulative_returns(with_log_returns)
    with_correlations = add_rolling_correlations(
        with_cumulative_returns,
        benchmark_symbol=benchmark_symbol,
        window=correlation_window,
    )

    returns = with_correlations[
        ["symbol", "date", "return_1d", "log_return_1d", "cumulative_return"]
    ]
    rolling_corr_col = f"rolling_corr_{correlation_window}_{benchmark_symbol.lower()}"
    correlations = with_correlations[["symbol", "date", rolling_corr_col]]

    return {
        "returns": returns.sort_values(["symbol", "date"]).reset_index(drop=True),
        "correlations": correlations.sort_values(["symbol", "date"]).reset_index(drop=True),
        "curated_prices": with_correlations,
    }


__all__ = [
    "add_cumulative_returns",
    "add_log_returns",
    "add_rolling_correlations",
    "add_simple_returns",
    "build_curated_views",
]
