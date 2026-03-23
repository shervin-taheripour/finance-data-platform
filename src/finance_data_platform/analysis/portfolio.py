"""Pure portfolio and CAPM analysis helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import pandas as pd


def _coerce_returns_wide(data: pd.DataFrame, return_col: str = "return_1d") -> pd.DataFrame:
    """Accept either long-form returns or already-wide returns."""

    if {"date", "symbol", return_col}.issubset(data.columns):
        wide = data.pivot(index="date", columns="symbol", values=return_col)
        return wide.sort_index()

    return data.sort_index()


def compute_capm_metrics(
    returns: pd.DataFrame,
    market_symbol: str = "SPY",
    periods_per_year: int = 252,
) -> pd.DataFrame:
    """Compute CAPM beta and alpha for each asset against a market series."""

    returns_wide = _coerce_returns_wide(returns).dropna(how="all")
    if market_symbol not in returns_wide.columns:
        raise ValueError(f"Market symbol not found in returns data: {market_symbol}")

    market = returns_wide[market_symbol]
    results: list[dict[str, float | str]] = []

    for symbol in returns_wide.columns:
        if symbol == market_symbol:
            continue

        joined = pd.concat(
            [returns_wide[symbol], market],
            axis=1,
            keys=["asset", "market"],
        ).dropna()
        if joined.empty:
            results.append({"symbol": symbol, "beta": math.nan, "alpha": math.nan})
            continue

        market_var = joined["market"].var(ddof=1)
        if pd.isna(market_var) or market_var == 0:
            beta = math.nan
            alpha = math.nan
        else:
            cov = joined["asset"].cov(joined["market"])
            beta = cov / market_var
            alpha = joined["asset"].mean() - (beta * joined["market"].mean())

        results.append(
            {
                "symbol": symbol,
                "beta": beta,
                "alpha": alpha,
                "annualized_return": joined["asset"].mean() * periods_per_year,
                "annualized_market_return": joined["market"].mean() * periods_per_year,
            }
        )

    return pd.DataFrame(results).set_index("symbol").sort_index()


def compute_sharpe_ratio(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> pd.Series:
    """Compute annualized Sharpe ratio for each asset."""

    returns_wide = _coerce_returns_wide(returns)
    annualized_return = returns_wide.mean() * periods_per_year
    annualized_vol = returns_wide.std(ddof=1) * math.sqrt(periods_per_year)
    sharpe = (annualized_return - risk_free_rate) / annualized_vol.replace(0, pd.NA)
    sharpe.name = "sharpe_ratio"
    return sharpe


def compute_treynor_ratio(
    returns: pd.DataFrame,
    capm_metrics: pd.DataFrame,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> pd.Series:
    """Compute annualized Treynor ratio using CAPM beta as risk measure."""

    returns_wide = _coerce_returns_wide(returns)
    annualized_return = returns_wide.mean() * periods_per_year
    betas = capm_metrics["beta"].reindex(annualized_return.index)
    treynor = (annualized_return - risk_free_rate) / betas.replace(0, pd.NA)
    treynor.name = "treynor_ratio"
    return treynor


def compute_portfolio_variance(
    returns: pd.DataFrame,
    weights: Mapping[str, float] | Sequence[float] | None = None,
    periods_per_year: int = 252,
) -> float:
    """Compute annualized portfolio variance from a return series matrix."""

    returns_wide = _coerce_returns_wide(returns).dropna(how="all")
    cov = returns_wide.cov() * periods_per_year
    columns = list(cov.columns)

    if weights is None:
        weight_values = [1 / len(columns)] * len(columns)
    elif isinstance(weights, Mapping):
        weight_values = [float(weights.get(col, 0.0)) for col in columns]
    else:
        weight_values = [float(value) for value in weights]
        if len(weight_values) != len(columns):
            raise ValueError("Weight vector length must match number of assets")

    total = 0.0
    for i, col_i in enumerate(columns):
        for j, col_j in enumerate(columns):
            total += weight_values[i] * weight_values[j] * float(cov.loc[col_i, col_j])
    return total


def build_portfolio_summary(
    returns: pd.DataFrame,
    market_symbol: str = "SPY",
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> dict[str, object]:
    """Build the main analysis outputs consumed by reporting."""

    returns_wide = _coerce_returns_wide(returns)
    capm_metrics = compute_capm_metrics(
        returns_wide,
        market_symbol=market_symbol,
        periods_per_year=periods_per_year,
    )
    sharpe = compute_sharpe_ratio(
        returns_wide,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )
    treynor = compute_treynor_ratio(
        returns_wide,
        capm_metrics=capm_metrics,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )
    cumulative_returns = (1 + returns_wide.fillna(0)).cumprod() - 1

    return {
        "returns_wide": returns_wide,
        "capm_metrics": capm_metrics,
        "sharpe_ratio": sharpe,
        "treynor_ratio": treynor,
        "equal_weight_variance": compute_portfolio_variance(
            returns_wide,
            periods_per_year=periods_per_year,
        ),
        "latest_cumulative_returns": cumulative_returns.tail(1).T.rename(
            columns={cumulative_returns.index[-1]: "cumulative_return"}
        ),
    }


__all__ = [
    "build_portfolio_summary",
    "compute_capm_metrics",
    "compute_portfolio_variance",
    "compute_sharpe_ratio",
    "compute_treynor_ratio",
]
