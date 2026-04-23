# tests/ai/test_embeddings.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

import src.ai.embeddings as emb


@pytest.fixture(autouse=True)
def reset_sentence_model() -> None:
    emb._MODEL = None
    yield
    emb._MODEL = None


@pytest.fixture
def stub_sentence_transformer(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    """Deterministic 4-D embeddings; no HuggingFace download."""
    model = MagicMock()

    def _encode(texts, **kwargs):
        if isinstance(texts, str):
            texts = [texts]
        n = len(texts)
        out = np.zeros((n, 4), dtype=np.float32)
        for i, _ in enumerate(texts):
            out[i, i % 4] = 1.0
        return out

    model.encode.side_effect = _encode
    ctor = MagicMock(return_value=model)
    monkeypatch.setattr(emb, "SentenceTransformer", ctor)
    return model, ctor



def test_load_sentence_transformer_returns_singleton(
    stub_sentence_transformer: tuple[MagicMock, MagicMock],
) -> None:
    _, ctor = stub_sentence_transformer
    m1 = emb.load_sentence_transformer()
    m2 = emb.load_sentence_transformer()
    assert m1 is m2
    assert ctor.call_count == 1


def test_generate_embeddings_adds_text_and_embedding_columns(
    stub_sentence_transformer: tuple[MagicMock, MagicMock],
) -> None:
    df = pd.DataFrame(
        {
            "title": ["Alpha", None],
            "summary": ["one", "two"],
        }
    )
    out = emb.generate_embeddings(df)
    assert "text_for_embedding" in out.columns
    assert "embedding" in out.columns
    assert len(out["embedding"].iloc[0]) == 4
    assert out["text_for_embedding"].iloc[0].startswith("Alpha")


def test_find_similar_articles_scores_and_top_k(monkeypatch: pytest.MonkeyPatch) -> None:
    """Query aligned with first row embedding should rank ``A`` first."""
    emb._MODEL = None
    model = MagicMock()
    emb_mx = np.eye(4, dtype=np.float32)
    df = pd.DataFrame(
        {
            "article_id": ["A", "B", "C", "D"],
            "embedding": [emb_mx[i].tolist() for i in range(4)],
        }
    )

    def encode(texts, **kwargs):
        if isinstance(texts, str):
            texts = [texts]
        if texts == ["match first"]:
            return np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        n = len(texts)
        out = np.zeros((n, 4), dtype=np.float32)
        for i, _ in enumerate(texts):
            out[i, i % 4] = 1.0
        return out

    model.encode.side_effect = encode
    monkeypatch.setattr(emb, "SentenceTransformer", lambda *a, **k: model)

    rows = emb.find_similar_articles("match first", df, top_k=2)
    assert len(rows) == 2
    assert rows[0][0] == "A"
    assert rows[0][1] >= rows[1][1]
