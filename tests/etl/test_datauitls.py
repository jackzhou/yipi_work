import pytest
import pandas as pd
from src.etl.dateutils import parse_published_date
from datetime import datetime

# --------------------------------------------------
# 1. ISO / DASH formats (including ISO + Z)
# --------------------------------------------------
@pytest.mark.parametrize("input_val", [
    "2023-05-14",
    "2020-01-10T00:00:00Z",
])
def test_iso_formats(input_val):
    result = parse_published_date(input_val)
    assert isinstance(result, datetime)


# --------------------------------------------------
# 2. DASH ambiguous formats (DD-MM-YYYY or MM-DD-YYYY)
# --------------------------------------------------
@pytest.mark.parametrize("input_val", [
    "01-10-2020",
    "13-06-2023",   # clearly day-first
])
def test_dash_formats(input_val):
    result = parse_published_date(input_val)
    assert isinstance(result, datetime)


# --------------------------------------------------
# 3. SLASH formats (US style mostly)
# --------------------------------------------------
@pytest.mark.parametrize("input_val", [
    "01/08/2021",
    "12/23/2022",
])
def test_slash_formats(input_val):
    result = parse_published_date(input_val)
    assert isinstance(result, datetime)


# --------------------------------------------------
# 4. TEXT formats (Month name)
# --------------------------------------------------
@pytest.mark.parametrize("input_val", [
    "April 09, 2021",
    "December 11, 2023",
])
def test_text_formats(input_val):
    result = parse_published_date(input_val)
    assert isinstance(result, datetime)


# --------------------------------------------------
# 5. OTHER (short text format like "01 Feb 2021")
# --------------------------------------------------
@pytest.mark.parametrize("input_val", [
    "01 Feb 2021",
    "13 Aug 2021",
])
def test_other_text_formats(input_val):
    result = parse_published_date(input_val)
    assert isinstance(result, datetime)


# --------------------------------------------------
# 6. Missing / null values
# --------------------------------------------------
@pytest.mark.parametrize("input_val", [
    None,
    "",
    "   ",
])
def test_missing_values(input_val):
    result = parse_published_date(input_val)
    assert result is None


# --------------------------------------------------
# 7. Malformed / invalid values
# --------------------------------------------------
@pytest.mark.parametrize("input_val", [
    "invalid-date",
    "2023-99-99",
])
def test_invalid_values(input_val):
    result = parse_published_date(input_val)
    assert result is None


# --------------------------------------------------
# 8. Consistency test on real dataset
# --------------------------------------------------
def test_dataset_parsing():
    df = pd.read_csv("data/raw/tech_news.csv")

    parsed = df["published_date"].apply(parse_published_date)

    # No crashes
    assert len(parsed) == len(df)

    # Most values should parse successfully
    failure_rate = parsed.isna().mean()

    print(f"\nParse failure rate: {failure_rate:.2%}")

    assert failure_rate < 0.05   # allow small tolerance