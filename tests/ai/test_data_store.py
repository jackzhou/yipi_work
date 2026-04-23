# tests/ai/test_data_store.py
"""Tests for ``src.ai.data_store`` using ``data/raw/tech_news.csv``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ai.data_store import duckdb_session, read, sql, write

_REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_TECH_NEWS = _REPO_ROOT / "data" / "raw" / "tech_news.csv"


@pytest.fixture
def raw_sample() -> pd.DataFrame:
    """First rows of raw tech news (same columns as production CSV)."""
    assert RAW_TECH_NEWS.is_file(), f"Missing fixture file: {RAW_TECH_NEWS}"
    return pd.read_csv(RAW_TECH_NEWS, nrows=8)


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_data_store.duckdb"


def test_write_read_roundtrip_from_raw(raw_sample: pd.DataFrame, tmp_db: Path) -> None:
    write(raw_sample, database=tmp_db)
    out = read(database=tmp_db)
    pd.testing.assert_frame_equal(
        raw_sample.reset_index(drop=True),
        out.reset_index(drop=True),
        check_dtype=False,
    )


def test_sql_filter_on_raw_columns(raw_sample: pd.DataFrame, tmp_db: Path) -> None:
    write(raw_sample, database=tmp_db)
    filtered = sql(
        "SELECT article_id, company_name, category FROM articles WHERE company_name = 'Meta AI'",
        database=tmp_db,
    )
    assert len(filtered) >= 1
    assert (filtered["company_name"] == "Meta AI").all()
    assert filtered["article_id"].iloc[0] == "ART0003"


def test_duckdb_session_closes_and_runs_query(tmp_db: Path) -> None:
    df = pd.read_csv(RAW_TECH_NEWS, nrows=3)
    with duckdb_session(tmp_db) as conn:
        conn.register("t", df)
        conn.execute("CREATE OR REPLACE TABLE articles AS SELECT * FROM t")
        got = conn.execute("SELECT COUNT(*) AS n FROM articles").fetchdf()
    assert int(got.loc[0, "n"]) == 3
    again = read(database=tmp_db)
    assert len(again) == 3
