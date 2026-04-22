import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT_PATH = _REPO_ROOT / "data" / "processed" / "data.txt"
_METADATA_PATH = _REPO_ROOT / "data" / "raw" / "company_metadata.json"


def _country_from_headquarters(hq: object) -> str:
    """Derive a display country/region from metadata ``headquarters`` (e.g. ``City, TX`` → US)."""
    if pd.isna(hq) or str(hq).strip() == "":
        return "UNKNOWN"
    text = str(hq).strip()
    parts = [p.strip() for p in text.rsplit(",", 1)]
    if len(parts) < 2:
        return text
    last = parts[-1]
    # US-style "City, ST" (2-letter state / territory codes in this dataset)
    if len(last) == 2 and last.isalpha():
        return "United States"
    return last


def _load_company_country_map(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8") as f:
        meta = json.load(f)
    rows = []
    for company_name, info in meta.items():
        hq = info.get("headquarters")
        rows.append(
            {
                "company_name": company_name,
                "country": _country_from_headquarters(hq),
            }
        )
    return pd.DataFrame(rows)


def classify_date(x):
    if pd.isna(x) or str(x).strip().lower() in ("", "none", "nan"):
        return "MISSING"

    x = str(x).strip()

    if "/" in x:
        return "SLASH_FORMAT"
    if "-" in x:
        return "ISO_OR_DASH_FORMAT"
    if "," in x:
        return "TEXT_FORMAT"

    return "OTHER"


def _mask_same_published_date(series: pd.Series, val: object) -> pd.Series:
    if pd.isna(val):
        return series.isna()
    return series.eq(val)


df = pd.read_csv(_REPO_ROOT / "data" / "raw" / "tech_news.csv")
meta_df = _load_company_country_map(_METADATA_PATH)
df = df.merge(meta_df, on="company_name", how="left")
df["country"] = df["country"].fillna("UNKNOWN")

df["date_pattern"] = df["published_date"].apply(classify_date)

buf = io.StringIO()
with redirect_stdout(buf):
    print("Counts by label:\n")
    print(df["date_pattern"].value_counts().sort_index())
    print()

    for label in sorted(df["date_pattern"].unique()):
        blk = df[df["date_pattern"] == label]
        sub = blk["published_date"]
        print(f"{'=' * 60}")
        print(f"{label} — {len(blk)} rows, {sub.nunique(dropna=False)} distinct values")
        print(f"{'=' * 60}")
        vc = sub.value_counts(dropna=False).sort_index(key=lambda s: s.astype(str))
        for val, cnt in vc.items():
            print(f"  {cnt:4d}  {val!r}")
            part = blk[_mask_same_published_date(blk["published_date"], val)]
            for _, row in part.iterrows():
                print(
                    f"        {row['company_name']!s:32}  {row['country']!s}"
                )
            print()

text = buf.getvalue()
_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
_OUTPUT_PATH.write_text(text, encoding="utf-8")
print(text)
