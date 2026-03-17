"""
Dataset schema profiling.

Detects:
- numeric columns
- categorical columns
- date/time columns (best-effort)
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

import pandas as pd

from app.schemas import DatasetProfile
from app.utils.date_utils import is_datetime_like_series


def profile_dataframe(
    df: pd.DataFrame,
    dataset_id: str,
    table_name: str,
    source: Literal["demo", "upload"],
    original_filename: Optional[str],
) -> DatasetProfile:
    numeric_cols = [str(c) for c in df.select_dtypes(include=["number"]).columns]

    date_cols: List[str] = []
    for c in df.columns:
        sc = str(c)
        if sc in set(numeric_cols):
            continue
        if is_datetime_like_series(df[c]):
            date_cols.append(sc)

    categorical_cols = [str(c) for c in df.columns if str(c) not in set(numeric_cols) | set(date_cols)]
    preview_rows: List[Dict[str, Any]] = df.head(10).to_dict(orient="records")

    return DatasetProfile(
        dataset_id=dataset_id,
        table_name=table_name,
        source=source,
        original_filename=original_filename,
        row_count=int(df.shape[0]),
        column_count=int(df.shape[1]),
        columns=[str(c) for c in df.columns],
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        date_columns=date_cols,
        preview_rows=preview_rows,
    )

