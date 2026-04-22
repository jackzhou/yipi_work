import pandas as pd
from src.etl.company_name import load_company_metadata, unmatched_names

sf = pd.read_json("data/raw/company_metadata.json").T
# print(f"Columns: {list(sf.index)}")
print(sf)
# print(sf.dtypes)
# print(sf.head())
# print(sf.tail())
# print(sf.info())
# print(sf.describe())
# print(sf.shape)
# print(sf.columns)
# print(sf.dtypes)
