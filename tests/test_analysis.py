"""Unit tests for portfolio analysis metrics."""

from __future__ import annotations

import math

import pandas as pd

from finance_data_platform.analysis.portfolio import (
    build_portfolio_summary,
    compute_capm_metrics,
    compute_portfolio_variance,
    compute_sharpe_ratio,
    compute_treynor_ratio,
)


def _sample_returns_long() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=6, freq="D")
    spy = [0.01, 0.02, -0.01, 0.015, 0.005, 0.03]
    aapl = [0.001 + 2 * x for x in spy]
    msft = [0.0005 + 0.8 * x for x in spy]

    rows = []
    for date, spy_ret, aapl_ret, msft_ret in zip(dates, spy, aapl, msft, strict=True):
        rows.extend(
            [
                {"date": date, "symbol": "SPY", "return_1d": spy_ret},
                {"date": date, "symbol": "AAPL", "return_1d": aapl_ret},
                {"date": date, "symbol": "MSFT", "return_1d": msft_ret},
            ]
        )
    return pd.DataFrame(rows)


def test_compute_capm_metrics_returns_expected_beta_and_alpha() -> None:
    metrics = compute_capm_metrics(_sample_returns_long(), market_symbol="SPY")
    assert math.isclose(metrics.loc["AAPL", "beta"], 2.0, rel_tol=1e-9)
    assert math.isclose(metrics.loc["AAPL", "alpha"], 0.001, rel_tol=1e-9)
    assert math.isclose(metrics.loc["MSFT", "beta"], 0.8, rel_tol=1e-9)


def test_compute_sharpe_ratio_returns_series() -> None:
    sharpe = compute_sharpe_ratio(_sample_returns_long(), risk_free_rate=0.0)
    assert isinstance(sharpe, pd.Series)
    assert sharpe.loc["AAPL"] > sharpe.loc["SPY"]


def test_compute_treynor_ratio_returns_series() -> None:
    returns = _sample_returns_long()
    metrics = compute_capm_metrics(returns, market_symbol="SPY")
    treynor = compute_treynor_ratio(returns, metrics, risk_free_rate=0.0)
    assert isinstance(treynor, pd.Series)
    assert treynor.loc["AAPL"] > 0


def test_compute_portfolio_variance_returns_positive_value() -> None:
    variance = compute_portfolio_variance(_sample_returns_long())
    assert variance > 0


def test_build_portfolio_summary_returns_expected_keys() -> None:
    summary = build_portfolio_summary(
        _sample_returns_long(),
        market_symbol="SPY",
        risk_free_rate=0.0,
    )
    assert set(summary) == {
        "returns_wide",
        "capm_metrics",
        "sharpe_ratio",
        "treynor_ratio",
        "equal_weight_variance",
        "latest_cumulative_returns",
    }
    assert not summary["capm_metrics"].empty
    assert summary["equal_weight_variance"] > 0
