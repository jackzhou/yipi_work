"""Data loading for the ETL pipeline."""

import logging

import src.common.logging_config  # noqa: F401 — configures logging on import

logger = logging.getLogger(__name__)


def hello_data() -> None:
    logger.info("hello data")