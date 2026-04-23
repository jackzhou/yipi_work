import pandas as pd

import src.ai.data_store as db
from src.ai.embeddings import find_similar_articles as search
    
def find_similar_articles(query_text, top_k=5):
    return search(query_text, db.read(), top_k)

def hybrid_search(query_text, sql_query, top_k=5):
    return search(query_text, db.sql(sql_query), top_k)

def find_similar_articles_by_artical_id(query_text, artical_id, top_k=5):
    return search(query_text, db.read(f"SELECT * FROM articles WHERE article_id = '{artical_id}'"), top_k)
