# src/ai/create_embeddings.py

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_NEWS_PARQUET = _REPO_ROOT / "data" / "processed" / "processed_news.parquet"

_DEFAULT_SENTENCE_MODEL = "all-MiniLM-L6-v2"

_MODEL: SentenceTransformer | None = None


def load_sentence_transformer() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(_DEFAULT_SENTENCE_MODEL)
    return _MODEL


def generate_embeddings(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    title = df["title"].fillna("").astype(str)
    summary = df["summary"].fillna("").astype(str)
    df["text_for_embedding"] = title + " " + summary
    model = load_sentence_transformer()
    embeddings = model.encode(df["text_for_embedding"].tolist())
    df["embedding"] = embeddings.tolist()
    return df


def find_similar_articles(query_text, filtered_df, top_k=5):
    embeddings = filtered_df["embedding"].tolist()
    model = load_sentence_transformer()
    query_emb = model.encode([query_text])
    scores = cosine_similarity(query_emb, embeddings)[0]
    top_idx = scores.argsort()[-top_k:][::-1]
    return [
        (
            filtered_df.iloc[i]["article_id"],
            scores[i],
        )
        for i in top_idx
    ]



