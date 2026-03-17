"""
Date/time helpers for schema profiling.
"""

from __future__ import annotations

import pandas as pd


def is_datetime_like_series(s: pd.Series, threshold: float = 0.7) -> bool:
    if s.empty:
        return False
    if s.dtype.kind in ("i", "u", "f"):
        return False
    parsed = pd.to_datetime(s, errors="coerce", utc=False, format="mixed")
    return float(parsed.notna().mean()) >= float(threshold)
