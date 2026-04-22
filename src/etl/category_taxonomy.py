# src/etl/category_taxonomy.py
"""
Category standardization for tech news.

Raw ``category`` strings map to a small **UPPER_SNAKE** taxonomy (e.g. ``AI_ML``)
so variants like ``AI/ML``, ``AI & ML``, ``Artificial Intelligence``, and
``Machine Learning`` share one code.
"""

from __future__ import annotations

from typing import Any, Final

import pandas as pd

# Normalized raw category (lowercase stripped) -> UPPER_SNAKE taxonomy code.
RAW_TO_TAXONOMY: Final[dict[str, str]] = {
    # AI / ML umbrella
    "ai & ml": "AI_ML",
    "ai/ml": "AI_ML",
    "artificial intelligence": "AI_ML",
    "machine learning": "AI_ML",
    # Data / analytics umbrella
    "analytics": "DATA_ANALYTICS",
    "data analytics": "DATA_ANALYTICS",
    "big data": "DATA_ANALYTICS",
    # Cloud umbrella
    "cloud": "CLOUD",
    "cloud computing": "CLOUD",
    "cloud services": "CLOUD",
    # Security umbrella
    "cybersecurity": "SECURITY",
    "infosec": "SECURITY",
    "security": "SECURITY",
    # Finance umbrella
    "fintech": "FINTECH",
    "finance": "FINTECH",
    "financial technology": "FINTECH",
    # Software umbrella
    "saas": "SOFTWARE",
    "enterprise software": "SOFTWARE",
    "software": "SOFTWARE",
}


def canonical_category(value: Any) -> str:
    """Return UPPER_SNAKE taxonomy code, or ``UNKNOWN`` / ``UNCATEGORIZED``."""
    if pd.isna(value) or str(value).strip() == "":
        return "UNKNOWN"
    key = str(value).strip().lower()
    return RAW_TO_TAXONOMY.get(key, "UNCATEGORIZED")
