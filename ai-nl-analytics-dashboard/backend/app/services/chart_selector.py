"""
Deterministic chart selection engine (mandatory).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def _numeric_keys(df: pd.DataFrame) -> List[str]:
    return [str(c) for c in df.select_dtypes(include=["number"]).columns]


def _datetime_like_key(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        if df[c].dtype.kind in ("i", "u", "f"):
            continue
        s = pd.to_datetime(df[c], errors="coerce")
        if s.notna().mean() >= 0.7:
            return str(c)
    return None


def _category_key(df: pd.DataFrame, numeric: List[str]) -> Optional[str]:
    for c in df.columns:
        if str(c) not in set(numeric):
            return str(c)
    return None


def choose_chart(rows: List[Dict[str, Any]]) -> Tuple[str, Optional[str], List[str]]:
    if not rows:
        return "table", None, []
    df = pd.DataFrame(rows)
    if df.shape[1] < 2:
        return "table", None, []

    numeric = _numeric_keys(df)
    if not numeric:
        return "table", None, []

    time_key = _datetime_like_key(df)
    if time_key:
        if len(numeric) >= 2:
            return "area", time_key, numeric[:4]
        return "line", time_key, numeric[:2]

    cat = _category_key(df, numeric=numeric)
    if not cat:
        return "table", None, []

    if len(numeric) == 1:
        uniq = df[cat].nunique(dropna=False)
        if 2 <= uniq <= 6:
            return "pie", cat, [numeric[0]]
        return "bar", cat, [numeric[0]]

    return "stacked_bar", cat, numeric[:4]

