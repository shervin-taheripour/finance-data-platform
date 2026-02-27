"""Parquet raw-zone storage for ticker-partitioned ingestion data."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import pandas as pd

from finance_data_platform.ingestion.yfinance_connector import TickerIngestionBatch

if TYPE_CHECKING:
    from collections.abc import Sequence


EMPTY_TABLE_DDL = {
    "ohlcv": """
        CREATE OR REPLACE TEMP TABLE ohlcv (
            symbol VARCHAR,
            date DATE,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            adj_close DOUBLE,
            volume BIGINT,
            source VARCHAR
        );
    """,
    "dividends": """
        CREATE OR REPLACE TEMP TABLE dividends (
            symbol VARCHAR,
            ex_date DATE,
            amount DOUBLE,
            currency VARCHAR,
            source VARCHAR
        );
    """,
    "splits": """
        CREATE OR REPLACE TEMP TABLE splits (
            symbol VARCHAR,
            ex_date DATE,
            split_ratio DOUBLE,
            source VARCHAR
        );
    """,
    "metadata": """
        CREATE OR REPLACE TEMP TABLE metadata (
            symbol VARCHAR,
            short_name VARCHAR,
            long_name VARCHAR,
            sector VARCHAR,
            industry VARCHAR,
            country VARCHAR,
            currency VARCHAR,
            exchange VARCHAR,
            market_cap BIGINT,
            shares_outstanding BIGINT,
            as_of_date DATE,
            source VARCHAR
        );
    """,
}


def ensure_raw_layout(base_path: str = "data/raw") -> None:
    """Create required raw-zone directories for ticker-partitioned parquet files."""

    base = Path(base_path)
    for subdir in ("ohlcv", "dividends", "splits", "metadata"):
        (base / subdir).mkdir(parents=True, exist_ok=True)


def _records_to_df(records: Sequence[object]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame([record.model_dump() for record in records])


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def write_raw_ticker_batch(batch: TickerIngestionBatch, base_path: str = "data/raw") -> None:
    """Persist a validated ticker batch in ticker-level raw partitions."""

    ensure_raw_layout(base_path)
    symbol = batch.ticker.upper()
    root = Path(base_path)

    ohlcv_df = _records_to_df(batch.ohlcv)
    dividends_df = _records_to_df(batch.dividends)
    splits_df = _records_to_df(batch.splits)

    if batch.metadata is not None:
        metadata_df = pd.DataFrame([batch.metadata.model_dump()])
    else:
        metadata_df = pd.DataFrame()

    _write_parquet(ohlcv_df, root / "ohlcv" / f"{symbol}.parquet")
    _write_parquet(dividends_df, root / "dividends" / f"{symbol}.parquet")
    _write_parquet(splits_df, root / "splits" / f"{symbol}.parquet")
    _write_parquet(metadata_df, root / "metadata" / f"{symbol}.parquet")


def _sql_quote(value: str) -> str:
    return value.replace("'", "''")


def _register_parquet_or_empty(con: duckdb.DuckDBPyConnection, name: str, glob_path: Path) -> None:
    if any(glob_path.parent.glob("*.parquet")):
        quoted_glob = _sql_quote(str(glob_path))
        con.execute(
            f"CREATE OR REPLACE VIEW {name} AS "
            f"SELECT * FROM read_parquet('{quoted_glob}');"
        )
        return

    con.execute(EMPTY_TABLE_DDL[name])


def query_raw(sql: str, base_path: str = "data/raw") -> pd.DataFrame:
    """Query raw parquet files via DuckDB using dataset views."""

    root = Path(base_path)
    with duckdb.connect(database=":memory:") as con:
        _register_parquet_or_empty(con, "ohlcv", root / "ohlcv" / "*.parquet")
        _register_parquet_or_empty(con, "dividends", root / "dividends" / "*.parquet")
        _register_parquet_or_empty(con, "splits", root / "splits" / "*.parquet")
        _register_parquet_or_empty(con, "metadata", root / "metadata" / "*.parquet")
        return con.execute(sql).df()


__all__ = ["ensure_raw_layout", "query_raw", "write_raw_ticker_batch"]
