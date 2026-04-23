#!/usr/bin/env bash
rm -rf data/processed/processed_news.csv
rm -rf data/processed/processed_news.parquet
rm -rf data/db/tech_news.duckdb
source .venv/bin/activate

# python src/main_etl.py
# python main_ai.py