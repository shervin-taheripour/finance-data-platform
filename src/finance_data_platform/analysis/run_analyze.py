"""CLI entrypoint for staged-to-curated analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from finance_data_platform.analysis.portfolio import build_portfolio_summary
from finance_data_platform.storage.parquet_store import (
    read_partitioned_dataset,
    write_partitioned_dataset,
    write_table_dataset,
)
from finance_data_platform.transforms.enrichment import build_curated_views


def load_runtime_config(config_path: str = "config.yaml") -> dict[str, Any]:
    with Path(config_path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def main(config_path: str = "config.yaml") -> None:
    config = load_runtime_config(config_path)
    base_path = str(config["storage"]["base_path"])
    benchmark_symbol = str(config["universe"]["benchmark"]).upper()
    correlation_window = int(config["transforms"]["enrichment"]["correlation_window"])
    risk_free_rate = float(config["analysis"].get("risk_free_rate", 0.0))

    indicators = read_partitioned_dataset("indicators", zone="staged", base_path=base_path)
    if indicators.empty:
        raise RuntimeError("No staged indicator parquet files found. Run `make transform` first.")

    curated = build_curated_views(
        indicators,
        benchmark_symbol=benchmark_symbol,
        correlation_window=correlation_window,
    )
    summary = build_portfolio_summary(
        curated["returns"],
        market_symbol=benchmark_symbol,
        risk_free_rate=risk_free_rate,
    )

    write_partitioned_dataset(
        curated["curated_prices"],
        "curated_prices",
        zone="curated",
        base_path=base_path,
    )
    write_partitioned_dataset(
        curated["returns"],
        "returns",
        zone="curated",
        base_path=base_path,
    )
    write_partitioned_dataset(
        curated["correlations"],
        "correlations",
        zone="curated",
        base_path=base_path,
    )
    write_table_dataset(
        summary["capm_metrics"].reset_index(),
        "capm_metrics",
        zone="curated",
        base_path=base_path,
    )
    write_table_dataset(
        summary["sharpe_ratio"].rename_axis("symbol").reset_index(),
        "sharpe_ratio",
        zone="curated",
        base_path=base_path,
    )
    write_table_dataset(
        summary["treynor_ratio"].rename_axis("symbol").reset_index(),
        "treynor_ratio",
        zone="curated",
        base_path=base_path,
    )
    write_table_dataset(
        summary["latest_cumulative_returns"].rename_axis("symbol").reset_index(),
        "latest_cumulative_returns",
        zone="curated",
        base_path=base_path,
    )
    write_table_dataset(
        pd.DataFrame([{"equal_weight_variance": float(summary["equal_weight_variance"])}]),
        "portfolio_summary",
        zone="curated",
        base_path=base_path,
    )

    print(
        "Analysis complete: "
        f"returns_rows={len(curated['returns'])}, capm_assets={len(summary['capm_metrics'])}, "
        f"curated_path={Path(base_path) / 'curated'}"
    )


if __name__ == "__main__":
    main()
