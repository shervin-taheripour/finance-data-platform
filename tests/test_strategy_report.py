"""Tests for the strategy report aggregation and rendering path."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from finance_data_platform.reporting.strategy_report import (
    DATA_VIEW_NOTE,
    DISCLAIMER,
    build_strategy_report_data,
    load_strategy_preset,
    render_strategy_report,
)
from finance_data_platform.universe_presets import load_universe_preset


def _fixture_metadata() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "long_name": "Alpha Corp",
                "currency": "USD",
                "as_of_date": "2024-01-08",
            },
            {
                "symbol": "BBB",
                "long_name": "Beta Corp",
                "currency": "USD",
                "as_of_date": "2024-01-08",
            },
            {
                "symbol": "CCC",
                "long_name": "Gamma Corp",
                "currency": "USD",
                "as_of_date": "2024-01-08",
            },
            {
                "symbol": "DDD.T",
                "long_name": "Delta KK",
                "currency": "JPY",
                "as_of_date": "2024-01-08",
            },
        ]
    )


def _fixture_curated_prices() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "date": "2024-01-08",
                "cumulative_return": 0.10,
                "volatility_30": 0.20,
            },
            {
                "symbol": "BBB",
                "date": "2024-01-08",
                "cumulative_return": 0.20,
                "volatility_30": 0.30,
            },
            {
                "symbol": "CCC",
                "date": "2024-01-08",
                "cumulative_return": 0.30,
                "volatility_30": 0.40,
            },
            {
                "symbol": "DDD.T",
                "date": "2024-01-08",
                "cumulative_return": 0.40,
                "volatility_30": 0.50,
            },
        ]
    )


def _fixture_capm() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"symbol": "AAA", "beta": 1.0, "alpha": 0.0010},
            {"symbol": "BBB", "beta": 2.0, "alpha": 0.0020},
            {"symbol": "CCC", "beta": 3.0, "alpha": 0.0030},
            {"symbol": "DDD.T", "beta": 4.0, "alpha": 0.0040},
        ]
    )


def _fixture_sharpe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"symbol": "AAA", "sharpe_ratio": 1.0},
            {"symbol": "BBB", "sharpe_ratio": 2.0},
            {"symbol": "CCC", "sharpe_ratio": 3.0},
            {"symbol": "DDD.T", "sharpe_ratio": 4.0},
        ]
    )


def test_bucket_aggregation_basic() -> None:
    preset = load_universe_preset(
        "strategy_fixture",
        preset_dir=Path("tests/fixtures"),
    )
    report = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=_fixture_curated_prices(),
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    summary = {row.bucket_id: row for row in report.summary_rows}
    assert summary["core"].tickers_with_data == 2
    assert summary["core"].avg_cumulative_return == pytest.approx(0.15)
    assert summary["core"].avg_volatility == pytest.approx(0.25)
    assert summary["core"].avg_sharpe_ratio == pytest.approx(1.5)
    assert summary["core"].avg_beta == pytest.approx(1.5)


def test_bucket_aggregation_handles_missing_tickers() -> None:
    preset = load_universe_preset("strategy_fixture", preset_dir=Path("tests/fixtures"))
    prices = _fixture_curated_prices()[lambda df: df["symbol"] != "BBB"]
    report = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=prices,
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    issues = {issue.symbol: issue.reason for issue in report.data_quality_issues}
    assert issues["BBB"] == "no curated data found"
    core_summary = next(row for row in report.summary_rows if row.bucket_id == "core")
    assert core_summary.tickers_with_data == 1
    assert core_summary.total_tickers == 2


def test_bucket_aggregation_handles_empty_bucket() -> None:
    preset = load_universe_preset("strategy_fixture", preset_dir=Path("tests/fixtures"))
    report = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=_fixture_curated_prices(),
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    empty_bucket = next(bucket for bucket in report.bucket_sections if bucket.bucket_id == "empty")
    assert empty_bucket.empty_message == "No data available for this bucket."
    assert empty_bucket.summary.has_any_data is False


def test_bucket_aggregation_excludes_non_usd_from_beta() -> None:
    preset = load_universe_preset("strategy_fixture", preset_dir=Path("tests/fixtures"))
    report = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=_fixture_curated_prices(),
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    global_summary = next(row for row in report.summary_rows if row.bucket_id == "global")
    assert global_summary.avg_beta == pytest.approx(3.0)
    assert global_summary.avg_cumulative_return == pytest.approx(0.35)
    assert global_summary.avg_volatility == pytest.approx(0.45)
    assert global_summary.avg_sharpe_ratio == pytest.approx(3.5)
    assert global_summary.beta_aggregate_note == "USD-only: 1 tickers"


def test_bucket_aggregation_partial_bucket_count() -> None:
    preset = load_universe_preset("strategy_fixture", preset_dir=Path("tests/fixtures"))
    prices = _fixture_curated_prices()[lambda df: df["symbol"] != "BBB"]
    report = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=prices,
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    core_summary = next(row for row in report.summary_rows if row.bucket_id == "core")
    assert core_summary.tickers_with_data == 1
    assert core_summary.total_tickers == 2


def test_strategy_report_renders(tmp_path: Path) -> None:
    preset = load_strategy_preset("strategy_fixture", preset_dir=Path("tests/fixtures"))
    report_data = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=_fixture_curated_prices(),
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    report_path = render_strategy_report(report_data, tmp_path / "strategy_report.html")
    html = report_path.read_text(encoding="utf-8")
    assert "Core Names" in html
    assert "Global Names" in html
    assert "AAA" in html
    assert "DDD.T" in html


def test_strategy_report_marks_non_usd_tickers(tmp_path: Path) -> None:
    preset = load_strategy_preset("strategy_fixture", preset_dir=Path("tests/fixtures"))
    report_data = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=_fixture_curated_prices(),
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    report_path = render_strategy_report(report_data, tmp_path / "strategy_report.html")
    html = report_path.read_text(encoding="utf-8")
    assert "JPY" in html
    assert "DDD.T" in html


def test_strategy_report_excludes_no_data_tickers_from_aggregates() -> None:
    preset = load_universe_preset("strategy_fixture", preset_dir=Path("tests/fixtures"))
    prices = _fixture_curated_prices()[lambda df: df["symbol"] != "BBB"]
    report = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=prices,
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    core_summary = next(row for row in report.summary_rows if row.bucket_id == "core")
    assert core_summary.avg_cumulative_return == 0.10
    core_bucket = next(bucket for bucket in report.bucket_sections if bucket.bucket_id == "core")
    missing_row = next(row for row in core_bucket.rows if row.symbol == "BBB")
    assert missing_row.status == "data not available"


def test_strategy_report_includes_disclaimer(tmp_path: Path) -> None:
    preset = load_strategy_preset("strategy_fixture", preset_dir=Path("tests/fixtures"))
    report_data = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=_fixture_curated_prices(),
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    report_path = render_strategy_report(report_data, tmp_path / "strategy_report.html")
    html = report_path.read_text(encoding="utf-8")
    assert DISCLAIMER in html


def test_strategy_report_includes_data_view_note(tmp_path: Path) -> None:
    preset = load_strategy_preset("strategy_fixture", preset_dir=Path("tests/fixtures"))
    report_data = build_strategy_report_data(
        preset=preset,
        metadata=_fixture_metadata(),
        curated_prices=_fixture_curated_prices(),
        capm_metrics=_fixture_capm(),
        sharpe_ratio=_fixture_sharpe(),
    )

    report_path = render_strategy_report(report_data, tmp_path / "strategy_report.html")
    html = report_path.read_text(encoding="utf-8")
    assert DATA_VIEW_NOTE in html
