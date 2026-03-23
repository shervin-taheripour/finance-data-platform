"""Unit tests for HTML report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from finance_data_platform.analysis.portfolio import build_portfolio_summary
from finance_data_platform.reporting.generator import render_report
from finance_data_platform.transforms.enrichment import build_curated_views
from finance_data_platform.transforms.indicators import build_indicator_frame


def _sample_prices() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=8, freq="D")
    return pd.DataFrame(
        {
            "symbol": ["AAPL"] * 8 + ["SPY"] * 8,
            "date": list(dates) * 2,
            "close": [
                100,
                101,
                103,
                102,
                104,
                106,
                107,
                109,
                200,
                201,
                202,
                201,
                204,
                205,
                206,
                208,
            ],
            "open": [
                99,
                100,
                102,
                101,
                103,
                105,
                106,
                108,
                199,
                200,
                201,
                200,
                203,
                204,
                205,
                207,
            ],
            "high": [
                101,
                102,
                104,
                103,
                105,
                107,
                108,
                110,
                201,
                202,
                203,
                202,
                205,
                206,
                207,
                209,
            ],
            "low": [
                98,
                99,
                101,
                100,
                102,
                104,
                105,
                107,
                198,
                199,
                200,
                199,
                202,
                203,
                204,
                206,
            ],
            "volume": [10, 11, 12, 13, 14, 15, 16, 17, 20, 21, 22, 23, 24, 25, 26, 27],
        }
    )


def test_render_report_creates_self_contained_html(tmp_path: Path) -> None:
    config = yaml.safe_load(Path("config.yaml").read_text())
    prices = _sample_prices()
    indicators = build_indicator_frame(prices, config)
    curated = build_curated_views(indicators, benchmark_symbol="SPY", correlation_window=3)
    summary = build_portfolio_summary(
        curated["returns"],
        market_symbol="SPY",
        risk_free_rate=0.0,
    )
    metadata = {
        "symbol": "AAPL",
        "long_name": "Apple Inc.",
        "sector": "Technology",
        "currency": "USD",
    }

    output_path = tmp_path / "aapl_report.html"
    report_path = render_report(
        symbol="AAPL",
        metadata=metadata,
        indicator_frame=indicators,
        portfolio_summary=summary,
        output_path=output_path,
    )

    assert report_path.exists()
    html = report_path.read_text(encoding="utf-8")
    assert "AAPL Market Report" in html
    assert "Apple Inc." in html
    assert "data:image/png;base64," in html
    assert "CAPM Relationship" in html
