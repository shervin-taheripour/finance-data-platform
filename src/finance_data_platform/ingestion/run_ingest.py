"""CLI entrypoint for raw-zone ingestion."""

from __future__ import annotations

from pathlib import Path

from finance_data_platform.ingestion.yfinance_connector import fetch_universe, load_ingestion_config
from finance_data_platform.storage.parquet_store import write_raw_ticker_batch


def main() -> None:
    cfg = load_ingestion_config("config.yaml")
    raw_base = Path(cfg.storage.base_path) / "raw"

    batches = fetch_universe(cfg)
    for batch in batches:
        write_raw_ticker_batch(batch, base_path=str(raw_base))

    total_ohlcv = sum(len(batch.ohlcv) for batch in batches)
    print(
        f"Ingestion complete: tickers={len(batches)}, ohlcv_rows={total_ohlcv}, "
        f"raw_path={raw_base}"
    )


if __name__ == "__main__":
    main()
