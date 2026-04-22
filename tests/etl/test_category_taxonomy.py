# tests/etl/test_category_taxonomy.py
"""Unit tests for ``src.etl.category_taxonomy``."""

from __future__ import annotations

import pytest
import pandas as pd

from src.etl.category_taxonomy import RAW_TO_TAXONOMY, canonical_category


@pytest.mark.parametrize("raw_key, expected", list(RAW_TO_TAXONOMY.items()))
def test_canonical_category_exact_keys(raw_key: str, expected: str) -> None:
    assert canonical_category(raw_key) == expected


@pytest.mark.parametrize(
    "input_val, expected",
    [
        ("AI & ML", "AI_ML"),
        ("FinTech", "FINTECH"),
        ("  Cloud Computing  ", "CLOUD"),
        ("ENTERPRISE SOFTWARE", "SOFTWARE"),
    ],
)
def test_canonical_category_case_and_whitespace(input_val: str, expected: str) -> None:
    assert canonical_category(input_val) == expected


@pytest.mark.parametrize(
    "value",
    [None, "", "   ", float("nan"), pd.NA],
)
def test_canonical_category_unknown(value) -> None:
    assert canonical_category(value) == "UNKNOWN"


def test_canonical_category_uncategorized() -> None:
    assert canonical_category("Quantum Computing") == "UNCATEGORIZED"


def test_raw_to_taxonomy_keys_are_lowercase() -> None:
    for k in RAW_TO_TAXONOMY:
        assert k == k.lower(), f"key must be lowercase: {k!r}"
