"""Unified entry point: ETL pipeline and AI enrichment pipeline."""

import argparse
import logging
from pathlib import Path

import src.common.logging_config  # noqa: F401 — configures logging on import
import pandas as pd

import src.ai.data_store as db
from src.ai.embeddings import generate_embeddings
from src.ai.similarity_search import export_with_top_similar_articles
from src.etl.transform import run_flow

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]


def run_etl() -> None:
    logger.info("Starting ETL pipeline")
    raw_csv_path = ROOT / "data" / "raw" / "tech_news.csv"
    metadata_json_path = ROOT / "data" / "raw" / "company_metadata.json"
    run_flow(raw_csv_path, metadata_json_path)
    logger.info("ETL pipeline completed")



def run_ai() -> None:
    logger.info("loading cleaned data")
    db.load_cleaned_data()
    logger.info("cleaned data loaded")
    df = db.read()
    logger.info("data loaded: %s", df.shape)
    df_with_embeddings = generate_embeddings(df)
    logger.info("embeddings generated: %s", df.shape)

    embedding_table = "articles_embeddings"
    db.write(df_with_embeddings, table_name=embedding_table)
    logger.info("embeddings written to table %s", embedding_table)
    export_final_file()

def export_final_file() -> None:
    category_list = "('AI_ML', 'AI', 'ML', 'Artificial Intelligence', 'Machine Learning')"
    query = f"""
        SELECT
            article_id,
            title,
            company_name,
            published_date,
            category,
            revenue as revenue_usd,
            summary,
            url,
            industry,
            founded_year,
            headquarters,
            employee_count,
            is_public,
            stock_ticker,
            company_age,
            company_size_category,
            embedding,

        FROM articles_embeddings
        WHERE
            (
                category IN {category_list}
                OR industry IN {category_list}
            )
            AND year BETWEEN 2022 AND 2024
            AND revenue >= 50000000

    """

    export_with_top_similar_articles(query, ROOT / "output" / "ai_articles_enriched.csv")



def main() -> None:
    parser = argparse.ArgumentParser(description="Run ETL, AI pipeline, or both.")
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=("etl", "ai", "all"),
        help="etl: transform only; ai: embeddings + export; all: etl then ai (default)",
    )
    args = parser.parse_args()

    if args.mode in ("etl", "all"):
        run_etl()
    if args.mode in ("ai", "all"):
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        pd.set_option("display.max_colwidth", None)
        run_ai()


if __name__ == "__main__":
    main()
