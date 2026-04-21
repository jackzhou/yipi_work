# Design and implementation notes

Document architecture, data flow, and modeling choices for this project here.

## Data Quality Handling – Company Metadata

The provided `company_metadata.json` contains inconsistencies between the `is_public` and `stock_ticker` fields. For example, some companies marked as private (`is_public: false`) have non-null stock tickers (e.g., OpenAI with ticker `"OPEN"`).

In this project, such cases are treated as **data quality issues** rather than valid business logic. The fields disagree: either the company is public and has a ticker, or it is private and has no ticker.

### Resolution Strategy

- A **non-null `stock_ticker`** is treated as evidence that the company is publicly traded.
- If `stock_ticker` is present and `is_public` is `false`, then:
  - **`is_public` is set to `true`** (the ticker is kept as given).
- If `is_public` is `false` and there is no ticker, no change is needed.
- These corrections can optionally be flagged for visibility (not required for downstream logic).
