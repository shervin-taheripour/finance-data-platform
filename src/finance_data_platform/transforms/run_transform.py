"""CLI entrypoint for raw-to-staged transforms."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from finance_data_platform.storage.parquet_store import (
    read_partitioned_dataset,
    write_partitioned_dataset,
)
from finance_data_platform.transforms.indicators import build_indicator_frame


def load_runtime_config(config_path: str = "config.yaml") -> dict[str, Any]:
    with Path(config_path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def main(config_path: str = "config.yaml") -> None:
    config = load_runtime_config(config_path)
    base_path = str(config["storage"]["base_path"])
    raw_prices = read_partitioned_dataset("ohlcv", zone="raw", base_path=base_path)
    if raw_prices.empty:
        raise RuntimeError("No raw OHLCV parquet files found. Run `make ingest` first.")

    indicators = build_indicator_frame(raw_prices, config)
    write_partitioned_dataset(indicators, "indicators", zone="staged", base_path=base_path)

    print(
        "Transform complete: "
        f"symbols={indicators['symbol'].nunique()}, rows={len(indicators)}, "
        f"staged_path={Path(base_path) / 'staged' / 'indicators'}"
    )


if __name__ == "__main__":
    main()
