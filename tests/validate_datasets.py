"""
Validate raw tech news CSV + company metadata JSON for parseability and joins.

Run from repo root:  python tests/validate_datasets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CSV = _REPO_ROOT / "data" / "raw" / "tech_news.csv"
_JSON = _REPO_ROOT / "data" / "raw" / "company_metadata.json"


def main() -> int:
    sys.path.insert(0, str(_REPO_ROOT))
    from src.etl.dateutils import parse_published_date
    from src.etl.revenue_utils import dollar_revenue

    issues: list[str] = []

    with _JSON.open(encoding="utf-8") as f:
        meta = json.load(f)
    company_keys = set(meta.keys())

    df = pd.read_csv(_CSV)

    # --- company_name in metadata ---
    for i, row in df.iterrows():
        name = row.get("company_name")
        if pd.isna(name) or str(name).strip() == "":
            issues.append(f"row {i + 2}: empty company_name")
            continue
        if name not in company_keys:
            issues.append(f"row {i + 2}: company_name {name!r} not in company_metadata.json")

    # --- published_date: non-empty must parse ---
    def _cell_missing(v: object) -> bool:
        if pd.isna(v):
            return True
        return str(v).strip().lower() in ("", "none", "nan")

    for i, row in df.iterrows():
        raw = row.get("published_date")
        if _cell_missing(raw):
            continue
        dt = parse_published_date(raw)
        if dt is None:
            issues.append(f"row {i + 2}: published_date not parseable: {raw!r}")

    # --- revenue: must not raise ---
    for i, row in df.iterrows():
        raw = row.get("revenue")
        try:
            if pd.isna(raw):
                dollar_revenue(None)
            else:
                dollar_revenue(raw)
        except Exception as e:
            issues.append(f"row {i + 2}: revenue error for {raw!r}: {e}")

    # --- JSON structure sanity ---
    required = ("headquarters", "founded_year", "industry", "is_public")
    for company, info in meta.items():
        if not isinstance(info, dict):
            issues.append(f"metadata[{company!r}]: expected object, got {type(info)}")
            continue
        for key in required:
            if key not in info:
                issues.append(f"metadata[{company!r}]: missing key {key!r}")

    print("Validation: data/raw/tech_news.csv + data/raw/company_metadata.json")
    print(f"  Rows in CSV: {len(df)}")
    print(f"  Companies in JSON: {len(meta)}")
    print()
    if not issues:
        print("OK — no issues found (company keys, dates parse, revenue parse, JSON shape).")
        return 0

    print(f"FOUND {len(issues)} issue(s):\n")
    for line in issues[:200]:
        print(line)
    if len(issues) > 200:
        print(f"... and {len(issues) - 200} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
