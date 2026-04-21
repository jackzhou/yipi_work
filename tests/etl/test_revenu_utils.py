# tests/etl/test_revenu_utils.py
"""Test revenue utilities."""

import pytest
import pandas as pd
from src.etl.revenue_utils import dollar_revenue


# ----------------------------
# 1. Deterministic test cases
# ----------------------------
@pytest.mark.parametrize("input_val, expected", [
    ("$5M", 5_000_000),
    ("$5.2B", 5_200_000_000),
    ("5.2 billion", 5_200_000_000),
    ("€1M", 1_100_000),
    ("£1M", 1_270_000),
    ("¥150000000", 1_000_000),
    ("$10M - $20M", 15_000_000),
    ("5M-10M", 7_500_000),
    ("Not disclosed", 0),
    ("N/A", 0),
    (None, 0),
    ("around $20 million", 20_000_000),
])
def test_dollar_revenue_basic(input_val, expected):
    assert dollar_revenue(input_val) == expected


# ----------------------------
# 2. Pattern robustness test
# ----------------------------
def test_revenue_patterns_from_dataset():
    df = pd.read_csv("data/raw/tech_news.csv")

    # Apply function
    results = df["revenue"].apply(dollar_revenue)

    # Basic sanity checks
    assert len(results) == len(df)

    # No crashes / None values
    assert results.isnull().sum() == 0

    # All values should be integers
    assert results.apply(lambda x: isinstance(x, int)).all()

    # Values should be non-negative
    assert (results >= 0).all()


# ----------------------------
# 3. Distribution / stats test
# ----------------------------
def test_revenue_distribution_stats():
    df = pd.read_csv("data/raw/tech_news.csv")

    results = df["revenue"].apply(dollar_revenue)

    # Basic distribution checks (not strict, just sanity)
    assert results.max() > 1_000_000   # at least some large companies
    assert results.mean() >= 0

    # Optional: print stats (visible in pytest -v)
    print("\n--- Revenue Stats ---")
    print(f"min: {results.min()}")
    print(f"max: {results.max()}")
    print(f"mean: {int(results.mean())}")