# tests/etl/test_company_name.py
"""Tests for ``src.etl.company_name``."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src.etl.company_name import (
    COMPANY_METADATA_JSON_PATH,
    load_company_metadata,
    unmatched_names,
)


def test_default_path_points_at_raw_metadata() -> None:
    assert COMPANY_METADATA_JSON_PATH.name == "company_metadata.json"
    assert COMPANY_METADATA_JSON_PATH.parts[-3:] == ("data", "raw", "company_metadata.json")


def test_load_company_metadata_parses_repo_json() -> None:
    df = load_company_metadata()
    assert len(df) == 21
    assert "company_name" in df.columns
    assert set(df.columns) >= {
        "company_name",
        "founded_year",
        "headquarters",
        "employee_count",
        "industry",
        "is_public",
        "stock_ticker",
    }
    by = df.set_index("company_name")
    assert bool(by.loc["OpenAI", "is_public"])
    assert not bool(by.loc["Anthropic", "is_public"])


def test_load_company_metadata_ticker_sets_public(tmp_path) -> None:
    p = tmp_path / "meta.json"
    p.write_text(
        json.dumps(
            {
                "ListedCo": {
                    "founded_year": 2000,
                    "headquarters": "X",
                    "employee_count": 1,
                    "industry": "Y",
                    "is_public": False,
                    "stock_ticker": "LIST",
                },
                "PrivateCo": {
                    "founded_year": 2001,
                    "headquarters": "X",
                    "employee_count": 2,
                    "industry": "Y",
                    "is_public": False,
                    "stock_ticker": None,
                },
            }
        ),
        encoding="utf-8",
    )
    df = load_company_metadata(p)
    by = df.set_index("company_name")
    assert bool(by.loc["ListedCo", "is_public"])
    assert not bool(by.loc["PrivateCo", "is_public"])


def test_load_company_metadata_rejects_non_object(tmp_path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ValueError, match="Expected a JSON object"):
        load_company_metadata(p)


def test_unmatched_names_against_temp_files(tmp_path) -> None:
    meta = tmp_path / "company_metadata.json"
    meta.write_text(
        json.dumps(
            {
                "Known Inc": {
                    "founded_year": 2010,
                    "headquarters": "A",
                    "employee_count": 10,
                    "industry": "Z",
                    "is_public": True,
                    "stock_ticker": None,
                }
            }
        ),
        encoding="utf-8",
    )
    csv = tmp_path / "news.csv"
    pd.DataFrame(
        {"company_name": ["Known Inc", "Ghost LLC", "Ghost LLC", "", None]}
    ).to_csv(csv, index=False)
    out = unmatched_names(processed_csv=csv, metadata_json=meta)
    assert out == ["Ghost LLC"]

def test_print_metadata() -> None:

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    unmatched = unmatched_names()

    print(set(unmatched))
    print(len(unmatched))