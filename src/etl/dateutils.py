# src/etl/dateutils.py
"""Published-date parsing and calendar fields for analysis."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, NamedTuple

from dateutil import parser as date_parser

_MISSING_STRINGS = frozenset({"", "N/A", "NA", "NULL", "NONE", "NAT"})


class PublishedDateParts(NamedTuple):
    """Year, month, and calendar quarter derived from a parsed datetime."""

    year: int | None
    month: int | None
    quarter: int | None


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        import pandas as pd

        if pd.isna(value):
            return True
    except ImportError:
        pass
    if isinstance(value, str):
        t = value.strip()
        if not t:
            return True
        if t.upper() in _MISSING_STRINGS:
            return True
    return False


def _to_naive_utc(dt: datetime) -> datetime:
    """Normalize timezone-aware datetimes to UTC-naive for consistent analysis."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _try_parse(s: str, *, dayfirst: bool | None) -> datetime:
    return date_parser.parse(
        s,
        dayfirst=dayfirst if dayfirst is not None else False,
        fuzzy=False,
    )


def parse_published_date(value: Any) -> datetime | None:
    """
    Parse a ``published_date`` cell into a timezone-naive ``datetime``.

    Handles common variants (ISO-8601, US and EU slash/dash dates, month names,
    timestamps with ``Z``). Missing or invalid values return ``None``.

    Parameters
    ----------
    value
        Raw cell value (string, ``None``, ``NaN``, ``pd.NA``, etc.).

    Returns
    -------
    datetime | None
        Parsed instant as **UTC-naive** ``datetime``, or ``None`` if missing/invalid.
    """
    if _is_missing(value):
        return None

    s = str(value).strip()

    # Prefer explicit strategies for ambiguous numeric dates (US vs EU).
    candidates: list[tuple[str, bool | None]] = [(s, None)]
    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", s):
        candidates = [(s, False), (s, True)]

    for text, dayfirst in candidates:
        try:
            dt = _try_parse(text, dayfirst=dayfirst)
            return _to_naive_utc(dt)
        except (ValueError, OverflowError, TypeError):
            continue

    # Last resort: fuzzy parse (e.g. odd whitespace)
    try:
        dt = date_parser.parse(s, fuzzy=True)
        return _to_naive_utc(dt)
    except (ValueError, OverflowError, TypeError):
        pass

    return None


def calendar_parts(dt: datetime | None) -> PublishedDateParts:
    """
    Extract **year**, **month**, and **calendar quarter** (1–4) for analysis.

    ``dt`` should be the output of :func:`parse_published_date` (naive ``datetime``),
    or ``None`` / missing → all fields ``None``.
    """
    if dt is None:
        return PublishedDateParts(year=None, month=None, quarter=None)
    try:
        import pandas as pd

        if pd.isna(dt):
            return PublishedDateParts(year=None, month=None, quarter=None)
    except ImportError:
        pass
    q = (dt.month - 1) // 3 + 1
    return PublishedDateParts(year=dt.year, month=dt.month, quarter=q)
