"""CLI entrypoint for HTML report generation from curated outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from finance_data_platform.reporting.generator import render_report
from finance_data_platform.storage.parquet_store import read_partitioned_dataset, read_table_dataset


def load_runtime_config(config_path: str = "config.yaml") -> dict[str, Any]:
    with Path(config_path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _load_portfolio_summary(base_path: str) -> dict[str, object]:
    returns = read_partitioned_dataset("returns", zone="curated", base_path=base_path)
    capm_metrics = read_table_dataset("capm_metrics", zone="curated", base_path=base_path)
    sharpe_ratio = read_table_dataset("sharpe_ratio", zone="curated", base_path=base_path)
    treynor_ratio = read_table_dataset("treynor_ratio", zone="curated", base_path=base_path)
    latest_cumulative = read_table_dataset(
        "latest_cumulative_returns",
        zone="curated",
        base_path=base_path,
    )
    summary_metrics = read_table_dataset("portfolio_summary", zone="curated", base_path=base_path)

    if returns.empty:
        raise RuntimeError("No curated return parquet files found. Run `make analyze` first.")

    returns_wide = returns.pivot(
        index="date",
        columns="symbol",
        values="return_1d",
    ).sort_index()
    capm_frame = capm_metrics.set_index("symbol") if not capm_metrics.empty else pd.DataFrame()

    return {
        "returns_wide": returns_wide,
        "capm_metrics": capm_frame,
        "sharpe_ratio": (
            sharpe_ratio.set_index("symbol")["sharpe_ratio"]
            if not sharpe_ratio.empty
            else pd.Series(dtype=float)
        ),
        "treynor_ratio": (
            treynor_ratio.set_index("symbol")["treynor_ratio"]
            if not treynor_ratio.empty
            else pd.Series(dtype=float)
        ),
        "equal_weight_variance": (
            float(summary_metrics.loc[0, "equal_weight_variance"])
            if not summary_metrics.empty
            else 0.0
        ),
        "latest_cumulative_returns": (
            latest_cumulative.set_index("symbol")
            if not latest_cumulative.empty
            else pd.DataFrame(columns=["cumulative_return"])
        ),
    }


def main(config_path: str = "config.yaml") -> None:
    config = load_runtime_config(config_path)
    base_path = str(config["storage"]["base_path"])
    output_root = Path(str(config["reporting"]["output_path"]))
    market_symbol = str(config["universe"]["benchmark"]).upper()
    symbols = [str(symbol).upper() for symbol in config["universe"]["tickers"]]

    indicators = read_partitioned_dataset("indicators", zone="staged", base_path=base_path)
    metadata = read_partitioned_dataset("metadata", zone="raw", base_path=base_path)
    portfolio_summary = _load_portfolio_summary(base_path)

    generated: list[Path] = []
    for symbol in symbols:
        symbol_metadata = metadata[metadata["symbol"] == symbol] if not metadata.empty else None
        report_path = output_root / f"{symbol.lower()}_report.html"
        generated.append(
            render_report(
                symbol=symbol,
                metadata=symbol_metadata,
                indicator_frame=indicators,
                portfolio_summary=portfolio_summary,
                output_path=report_path,
                template_path=config["reporting"]["template"],
                market_symbol=market_symbol,
                field_registry_path=config["reporting"].get(
                    "field_registry",
                    "config/report_fields.yaml",
                ),
            )
        )

    print(f"Report complete: reports={len(generated)}, output_path={output_root}")


if __name__ == "__main__":
    main()
