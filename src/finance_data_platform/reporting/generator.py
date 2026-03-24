"""Self-contained HTML report generation for the finance data platform."""

from __future__ import annotations

import base64
import io
import logging
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_TEMPLATE = Path("src/finance_data_platform/reporting/templates/report.html")
DEFAULT_FIELD_REGISTRY = Path("config/report_fields.yaml")
LOGGER = logging.getLogger(__name__)


def fig_to_base64(fig: plt.Figure) -> str:
    """Convert a Matplotlib figure to a base64 PNG string."""

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


@cache
def _load_field_registry(
    registry_path: str,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    payload = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8")) or {}
    exact: dict[str, dict[str, Any]] = {}
    patterns: list[dict[str, Any]] = []
    for item in payload.get("fields", []):
        field_name = str(item["field_name"])
        entry = {
            "field_name": field_name,
            "display_label": str(item["display_label"]),
            "section": str(item.get("section", "general")),
            "format_type": str(item.get("format_type", "text")),
        }
        if field_name.endswith("*"):
            patterns.append(entry)
        else:
            exact[field_name] = entry
    return exact, patterns


def _field_spec(name: str, registry_path: Path) -> dict[str, Any] | None:
    exact, patterns = _load_field_registry(str(registry_path))
    if name in exact:
        return exact[name]
    for entry in patterns:
        prefix = entry["field_name"][:-1]
        if name.startswith(prefix):
            match = dict(entry)
            match["suffix"] = name[len(prefix) :]
            return match
    return None


def _fallback_label(name: str) -> str:
    return name.replace("_", " ").title()


def _display_label(name: str, registry_path: Path) -> str:
    spec = _field_spec(name, registry_path)
    if spec is None:
        return _fallback_label(name)
    suffix = spec.get("suffix")
    if suffix is None:
        return spec["display_label"]
    return spec["display_label"].format(suffix=suffix)


def _format_value(field_name: str, value: Any, registry_path: Path) -> Any:
    if pd.isna(value):
        return "n/a"

    spec = _field_spec(field_name, registry_path)
    format_type = spec["format_type"] if spec is not None else "text"

    if format_type == "text":
        return value
    if format_type == "source_name" and isinstance(value, str):
        return value.replace("yfinance", "Yahoo Finance")
    if format_type == "integer":
        return f"{int(value):,}"

    numeric = float(value)
    if format_type.startswith("decimal_"):
        digits = int(format_type.split("_", 1)[1])
        return f"{numeric:,.{digits}f}"
    if format_type.startswith("percent_"):
        digits = int(format_type.split("_", 1)[1])
        return f"{numeric:.{digits}%}"
    return value


def _coerce_metadata(metadata: Mapping[str, Any] | pd.DataFrame | None) -> pd.DataFrame:
    if metadata is None:
        return pd.DataFrame(columns=["field", "value"])
    if isinstance(metadata, pd.DataFrame):
        if metadata.empty:
            return pd.DataFrame(columns=["field", "value"])
        if {"field", "value"}.issubset(metadata.columns):
            return metadata[["field", "value"]]
        row = metadata.iloc[0].dropna().to_dict()
    else:
        row = {key: value for key, value in metadata.items() if value is not None}

    return pd.DataFrame({"field": list(row.keys()), "value": list(row.values())})


def _latest_column(columns: list[str], prefix: str) -> str | None:
    matches = [col for col in columns if col.startswith(prefix)]
    return matches[0] if matches else None


def _prepare_metadata_table(metadata: pd.DataFrame, registry_path: Path) -> pd.DataFrame:
    if metadata.empty:
        return metadata
    return pd.DataFrame(
        {
            "Field": [_display_label(field, registry_path) for field in metadata["field"]],
            "Value": [
                _format_value(field, value, registry_path)
                for field, value in zip(metadata["field"], metadata["value"], strict=True)
            ],
        }
    )


def _prepare_snapshot_table(
    df: pd.DataFrame,
    registry_path: Path,
    label_name: str,
) -> pd.DataFrame:
    if df.empty:
        return df
    return pd.DataFrame(
        {
            label_name: [_display_label(metric, registry_path) for metric in df["metric"]],
            "Value": [
                _format_value(metric, value, registry_path)
                for metric, value in zip(df["metric"], df["value"], strict=True)
            ],
        }
    )


def _prepare_cumulative_table(df: pd.DataFrame, registry_path: Path) -> pd.DataFrame:
    if df.empty:
        return df
    return pd.DataFrame(
        {
            _display_label("symbol", registry_path): df["symbol"].astype(str),
            _display_label("cumulative_return", registry_path): [
                _format_value("cumulative_return", value, registry_path)
                for value in df["cumulative_return"]
            ],
        }
    )


def _warn_on_unmapped_fields(fields: set[str], registry_path: Path) -> None:
    unmapped = sorted(field for field in fields if _field_spec(field, registry_path) is None)
    if not unmapped:
        return
    LOGGER.warning(
        "Unmapped report fields detected: %s. Add them to %s.",
        ", ".join(unmapped),
        registry_path,
    )


def _build_indicator_snapshot(indicator_frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    asset = indicator_frame[indicator_frame["symbol"] == symbol].sort_values("date")
    if asset.empty:
        return pd.DataFrame(columns=["metric", "value"])

    latest = asset.iloc[-1]
    columns = list(asset.columns)
    metric_cols = [
        _latest_column(columns, "sma_"),
        _latest_column(columns, "ema_"),
        _latest_column(columns, "rsi_"),
        "macd_line" if "macd_line" in columns else None,
        _latest_column(columns, "volatility_"),
    ]
    metric_cols = [col for col in metric_cols if col is not None]

    return pd.DataFrame([{"metric": col, "value": latest[col]} for col in metric_cols])


def _build_analysis_snapshot(portfolio_summary: dict[str, Any], symbol: str) -> pd.DataFrame:
    capm = portfolio_summary["capm_metrics"]
    sharpe = portfolio_summary["sharpe_ratio"]
    treynor = portfolio_summary["treynor_ratio"]

    snapshot = [
        {"metric": "sharpe_ratio", "value": sharpe.get(symbol, float("nan"))},
        {"metric": "treynor_ratio", "value": treynor.get(symbol, float("nan"))},
    ]

    if symbol in capm.index:
        snapshot.extend(
            [
                {"metric": "beta", "value": capm.loc[symbol, "beta"]},
                {"metric": "alpha", "value": capm.loc[symbol, "alpha"]},
            ]
        )

    snapshot.append(
        {"metric": "equal_weight_variance", "value": portfolio_summary["equal_weight_variance"]}
    )
    return pd.DataFrame(snapshot)


def build_indicator_chart(
    indicator_frame: pd.DataFrame,
    symbol: str,
    lookback: int = 180,
) -> str:
    """Render price and indicator overlays for a single asset."""

    asset = indicator_frame[indicator_frame["symbol"] == symbol].sort_values("date").tail(lookback)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(asset["date"], asset["close"], label="Close", linewidth=2, color="#183153")

    columns = list(asset.columns)
    for prefix, label, color in [
        ("sma_", "SMA", "#2a9d8f"),
        ("ema_", "EMA", "#e76f51"),
    ]:
        col = _latest_column(columns, prefix)
        if col is not None and asset[col].notna().any():
            ax.plot(asset["date"], asset[col], label=label, linewidth=1.5, color=color)

    upper = _latest_column(columns, "bb_upper_")
    lower = _latest_column(columns, "bb_lower_")
    if (
        upper is not None
        and lower is not None
        and asset[upper].notna().any()
        and asset[lower].notna().any()
    ):
        ax.fill_between(asset["date"], asset[lower], asset[upper], alpha=0.15, color="#8ecae6")

    ax.set_title(f"{symbol} Price and Indicators")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(loc="upper left")
    fig.tight_layout()
    return fig_to_base64(fig)


def build_returns_chart(
    portfolio_summary: dict[str, Any],
    asset: str,
    market_symbol: str = "SPY",
) -> str:
    """Render cumulative returns for the asset, market, and equal-weight basket."""

    returns_wide = portfolio_summary["returns_wide"].copy().fillna(0)
    cumulative = (1 + returns_wide).cumprod() - 1
    equal_weight = (1 + returns_wide.mean(axis=1)).cumprod() - 1

    fig, ax = plt.subplots(figsize=(9, 4.5))
    if asset in cumulative.columns:
        ax.plot(cumulative.index, cumulative[asset], label=asset, linewidth=2)
    if market_symbol in cumulative.columns:
        ax.plot(cumulative.index, cumulative[market_symbol], label=market_symbol, linewidth=2)
    ax.plot(equal_weight.index, equal_weight, label="Equal Weight", linewidth=2, linestyle="--")
    ax.set_title("Cumulative Returns")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(loc="upper left")
    fig.tight_layout()
    return fig_to_base64(fig)


def build_capm_chart(
    portfolio_summary: dict[str, Any],
    asset: str,
    market_symbol: str = "SPY",
) -> str:
    """Render CAPM scatter and fitted line for the selected asset."""

    returns_wide = portfolio_summary["returns_wide"]
    capm = portfolio_summary["capm_metrics"]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    if (
        asset in returns_wide.columns
        and market_symbol in returns_wide.columns
        and asset in capm.index
    ):
        joined = pd.concat(
            [returns_wide[asset], returns_wide[market_symbol]],
            axis=1,
            keys=["asset", "market"],
        ).dropna()
        ax.scatter(joined["market"], joined["asset"], alpha=0.6, color="#457b9d")
        beta = float(capm.loc[asset, "beta"])
        alpha = float(capm.loc[asset, "alpha"])
        x_min = float(joined["market"].min())
        x_max = float(joined["market"].max())
        x_values = pd.Series([x_min, x_max])
        ax.plot(x_values, alpha + beta * x_values, color="#d62828", linewidth=2)

    ax.set_title(f"{asset} vs {market_symbol} CAPM")
    ax.set_xlabel(f"{market_symbol} Return")
    ax.set_ylabel(f"{asset} Return")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    return fig_to_base64(fig)


def _build_html_table(df: pd.DataFrame, index: bool = False) -> str:
    if df.empty:
        return '<p class="empty">No data available.</p>'
    return df.to_html(index=index, classes="report-table", border=0)


def render_report(
    symbol: str,
    metadata: Mapping[str, Any] | pd.DataFrame | None,
    indicator_frame: pd.DataFrame,
    portfolio_summary: dict[str, Any],
    output_path: str | Path,
    template_path: str | Path = DEFAULT_TEMPLATE,
    market_symbol: str = "SPY",
    field_registry_path: str | Path = DEFAULT_FIELD_REGISTRY,
) -> Path:
    """Render a self-contained HTML report to disk."""

    template_path = Path(template_path)
    field_registry_path = Path(field_registry_path)
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_path.name)

    metadata_raw = _coerce_metadata(metadata)
    indicator_raw = _build_indicator_snapshot(indicator_frame, symbol)
    analysis_raw = _build_analysis_snapshot(portfolio_summary, symbol)
    cumulative_raw = portfolio_summary["latest_cumulative_returns"].reset_index().rename(
        columns={"index": "symbol"}
    )

    fields_to_check = set(metadata_raw.get("field", pd.Series(dtype=str)).astype(str))
    fields_to_check.update(indicator_raw.get("metric", pd.Series(dtype=str)).astype(str))
    fields_to_check.update(analysis_raw.get("metric", pd.Series(dtype=str)).astype(str))
    if not cumulative_raw.empty:
        fields_to_check.update(["symbol", "cumulative_return"])
    _warn_on_unmapped_fields(fields_to_check, field_registry_path)

    metadata_table = _prepare_metadata_table(metadata_raw, field_registry_path)
    indicator_snapshot = _prepare_snapshot_table(
        indicator_raw,
        field_registry_path,
        label_name="Indicator",
    )
    analysis_snapshot = _prepare_snapshot_table(
        analysis_raw,
        field_registry_path,
        label_name="Metric",
    )
    cumulative_table = _prepare_cumulative_table(
        cumulative_raw,
        field_registry_path,
    )

    context = {
        "symbol": symbol,
        "metadata_table": _build_html_table(metadata_table),
        "indicator_snapshot_table": _build_html_table(indicator_snapshot),
        "analysis_snapshot_table": _build_html_table(analysis_snapshot),
        "latest_cumulative_table": _build_html_table(cumulative_table),
        "indicator_chart": build_indicator_chart(indicator_frame, symbol),
        "returns_chart": build_returns_chart(
            portfolio_summary,
            symbol,
            market_symbol=market_symbol,
        ),
        "capm_chart": build_capm_chart(
            portfolio_summary,
            symbol,
            market_symbol=market_symbol,
        ),
    }

    html = template.render(**context)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


__all__ = [
    "build_capm_chart",
    "build_indicator_chart",
    "build_returns_chart",
    "fig_to_base64",
    "render_report",
]
