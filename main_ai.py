"""Entry point for the AI enrichment pipeline."""

import logging

import src.common.logging_config  # noqa: F401 — configures logging on import

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("hello ai")


if __name__ == "__main__":
    main()
