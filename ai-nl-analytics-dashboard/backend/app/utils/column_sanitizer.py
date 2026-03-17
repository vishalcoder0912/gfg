"""
Column sanitization utilities.
"""

from __future__ import annotations

import re
from typing import Dict, List

import pandas as pd


def sanitize_identifier(name: str) -> str:
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if not name:
        name = "col"
    if name[0].isdigit():
        name = f"c_{name}"
    return name


def _dedupe(names: List[str]) -> List[str]:
    seen: Dict[str, int] = {}
    out: List[str] = []
    for n in names:
        if n not in seen:
            seen[n] = 0
            out.append(n)
            continue
        seen[n] += 1
        out.append(f"{n}_{seen[n]}")
    return out


def sanitize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = _dedupe([sanitize_identifier(c) for c in df.columns])
    return df

