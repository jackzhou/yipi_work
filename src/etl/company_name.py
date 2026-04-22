# src/etl/company_name.py
"""
Company metadata loading and name reconciliation with processed news CSV.

Expected ``company_metadata.json`` shape: a single JSON object whose keys are
company display names and whose values are objects with (at least)
``founded_year``, ``headquarters``, ``employee_count``, ``industry``,
``is_public`` (boolean), and ``stock_ticker`` (string or null). Loaded with
``orient="index"`` so each key becomes the ``company_name`` column.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[2]
# Default input: ``data/raw/company_metadata.json`` at repo root.
COMPANY_METADATA_JSON_PATH = _REPO_ROOT / "data" / "raw" / "company_metadata.json"
_DEFAULT_PROCESSED_NEWS = _REPO_ROOT / "data" / "processed" / "processed_news.csv"


def _has_symbol(ticker: object) -> bool:
    if pd.isna(ticker):
        return False
    return str(ticker).strip() != ""


def load_company_metadata(path: Path | None = None) -> pd.DataFrame:
    """
    Parse ``data/raw/company_metadata.json`` (or ``path``) into a DataFrame (one row
    per company). The file must be a JSON object mapping company name to field dicts.

    If ``stock_ticker`` is present (non-null, non-blank), ``is_public`` is set to
    ``True`` when it was ``False``. Rows without a ticker keep ``is_public`` unchanged.
    """
    metadata_path = path or COMPANY_METADATA_JSON_PATH
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a JSON object at {metadata_path}, got {type(raw).__name__}")
    records = [{"company_name": name, **fields} for name, fields in raw.items()]
    df = pd.DataFrame.from_records(records)

    has_sym = df["stock_ticker"].map(_has_symbol)
    df.loc[has_sym & ~df["is_public"], "is_public"] = True
    return df


def unmatched_names(
    *,
    processed_csv: Path | None = None,
    metadata_json: Path | None = None,
) -> list[str]:
    """
    Distinct ``company_name`` values from the processed news CSV that are not
    keys in company metadata (exact string match after stripping CSV values).
    """
    meta = load_company_metadata(metadata_json)
    known = set(meta["company_name"].astype(str))

    csv_path = processed_csv or _DEFAULT_PROCESSED_NEWS
    news = pd.read_csv(csv_path)
    if "company_name" not in news.columns:
        raise ValueError(f"Expected a 'company_name' column in {csv_path}")

    names = news["company_name"].dropna().astype(str).str.strip()
    names = names[names != ""]
    print(f"Number of names: {len(names)}")
    print(sorted(set(names)))
    print(sorted(known))
    return sorted(set(names) - known)
