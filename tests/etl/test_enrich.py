# tests/etl/test_enrich.py
"""Tests for ``src.etl.enrich``."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.etl.enrich import (
    COMPANY_METADATA_JSON_PATH,
    CompanyEnrich,
    enrich,
    load_company_metadata,
)

_DEFAULT_PROCESSED_NEWS = COMPANY_METADATA_JSON_PATH.parents[1] / "processed" / "processed_news.csv"


def unmatched_names(
    *,
    processed_csv: Path | None = None,
    processed_df: pd.DataFrame | None = None,
    metadata_json: Path | None = None,
) -> list[str]:
    """Test helper: thin wrapper around :meth:`CompanyEnrich.unmatched_names`."""
    if processed_df is not None and processed_csv is not None:
        raise ValueError("Pass at most one of processed_df and processed_csv")
    if processed_df is None:
        processed_df = pd.read_csv(processed_csv or _DEFAULT_PROCESSED_NEWS)
    return CompanyEnrich(
        metadata_json or COMPANY_METADATA_JSON_PATH,
        processed_df,
    ).unmatched_names()


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
    news_df = pd.DataFrame(
        {"company_name": ["Known Inc", "Ghost LLC", "Ghost LLC", "", None]}
    )
    ce = CompanyEnrich(meta, news_df)
    assert ce.unmatched_names() == ["Ghost LLC"]


def test_enrich_default_wrapper_smoke() -> None:
    df = pd.read_csv(COMPANY_METADATA_JSON_PATH.parents[1] / "processed" / "processed_news.csv")
    out = enrich(df)
    assert "original_company_name" in out.columns
    assert "company_name" in out.columns
    assert out["company_name"].nunique() == 21
    # Assert every original_company_name and company_name are all the same
    assert all(
        o == c
        for o, c in zip(
            out["original_company_name"].astype(str),
            out["company_name"].astype(str),
        )
    ), "Not all original_company_name and company_name values are the same"


def test_unmatched_names_rejects_both_sources(tmp_path) -> None:
    df = pd.DataFrame({"company_name": ["A"]})
    with pytest.raises(ValueError, match="at most one"):
        unmatched_names(processed_df=df, processed_csv=tmp_path / "x.csv")


def test_enrich_yields_known_company_names(tmp_path) -> None:
    meta = tmp_path / "company_metadata.json"
    company_records = {
        "Alpha Inc": {
            "founded_year": 2000,
            "headquarters": "NY",
            "employee_count": 100,
            "industry": "Tech",
            "is_public": True,
            "stock_ticker": "ALPH",
        },
        "Beta LLC": {
            "founded_year": 2010,
            "headquarters": "SF",
            "employee_count": 50,
            "industry": "Finance",
            "is_public": False,
            "stock_ticker": None,
        },
    }
    meta.write_text(json.dumps(company_records), encoding="utf-8")

    csv = tmp_path / "processed_news.csv"
    df_in = pd.DataFrame(
        {
            "company_name": [
                "Alpha Inc",
                "Beta LLC",
                "Alpha Inc",
                "Beta LLC",
                "Unknown Corp",
                "",
                None,
            ]
        }
    )
    df_in.to_csv(csv, index=False)

    df = pd.read_csv(csv)
    ce = CompanyEnrich(meta, df)
    enriched = ce.enrich(df)

    known = set(company_records.keys())
    for row in enriched.itertuples(index=False):
        val = getattr(row, "company_name")
        if isinstance(val, str) and val.strip() and val != "UNKNOWN":
            assert val in known, f"Unexpected company_name {val!r} in enriched output"


_RAW_TECH_NEWS = COMPANY_METADATA_JSON_PATH.parent / "tech_news.csv"


def test_company_age_non_negative_on_raw_tech_news() -> None:
    """``data/raw/tech_news.csv``: every finite ``company_age`` is >= 0."""
    raw = pd.read_csv(_RAW_TECH_NEWS)
    out = enrich(raw)
    assert "company_age" in out.columns
    ages = out["company_age"].dropna()
    assert len(ages) > 0
    assert (ages >= 0).all()


def test_company_age_expected_for_fixture(tmp_path) -> None:
    """Known ``published_date`` year minus ``founded_year`` after merge."""
    meta = tmp_path / "meta.json"
    meta.write_text(
        json.dumps(
            {
                "FixtureCo": {
                    "founded_year": 2000,
                    "headquarters": "X",
                    "employee_count": 100,
                    "industry": "Tech",
                    "is_public": True,
                    "stock_ticker": None,
                }
            }
        ),
        encoding="utf-8",
    )
    news = pd.DataFrame(
        {
            "company_name": ["FixtureCo", "FixtureCo"],
            "published_date": ["2020-06-01", "2025-01-01"],
        }
    )
    out = CompanyEnrich(meta, news).enrich(news)
    assert out["company_age"].tolist() == [20, 25]
    assert (out["company_age"] >= 0).all()


@pytest.mark.parametrize(
    "employee_count,expected",
    [
        (5_000, "Small"),
        (20_000, "Medium"),
        (50_000, "Large"),
    ],
)
def test_company_size_category_buckets(tmp_path, employee_count: int, expected: str) -> None:
    meta = tmp_path / "meta.json"
    meta.write_text(
        json.dumps(
            {
                "SizeCo": {
                    "founded_year": 2010,
                    "headquarters": "Y",
                    "employee_count": employee_count,
                    "industry": "Tech",
                    "is_public": False,
                    "stock_ticker": None,
                }
            }
        ),
        encoding="utf-8",
    )
    news = pd.DataFrame(
        {"company_name": ["SizeCo"], "published_date": ["2020-01-01"]}
    )
    out = CompanyEnrich(meta, news).enrich(news)
    assert out["company_size_category"].iloc[0] == expected