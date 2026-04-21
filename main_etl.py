# main_etl.py
"""Entry point for the ETL pipeline."""

import logging

import src.common.logging_config  # noqa: F401 — configures logging on import
from src.etl.load import hello_data

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("hello etl")
    hello_data()


if __name__ == "__main__":
    main()
