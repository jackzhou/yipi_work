# src/etl/load.py
"""Data loading for the ETL pipeline."""

from __future__ import annotations
import logging
from pathlib import Path
import pandas as pd
from src.common.logging_config import configure_logging 
from src.etl.revenue_utils import dollar_revenue
from src.etl.category_taxonomy import canonical_category
from src.etl.dateutils import parse_published_date, calendar_parts

configure_logging()
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]



def _revenue_cell_to_usd(value: object) -> int:
    if pd.isna(value):
        return dollar_revenue(None)
    return dollar_revenue(value)


def _process_publish_data(df: pd.DataFrame) -> pd.DataFrame:
    """Preserve raw ``published_date`` as ``original_data``, parse dates, add year/month/quarter, reorder columns."""
    _published_raw = df["published_date"]
    df = df.copy()
    df["original_data"] = _published_raw.map(
        lambda v: "" if pd.isna(v) else str(v).strip()
    )
    df["published_date"] = _published_raw.apply(parse_published_date)

    _parts = df["published_date"].apply(calendar_parts)
    df["year"] = _parts.apply(lambda p: p.year).astype('Int64')
    df["month"] = _parts.apply(lambda p: p.month).astype('Int64')
    df["quarter"] = _parts.apply(lambda p: p.quarter).astype('Int64')

    _ymq = ["year", "month", "quarter"]
    cols_wo_ymq = [c for c in df.columns if c not in _ymq]
    cols_wo_ymq.remove("original_data")
    _ins = cols_wo_ymq.index("published_date")
    ordered = cols_wo_ymq[:_ins] + ["original_data"] + cols_wo_ymq[_ins:]
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


def load_news_data() -> tuple[Path, Path]:
    """
    Read ``home_work/tech_news.csv``, add USD int revenue, write comparison CSV.

    Writes ``data/processed/compare.csv`` with columns ``revenue_original`` (string)
    and ``revenue_usd`` (int).
    """
    input_path = _REPO_ROOT / "data" / "raw" / "tech_news.csv"
    output_csv_path = _REPO_ROOT / "data" / "processed" / "processed_news.csv"
    output_parquet_path = _REPO_ROOT / "data" / "processed" / "processed_news.parquet"

    df = pd.read_csv(input_path)
    # logger.info(df.dtypes)
    if "revenue" not in df.columns:
        raise ValueError("Expected a 'revenue' column in tech_news.csv")
    if "category" not in df.columns:
        raise ValueError("Expected a 'category' column in tech_news.csv")

    df["category"] = df["category"].map(canonical_category)
    df["revenue"] = df.apply(lambda x: _revenue_cell_to_usd(x["revenue"]), axis=1)
    df = _process_publish_data(df)

    csv_s, pq_s = _persist_to_file(df, output_csv_path, output_parquet_path)
    return Path(csv_s), Path(pq_s)


def hello_data() -> None:
    logger.info("hello data")
