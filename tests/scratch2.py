import pandas as pd
from src.etl.enrich import enrich, load_company_metadata

df = pd.read_csv("data/processed/processed_news.csv")
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)
df = enrich(df).drop(columns=["summary", "title"])
print(df[["company_name", "original_company_name", "company_age", "company_size_category", "employee_count", 'founded_year', 'published_date', 'year']])
# Print the first row where "company_name" and "original_company_name" are not the same
diff_rows = df[df["company_name"] != df["original_company_name"]]
if not diff_rows.empty:
    print(diff_rows.iloc[[0]][["company_name", "original_company_name"]])
else:
    print("No differing rows found.")

# Print all rows where "company_name" and "original_company_name" are different
print(diff_rows[["company_name", "original_company_name"]])


# print(df.tail())
# print(df.info())
# print(df.describe())
# print(df.shape)
# print(df.columns)
# print(df.dtypes)

# print(df.head())
# print(df.tail())
# print(df.info())
# print(df.describe())
# print(df.shape)
# print(df.columns)
# print(df.dtypes)
# print(sf.dtypes)
# print(sf.head())
# print(sf.tail())
# print(sf.info())
# print(sf.describe())
# print(sf.shape)
# print(sf.columns)
# print(sf.dtypes)
