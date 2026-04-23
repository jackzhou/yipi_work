# src/etl/enrich.py
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
from typing import ClassVar, Final

import pandas as pd
from rapidfuzz import fuzz, process

_REPO_ROOT = Path(__file__).resolve().parents[2]
COMPANY_METADATA_JSON_PATH: Final[Path] = _REPO_ROOT / "data" / "raw" / "company_metadata.json"
_DEFAULT_PROCESSED_NEWS: Final[Path] = _REPO_ROOT / "data" / "processed" / "processed_news.csv"


def _has_symbol(ticker: object) -> bool:
    if ticker is None or pd.isna(ticker):
        return False
    return str(ticker).strip() != ""


def _nonblank_series(s: pd.Series) -> pd.Series:
    return s.notna() & (s.astype(str).str.strip() != "")


def _size_category(count: object) -> str:
    if pd.isna(count):
        return "Unknown"
    try:
        cnt = int(count)
    except (TypeError, ValueError):
        return "Unknown"
    if cnt < 10_000:
        return "Small"
    if cnt <= 30_000:
        return "Medium"
    return "Large"


def _add_derived_company_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``company_age`` and ``company_size_category`` from merged metadata + article dates."""
    out = df.copy()
    if "founded_year" in out.columns and "published_date" in out.columns:
        pub_year = pd.to_datetime(out["published_date"], errors="coerce").dt.year.astype(
            "Int64"
        )
        founded = pd.to_numeric(out["founded_year"], errors="coerce").astype("Int64")
        delta = pub_year - founded
        # Drop impossible chronology (article year before founded_year)
        out["company_age"] = delta.where(delta.isna() | (delta >= 0), pd.NA)
    else:
        out["company_age"] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    if "employee_count" in out.columns:
        out["company_size_category"] = out["employee_count"].map(_size_category)
    else:
        out["company_size_category"] = "Unknown"
    return out


class CompanyEnrich:
    """Load company metadata, canonicalize names, merge onto news rows, list unmatched processed names."""

    COMPANY_ALIAS: ClassVar[dict[str, str]] = {
        "aws": "Amazon Web Services",
        "amazon aws": "Amazon Web Services",
        "amazon web service": "Amazon Web Services",
        "gcp": "Google DeepMind",
        "google": "Google DeepMind",
        "google ai": "Google DeepMind",
        "azure": "Microsoft",
        "microsoft azure": "Microsoft",
        "open ai": "OpenAI",
        "openai inc": "OpenAI",
        "meta": "Meta AI",
        "facebook ai": "Meta AI",
        "nvidia corp": "NVIDIA",
        "databricks inc": "Databricks",
        "snowflake inc": "Snowflake",
        "amazon": "Amazon Web Services",
    }

    def __init__(self, metadata_json_path: Path, processed_df: pd.DataFrame) -> None:
        self.metadata_json_path = Path(metadata_json_path)
        self.processed_df = processed_df
        self._metadata: pd.DataFrame | None = None
        self._company_names: set[str] | None = None

    @staticmethod
    def load_metadata_file(metadata_path: Path) -> pd.DataFrame:
        """Read metadata JSON from ``metadata_path`` and return a normalized DataFrame."""
        raw = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(
                f"Expected a JSON object at {metadata_path}, got {type(raw).__name__}"
            )
        records = [{"company_name": name, **fields} for name, fields in raw.items()]
        df = pd.DataFrame.from_records(records)
        has_sym = df["stock_ticker"].map(_has_symbol)
        df.loc[has_sym & ~df["is_public"], "is_public"] = True
        return df

    def load_metadata(self) -> pd.DataFrame:
        """Load (and cache) metadata from ``self.metadata_json_path``."""
        if self._metadata is None:
            self._metadata = self.load_metadata_file(self.metadata_json_path)
            self._company_names = {
                s.strip() for s in self._metadata["company_name"].astype(str)
            }
        return self._metadata

    @property
    def company_names(self) -> set[str]:
        self.load_metadata()
        assert self._company_names is not None
        return self._company_names

    def canonical_company_name(self, name: object) -> str:
        """Return canonical company name from metadata keys, aliases, or fuzzy match; else ``UNKNOWN``."""
        if pd.isna(name):
            return "UNKNOWN"
        s = str(name).strip()
        if s == "":
            return "UNKNOWN"

        names = self.company_names
        if s in names:
            return s

        key = s.lower()
        alias = self.COMPANY_ALIAS
        if key in alias:
            return alias[key]
        for a, canonical in alias.items():
            if a in key:
                return canonical

        match = process.extractOne(key, alias.keys(), scorer=fuzz.ratio)
        if match is None:
            return "UNKNOWN"
        best_alias, score, _idx = match
        return alias[best_alias] if score > 80 else "UNKNOWN"

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        meta = self.load_metadata()
        out = df.copy()
        out["canonical_company_name"] = out["company_name"].map(self.canonical_company_name)
        out = (
            out.merge(meta, left_on="canonical_company_name", right_on="company_name", how="left")
            .drop(columns=["company_name_y"])
            .rename(columns={"company_name_x": "original_company_name"})
            .rename(columns={"canonical_company_name": "company_name"})
        )
        return _add_derived_company_fields(out)

    def unmatched_names(self) -> list[str]:
        """
        Run :meth:`enrich` on ``processed_df`` and return sorted distinct
        ``original_company_name`` values where the original cell is non-empty but
        the canonical ``company_name`` is not a key in metadata (not in
        :attr:`company_names`), e.g. ``UNKNOWN`` or any string absent from
        ``company_metadata.json``.
        """
        news = self.processed_df
        if "company_name" not in news.columns:
            raise ValueError("Expected a 'company_name' column in processed_df")

        enriched = self.enrich(news.copy())
        orig = enriched["original_company_name"]
        has_orig = _nonblank_series(orig)
        names = self.company_names
        canon = enriched["company_name"]
        in_meta = canon.astype(str).str.strip().isin(names)
        no_meta = ~in_meta
        out = enriched.loc[has_orig & no_meta, "original_company_name"].astype(str).str.strip()
        return sorted(set(out))


def load_company_metadata(path: Path | None = None) -> pd.DataFrame:
    """Load metadata JSON; default path is ``COMPANY_METADATA_JSON_PATH``."""
    return CompanyEnrich.load_metadata_file(path or COMPANY_METADATA_JSON_PATH)


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich ``df`` using default repo metadata."""
    return CompanyEnrich(COMPANY_METADATA_JSON_PATH, df).enrich(df)
