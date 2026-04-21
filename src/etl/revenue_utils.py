# src/etl/revenue_utils.py
"""Revenue string parsing and approximate USD normalization."""

from __future__ import annotations

import math
import re
from typing import Final

# Approximate rates: multiply native amount by this to get USD (JPY: yen → USD).
CURRENCY_TO_USD: Final[dict[str, float]] = {
    "USD": 1.0,
    "EUR": 1.1,
    "GBP": 1.27,
    "JPY": 1.0 / 150.0,
}

_MISSING_TOKENS: Final[frozenset[str]] = frozenset(
    {"", "N/A", "NA", "NAN", "NOT DISCLOSED"}
)


def _is_missing_revenue(raw: str | None) -> bool:
    if raw is None:
        return True
    s = raw.strip()
    if not s:
        return True
    if s.upper() in _MISSING_TOKENS:
        return True
    return False


def _detect_currency(s: str) -> str:
    if "¥" in s:
        return "JPY"
    if "€" in s:
        return "EUR"
    if "£" in s:
        return "GBP"
    t = s.strip()
    if t.upper().endswith("USD"):
        return "USD"
    if "$" in s:
        return "USD"
    return "USD"


def _strip_currency_marks(s: str) -> str:
    out = s
    for ch in "£€¥$":
        out = out.replace(ch, "")
    out = re.sub(r"\bUSD\b", "", out, flags=re.IGNORECASE)
    return out.strip()


def _scale_from_suffix(rest: str) -> tuple[float, str]:
    """Return (multiplier, remainder with scale markers removed)."""
    t = rest.strip()
    low = t.lower()
    mult = 1.0
    if re.search(r"\bbillion\b", low):
        mult *= 1e9
        t = re.sub(r"\s*billion\b", "", t, flags=re.IGNORECASE).strip()
    elif re.search(r"\bmillion\b", low):
        mult *= 1e6
        t = re.sub(r"\s*million\b", "", t, flags=re.IGNORECASE).strip()
    elif re.search(r"\bthousand\b", low):
        mult *= 1e3
        t = re.sub(r"\s*thousand\b", "", t, flags=re.IGNORECASE).strip()

    m = re.match(r"^(.+?)\s*([bmkBMK])\s*$", t.strip())
    if m:
        base, letter = m.group(1).strip(), m.group(2).upper()
        letter_mult = {"B": 1e9, "M": 1e6, "K": 1e3}[letter]
        mult *= letter_mult
        t = base
    return mult, t


def _parse_single_native_amount(text: str) -> tuple[float, str]:
    s = text.strip()
    currency = _detect_currency(s)
    body = _strip_currency_marks(s)
    mult, num_part = _scale_from_suffix(body)
    num_part = num_part.replace(",", "").strip()
    if not num_part:
        raise ValueError(f"no numeric part in {text!r}")
    num_part = re.sub(r"^[^\d\-]*", "", num_part)
    m = re.match(r"^-?[\d.]+", num_part)
    if not m:
        raise ValueError(f"no number in {text!r}")
    value = float(m.group(0)) * mult
    return value, currency


def _single_to_usd(text: str) -> float:
    native, currency = _parse_single_native_amount(text)
    return native * CURRENCY_TO_USD[currency]


def dollar_revenue(revenue: str | float | None) -> int:
    """
    Clean revenue string → approximate USD integer.

    - Converts EUR / GBP / JPY using ``CURRENCY_TO_USD``.
    - Range strings ``a - b`` or ``a-b`` (e.g. ``$10M - $20M``, ``5M-10M``) use the midpoint.
    - Parses B/M/K, ``billion`` / ``million``, and comma-separated numbers.
    - Missing / N/A / Not disclosed → 0.
    """
    if revenue is None or (isinstance(revenue, float) and math.isnan(revenue)):
        return 0
    if not isinstance(revenue, str):
        revenue = str(revenue)
    if _is_missing_revenue(revenue):
        return 0

    s = revenue.strip()
    if " - " in s:
        left, right = s.split(" - ", 1)
        usd = (_single_to_usd(left) + _single_to_usd(right)) / 2.0
        return int(round(usd))

    if "-" in s:
        idx = s.find("-")
        left, right = s[:idx].strip(), s[idx + 1 :].strip()
        if left and right:
            try:
                usd = (_single_to_usd(left) + _single_to_usd(right)) / 2.0
                return int(round(usd))
            except ValueError:
                pass

    return int(round(_single_to_usd(s)))
