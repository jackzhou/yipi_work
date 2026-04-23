# Design and implementation notes

Document architecture, data flow, and modeling choices for this project here.

## Data Quality Handling – Company Metadata

The provided `company_metadata.json` contains inconsistencies between the `is_public` and `stock_ticker` fields. For example, some companies marked as private (`is_public: false`) have non-null stock tickers (e.g., OpenAI with ticker `"OPEN"`).

### Resolution Strategy

- A **non-null `stock_ticker`** is treated as evidence that the company is publicly traded.
- If `stock_ticker` is present and `is_public` is `false`, then:
  - `**is_public` is set to `true**` (the ticker is kept as given).
- If `is_public` is `false` and there is no ticker, no change is needed.
- These corrections can optionally be flagged for visibility (not required for downstream logic).

### On Category and Industry Joins

No join is ever performed between `category` (from news) and `industry` (from company metadata) during ETL; these fields are treated as entirely independent.

- `category` is standardized for news articles using a custom taxonomy (`src/etl/category_taxonomy.py`).
- `industry` reflects a company's sector, coming directly from metadata JSON.

There’s no mapping like `df["category"] == meta["industry"]`; this avoids misleading overlaps, since news topics and company sectors often differ and aligning them would add little value.

Any analysis of category/industry overlap is left for downstream, exploratory work only 

**Summary:**  
No join or cross-field mapping is performed between `category` and `industry` in ETL; each remains distinct in the output data.

### Hybrid Vector Search and Metadata Filtering with DuckDB

In this project, **semantic search** over news articles is implemented using a hybrid approach that separates **metadata filtering** and **vector similarity** ranking, instead of relying on an integrated vector database.

DuckDB handles structured filtering, allowing precise selection and extraction of news articles based on metadata columns, such as company, category, published date, etc., using familiar SQL expressions (e.g., `SELECT * FROM articles WHERE company_name = 'Meta AI' AND category = 'LLM'`). This enables efficient database-level narrowing of the candidate set before any semantic computation.

Python handles vector similarity: after retrieving a filtered set of articles from DuckDB (as a DataFrame), the application encodes the user's query using a sentence transformer, calculates cosine similarity with the `embedding` field for each article, and ranks results according to semantic relevance. This two-stage "hybrid search" allows the combination of fast, flexible metadata filtering and state-of-the-art text similarity without the need for a dedicated vector database or plugin.

**Summary:**  
Metadata narrowing (using SQL in DuckDB) and vector search (using Python’s machine learning stack) are composed:  
1. SQL extracts a relevant article subset.  
2. Embedding-based similarity ranks this subset by semantic match to the query.