# yipit_work

This project (yipit_work) implements an end-to-end ETL and AI enrichment pipeline.

For a full code walkthrough (ETL → embeddings → export), see **[PROJECT_WALKTHROUGH.md](PROJECT_WALKTHROUGH.md)**.

## Exported CSV file location

**`output/ai_articles_enriched.csv`** (relative to the repository root)

## Prerequisites

- Python 3.11

## Install

- Create a virtual environment with Python 3.11; see **create_venv.sh**
- Run:

  ```shellscript
  pip install -r requirements.txt
  ```

  See **install_deps.sh**

## Run tests

- `pytest`

## Run workflow

- Start the pipeline: `./run_all.sh`
- Python entry point: [src/pipeline.py](src/pipeline.py)
- Usage help: `PYTHONPATH=$PYTHONPATH:$(pwd) python src/pipeline.py -h`

## Code usage and testing

Each module (`<file>.py`) is accompanied by a corresponding test file (`test_<file>.py`), which serves both to validate functionality and to document the intended usage and behavior.

## Query functions

- Functions to execute SQL queries on DuckDB:

```python
def read(table_name: str = TABLE_NAME, *, database: str | Path | None = None) -> pd.DataFrame:
    """Read all rows from ``table_name``."""
    with duckdb_session(database) as conn:
        return conn.execute(f"SELECT * FROM {table_name}").fetchdf()


def sql(query: str, *, database: str | Path | None = None) -> pd.DataFrame:
    """Run a SQL query and return the result as a DataFrame."""
    with duckdb_session(database) as conn:
        return conn.execute(query).fetchdf()
```

- Function to perform vector similarity search:

```python
def find_similar_articles(query_text, filtered_df, top_k=5):
    ...
```

- Export function to CSV with embeddings:

```python
def export_with_top_similar_articles(sql_query, output_path):
    ...
```
