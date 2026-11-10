"""Data cleaning and normalization utilities for Zomato restaurant data."""
import re
from typing import Optional, Tuple


def clean_rating(rate_str: Optional[str]) -> Optional[float]:
    """Extract numeric rating from strings like '4.1/5', '3.8', 'NEW', '-'."""
    if not rate_str or not isinstance(rate_str, str):
        return None
    val = rate_str.strip()
    if val in {"NEW", "-", "", "nan"}:
        return None
    match = re.match(r"^(\d+(\.\d+)?)", val)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def clean_cost(cost_str: Optional[str]) -> Optional[float]:
    """Parse approx cost for two people from strings like '800', '1,200', etc."""
    if not cost_str:
        return None
    if isinstance(cost_str, (int, float)):
        return float(cost_str) if cost_str > 0 else None
    val = str(cost_str).replace(",", "").strip()
    try:
        cost = float(val)
        return cost if cost > 0 else None
    except ValueError:
        return None


def clean_votes(votes_val) -> int:
    """Parse votes into an integer."""
    if votes_val is None:
        return 0
    try:
        return int(float(str(votes_val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0


def normalize_text(text: Optional[str]) -> str:
    """Trim and lower text for case-insensitive matching."""
    if not text:
        return ""
    return str(text).strip()
