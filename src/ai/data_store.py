# src/ai/data_store.py

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DUCKDB_PATH = _REPO_ROOT / "data" /"tech_news.duckdb"
TABLE_NAME = "articles"


@contextmanager
def duckdb_session(database: str | Path | None = None) -> Iterator[duckdb.DuckDBPyConnection]:
    """
    Open a DuckDB connection and **close** it when the ``with`` block ends.

    ``database`` defaults to ``articles_embeddings.duckdb`` at the repo root.
    """
    path = database if database is not None else DEFAULT_DUCKDB_PATH
    conn = duckdb.connect(str(path))
    try:
        yield conn
    finally:
        conn.close()


def write(df: pd.DataFrame, table_name: str = TABLE_NAME, *, database: str | Path | None = None) -> None:
    """Replace ``table_name`` with the contents of ``df``."""
    with duckdb_session(database) as conn:
        conn.register("_df_write", df)
        conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM _df_write")


def read(table_name: str = TABLE_NAME, *, database: str | Path | None = None) -> pd.DataFrame:
    """Read all rows from ``table_name``."""
    with duckdb_session(database) as conn:
        return conn.execute(f"SELECT * FROM {table_name}").fetchdf()


def sql(query: str, *, database: str | Path | None = None) -> pd.DataFrame:
    """Run a SQL query and return the result as a DataFrame."""
    with duckdb_session(database) as conn:
        return conn.execute(query).fetchdf()
