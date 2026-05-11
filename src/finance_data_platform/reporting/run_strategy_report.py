"""CLI entrypoint for bucketed strategy reports."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from finance_data_platform.reporting.strategy_report import (
    build_strategy_report_data,
    load_strategy_preset,
    render_strategy_report,
)
from finance_data_platform.storage.parquet_store import read_partitioned_dataset, read_table_dataset
from finance_data_platform.universe_presets import resolve_universe_payload


def load_runtime_config(config_path: str = "config.yaml") -> dict[str, Any]:
    with Path(config_path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _sync_report_assets(output_root: Path) -> None:
    source = Path("assets/report_styles.css")
    if not source.exists():
        return
    target = output_root / "assets" / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main(config_path: str = "config.yaml") -> None:
    config = load_runtime_config(config_path)
    universe = resolve_universe_payload(config.get("universe", {}))
    preset_name = str(universe.get("preset", "default"))
    if not preset_name or preset_name == "default":
        raise RuntimeError("Strategy report requires a non-default universe preset in config.yaml.")

    base_path = str(config["storage"]["base_path"])
    output_root = Path(str(config["reporting"]["output_path"]))
    _sync_report_assets(output_root)

    preset = load_strategy_preset(preset_name)
    metadata = read_partitioned_dataset("metadata", zone="raw", base_path=base_path)
    curated_prices = read_partitioned_dataset("curated_prices", zone="curated", base_path=base_path)
    capm_metrics = read_table_dataset("capm_metrics", zone="curated", base_path=base_path)
    sharpe_ratio = read_table_dataset("sharpe_ratio", zone="curated", base_path=base_path)

    report_data = build_strategy_report_data(
        preset=preset,
        metadata=metadata,
        curated_prices=curated_prices,
        capm_metrics=capm_metrics,
        sharpe_ratio=sharpe_ratio,
    )

    output_path = output_root / f"strategy_{preset.name}.html"
    render_strategy_report(report_data, output_path=output_path)
    print(f"Strategy report complete: preset={preset.name}, output_path={output_path}")


if __name__ == "__main__":
    main()
