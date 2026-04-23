# main_etl.py

import logging
from pathlib import Path
import src.common.logging_config  # noqa: F401 — configures logging on import
from src.etl.transform import run_flow

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("hello etl")
    raw_csv_path = Path(__file__).parents[1] / "data" / "raw" / "tech_news.csv"
    metadata_json_path = Path(__file__).parents[1] / "data" / "raw" / "company_metadata.json"
    run_flow(
        raw_csv_path,
        metadata_json_path
    )

if __name__ == "__main__":
    main()
