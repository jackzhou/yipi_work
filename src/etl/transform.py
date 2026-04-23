# src/etl/transform.py
"""ETL transform pipeline: revenue, dates, category, company enrichment, and outputs."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.common.logging_config import configure_logging
from src.etl.category_taxonomy import canonical_category
from src.etl.dateutils import calendar_parts, parse_published_date
from src.etl.enrich import COMPANY_METADATA_JSON_PATH, CompanyEnrich
from src.etl.revenue_utils import dollar_revenue

configure_logging()
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_CSV = _REPO_ROOT / "data" / "processed" / "processed_news.csv"
_DEFAULT_OUTPUT_PARQUET = _REPO_ROOT / "data" / "processed" / "processed_news.parquet"


def _revenue_cell_to_usd(value: object) -> int:
    if pd.isna(value):
        return dollar_revenue(None)
    return dollar_revenue(value)


def _process_publish_data(df: pd.DataFrame) -> pd.DataFrame:
    _published_raw = df["published_date"]
    df = df.copy()
    df["original_published_date"] = _published_raw.map(
        lambda v: "" if pd.isna(v) else str(v).strip()
    )
    df["published_date"] = _published_raw.apply(parse_published_date)

    _parts = df["published_date"].apply(calendar_parts)
    df["year"] = _parts.apply(lambda p: p.year).astype("Int64")
    df["month"] = _parts.apply(lambda p: p.month).astype("Int64")
    df["quarter"] = _parts.apply(lambda p: p.quarter).astype("Int64")

    _ymq = ["year", "month", "quarter"]
    cols_wo_ymq = [c for c in df.columns if c not in _ymq]
    cols_wo_ymq.remove("original_published_date")
    _ins = cols_wo_ymq.index("published_date")
    ordered = cols_wo_ymq[:_ins] + ["original_published_date"] + cols_wo_ymq[_ins:]
    _after_pub = ordered.index("published_date") + 1
    return df[ordered[:_after_pub] + _ymq + ordered[_after_pub:]]


def _persist_to_file(
    df: pd.DataFrame, output_csv_path: Path, output_parquet_path: Path
) -> tuple[str, str]:
    """Write ``df`` to CSV and Parquet; log dtypes from round-trip Parquet read."""
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output_parquet_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_csv_path, index=False)
    df.to_parquet(output_parquet_path)
    df_parquet = pd.read_parquet(output_parquet_path)
    logger.info("df_parquet.dtypes:\n %s", df_parquet.dtypes)
    logger.info("Wrote %s (%s rows)", output_csv_path, len(df))
    logger.info("Wrote %s (%s rows)", output_parquet_path, len(df))
    return str(output_csv_path), str(output_parquet_path)


def run_flow(
    raw_csv_path: Path | str,
    metadata_json_path: Path | str,
    *,
    output_csv_path: Path | str | None = None,
    output_parquet_path: Path | str | None = None,
) -> tuple[Path, Path]:
    """
    Full pipeline from raw news CSV and company metadata JSON to processed outputs.

    1. **Revenue** — USD integer via :mod:`src.etl.revenue_utils`.
    2. **Dates** — normalize ``published_date``, ``original_data``, ``year``/``month``/``quarter``
       (:mod:`src.etl.dateutils`).
    3. **Category** — taxonomy codes via :mod:`src.etl.category_taxonomy`.
    4. **Company** — metadata merge + derived fields via :class:`src.etl.enrich.CompanyEnrich`;
       logs a warning if any unmatched original company names remain.

    Writes ``processed_news.csv`` and ``processed_news.parquet`` under ``data/processed/``
    by default.
    """
    raw_csv_path = Path(raw_csv_path)
    metadata_json_path = Path(metadata_json_path)
    out_csv = Path(output_csv_path) if output_csv_path else _DEFAULT_OUTPUT_CSV
    out_pq = Path(output_parquet_path) if output_parquet_path else _DEFAULT_OUTPUT_PARQUET

    df = pd.read_csv(raw_csv_path)
    if "revenue" not in df.columns:
        raise ValueError(f"Expected a 'revenue' column in {raw_csv_path}")
    if "category" not in df.columns:
        raise ValueError(f"Expected a 'category' column in {raw_csv_path}")
    if "published_date" not in df.columns:
        raise ValueError(f"Expected a 'published_date' column in {raw_csv_path}")
    if "company_name" not in df.columns:
        raise ValueError(f"Expected a 'company_name' column in {raw_csv_path}")

    df = df.copy()
    df["revenue"] = df["revenue"].map(_revenue_cell_to_usd)
    df = _process_publish_data(df)
    df["category"] = df["category"].map(canonical_category)

    ce = CompanyEnrich(metadata_json_path, df)
    df = ce.enrich(df)

    unmatched = ce.unmatched_names()
    if unmatched:
        logger.warning("Unmatched company names (not in metadata): %s", unmatched)

    csv_s, pq_s = _persist_to_file(df, out_csv, out_pq)
    return Path(csv_s), Path(pq_s)


