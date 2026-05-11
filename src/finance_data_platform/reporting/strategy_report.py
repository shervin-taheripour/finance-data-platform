"""Bucketed strategy report generation from curated datasets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from finance_data_platform.universe_presets import UniversePreset, load_universe_preset

DISCLAIMER = (
    "This is an analytical exercise demonstrating the platform's capabilities. "
    "Not financial advice. Do your own research before making investment decisions."
)
DATA_VIEW_NOTE = "This is a data view. Visualizations deferred to a future iteration."
DEFAULT_TEMPLATE = Path("src/finance_data_platform/reporting/templates/strategy_report.html.j2")


@dataclass(frozen=True, slots=True)
class StrategyTickerRow:
    symbol: str
    company: str
    currency: str
    cumulative_return: float | None
    volatility: float | None
    sharpe_ratio: float | None
    beta: float | None
    alpha: float | None
    has_data: bool
    status: str


@dataclass(frozen=True, slots=True)
class StrategyBucketSummary:
    bucket_id: str
    label: str
    role: str
    tickers_with_data: int
    total_tickers: int
    avg_cumulative_return: float | None
    avg_volatility: float | None
    avg_sharpe_ratio: float | None
    avg_beta: float | None
    beta_aggregate_note: str | None
    has_any_data: bool


@dataclass(frozen=True, slots=True)
class DataQualityIssue:
    symbol: str
    reason: str


@dataclass(frozen=True, slots=True)
class StrategyBucketSection:
    bucket_id: str
    label: str
    role: str
    summary: StrategyBucketSummary
    rows: list[StrategyTickerRow]
    empty_message: str | None


@dataclass(frozen=True, slots=True)
class StrategyReportData:
    preset_name: str
    description: str
    benchmark: str
    generated_at: str
    total_tickers: int
    bucket_count: int
    summary_rows: list[StrategyBucketSummary]
    bucket_sections: list[StrategyBucketSection]
    data_quality_issues: list[DataQualityIssue]
    disclaimer: str = DISCLAIMER
    data_view_note: str = DATA_VIEW_NOTE


def build_strategy_report_data(
    preset: UniversePreset,
    metadata: pd.DataFrame,
    curated_prices: pd.DataFrame,
    capm_metrics: pd.DataFrame,
    sharpe_ratio: pd.DataFrame,
) -> StrategyReportData:
    metadata_latest = _latest_by_symbol(metadata, date_col="as_of_date")
    price_latest = _latest_by_symbol(curated_prices, date_col="date")
    capm_by_symbol = capm_metrics.set_index("symbol") if not capm_metrics.empty else pd.DataFrame()
    sharpe_by_symbol = (
        sharpe_ratio.set_index("symbol")
        if not sharpe_ratio.empty
        else pd.DataFrame(columns=["sharpe_ratio"])
    )

    issues: list[DataQualityIssue] = []
    bucket_sections: list[StrategyBucketSection] = []
    summary_rows: list[StrategyBucketSummary] = []

    for bucket in preset.payload.get("buckets", []):
        rows: list[StrategyTickerRow] = []
        data_rows: list[StrategyTickerRow] = []
        beta_values: list[float] = []
        beta_eligible_count = 0

        for item in bucket.get("tickers", []):
            symbol = str(item["symbol"]).upper()
            company = str(item.get("company", symbol))
            preset_currency = str(item.get("currency", "USD")).upper()

            meta_row = metadata_latest.loc[symbol] if symbol in metadata_latest.index else None
            price_row = price_latest.loc[symbol] if symbol in price_latest.index else None
            capm_row = capm_by_symbol.loc[symbol] if symbol in capm_by_symbol.index else None
            sharpe_row = sharpe_by_symbol.loc[symbol] if symbol in sharpe_by_symbol.index else None

            currency = preset_currency
            if meta_row is not None and pd.notna(meta_row.get("currency")):
                currency = str(meta_row.get("currency")).upper()
            if meta_row is not None and pd.notna(meta_row.get("long_name")):
                company = str(meta_row.get("long_name"))

            if price_row is None:
                rows.append(
                    StrategyTickerRow(
                        symbol=symbol,
                        company=company,
                        currency=currency,
                        cumulative_return=None,
                        volatility=None,
                        sharpe_ratio=None,
                        beta=None,
                        alpha=None,
                        has_data=False,
                        status="data not available",
                    )
                )
                issues.append(DataQualityIssue(symbol=symbol, reason="no curated data found"))
                continue

            ticker_row = StrategyTickerRow(
                symbol=symbol,
                company=company,
                currency=currency,
                cumulative_return=_maybe_float(price_row.get("cumulative_return")),
                volatility=_maybe_float(price_row.get("volatility_30")),
                sharpe_ratio=(
                    _maybe_float(sharpe_row.get("sharpe_ratio")) if sharpe_row is not None else None
                ),
                beta=_maybe_float(capm_row.get("beta")) if capm_row is not None else None,
                alpha=_maybe_float(capm_row.get("alpha")) if capm_row is not None else None,
                has_data=True,
                status="ok",
            )
            rows.append(ticker_row)
            data_rows.append(ticker_row)

            if currency == "USD":
                beta_eligible_count += 1
                if ticker_row.beta is not None:
                    beta_values.append(ticker_row.beta)
            else:
                issues.append(
                    DataQualityIssue(
                        symbol=symbol,
                        reason=(
                            f"non-USD listing ({currency}) — beta excluded from aggregate"
                        ),
                    )
                )

        summary = StrategyBucketSummary(
            bucket_id=str(bucket.get("id", "")),
            label=str(bucket.get("label", "")),
            role=str(bucket.get("role", "")),
            tickers_with_data=len(data_rows),
            total_tickers=len(bucket.get("tickers", [])),
            avg_cumulative_return=_mean_or_none([row.cumulative_return for row in data_rows]),
            avg_volatility=_mean_or_none([row.volatility for row in data_rows]),
            avg_sharpe_ratio=_mean_or_none([row.sharpe_ratio for row in data_rows]),
            avg_beta=_mean_or_none(beta_values),
            beta_aggregate_note=(
                None
                if beta_eligible_count == len(data_rows)
                else f"USD-only: {beta_eligible_count} tickers"
            ),
            has_any_data=bool(data_rows),
        )
        summary_rows.append(summary)
        bucket_sections.append(
            StrategyBucketSection(
                bucket_id=summary.bucket_id,
                label=summary.label,
                role=summary.role,
                summary=summary,
                rows=rows,
                empty_message=(None if data_rows else "No data available for this bucket."),
            )
        )

    return StrategyReportData(
        preset_name=preset.name,
        description=str(preset.payload.get("description", "")),
        benchmark=preset.benchmark,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        total_tickers=len(preset.tickers),
        bucket_count=len(summary_rows),
        summary_rows=summary_rows,
        bucket_sections=bucket_sections,
        data_quality_issues=issues,
    )


def render_strategy_report(
    report_data: StrategyReportData,
    output_path: str | Path,
    template_path: str | Path = DEFAULT_TEMPLATE,
) -> Path:
    template_path = Path(template_path)
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_path.name)
    html = template.render(report=report_data, format_metric=_format_metric)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def load_strategy_preset(
    preset_name: str,
    *,
    preset_dir: str | Path = "config/universes",
) -> UniversePreset:
    return load_universe_preset(preset_name, preset_dir=preset_dir)


def _latest_by_symbol(df: pd.DataFrame, *, date_col: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame().set_index(pd.Index([], name="symbol"))
    if date_col not in df.columns:
        return df.drop_duplicates(subset=["symbol"], keep="last").set_index("symbol")
    ordered = df.sort_values(["symbol", date_col]).drop_duplicates(subset=["symbol"], keep="last")
    return ordered.set_index("symbol")


def _mean_or_none(values: list[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _maybe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _format_metric(value: float | None, *, kind: str) -> str:
    if value is None:
        return "n/a"
    if kind == "percent":
        return f"{value:.2%}"
    if kind == "decimal":
        return f"{value:.2f}"
    if kind == "decimal_4":
        return f"{value:.4f}"
    return str(value)


__all__ = [
    "DATA_VIEW_NOTE",
    "DISCLAIMER",
    "DataQualityIssue",
    "StrategyBucketSection",
    "StrategyBucketSummary",
    "StrategyReportData",
    "StrategyTickerRow",
    "build_strategy_report_data",
    "load_strategy_preset",
    "render_strategy_report",
]
