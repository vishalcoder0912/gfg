"""
Dataset registry (in-memory) for the prototype.

Stores:
- dataset_id -> DatasetProfile + table_name

Also ensures a built-in demo dataset is available for immediate use.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from app.database import ensure_meta_tables, sqlite_conn_ro, sqlite_conn_rw, inspect_table_schema, fetch_preview_rows
from app.schemas import DatasetProfile, DatasetSchemaColumn
from app.services.schema_profiler import profile_dataframe
from app.utils.column_sanitizer import sanitize_dataframe_columns, sanitize_identifier

_DATASETS: Dict[str, DatasetProfile] = {}
_LOADED_FROM_DB = False

def _persist_profile(profile: DatasetProfile) -> None:
    """Persist a dataset profile to the SQLite metadata table."""
    ensure_meta_tables()
    with sqlite_conn_rw() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO datasets_meta (
              dataset_id, table_name, source, original_filename,
              row_count, column_count,
              columns_json, numeric_columns_json, categorical_columns_json, date_columns_json,
              preview_rows_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                profile.dataset_id,
                profile.table_name,
                profile.source,
                profile.original_filename,
                int(profile.row_count),
                int(profile.column_count),
                json.dumps(profile.columns, ensure_ascii=True),
                json.dumps(profile.numeric_columns, ensure_ascii=True),
                json.dumps(profile.categorical_columns, ensure_ascii=True),
                json.dumps(profile.date_columns, ensure_ascii=True),
                json.dumps(profile.preview_rows, ensure_ascii=True),
                int(time.time()),
            ),
        )
        conn.commit()

def _load_registry_from_sqlite() -> None:
    """Load all persisted dataset profiles from SQLite into the in-memory registry."""
    global _LOADED_FROM_DB
    if _LOADED_FROM_DB:
        return
        
    ensure_meta_tables()
    try:
        with sqlite_conn_ro() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                  dataset_id, table_name, source, original_filename,
                  row_count, column_count,
                  columns_json, numeric_columns_json, categorical_columns_json, date_columns_json,
                  preview_rows_json
                FROM datasets_meta
                ORDER BY created_at DESC;
                """
            )
            rows = cur.fetchall()

        for r in rows:
            dataset_id = str(r[0])
            try:
                _DATASETS[dataset_id] = DatasetProfile(
                    dataset_id=dataset_id,
                    table_name=str(r[1]),
                    source=str(r[2]),
                    original_filename=r[3],
                    row_count=int(r[4]),
                    column_count=int(r[5]),
                    columns=json.loads(r[6] or "[]"),
                    numeric_columns=json.loads(r[7] or "[]"),
                    categorical_columns=json.loads(r[8] or "[]"),
                    date_columns=json.loads(r[9] or "[]"),
                    preview_rows=json.loads(r[10] or "[]"),
                )
            except Exception:
                # Skip malformed records to maintain registry stability
                continue
        _LOADED_FROM_DB = True
    except Exception:
        # Fallback if table doesn't exist yet
        pass

def ensure_demo_dataset_loaded() -> None:
    """
    Ensure the demo dataset is loaded into SQLite and registered.
    Uses 'demo_sales' as a stable ID.
    """
    dataset_id = "demo_sales"
    _load_registry_from_sqlite()
    
    if dataset_id in _DATASETS:
        return

    # Robust path detection for the demo CSV
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "demo", "demo_sales.csv"),
        os.path.join(os.getcwd(), "ai-nl-analytics-dashboard", "backend", "data", "demo", "demo_sales.csv"),
        os.path.join(os.getcwd(), "backend", "data", "demo", "demo_sales.csv"),
        os.path.join(os.getcwd(), "sample_sales_data.csv"),
    ]
    
    demo_path = None
    for p in possible_paths:
        if os.path.exists(p):
            demo_path = os.path.abspath(p)
            break
            
    if not demo_path:
        return

    try:
        df = pd.read_csv(demo_path)
        df = sanitize_dataframe_columns(df)
        table_name = "demo_sales"

        with sqlite_conn_rw() as conn:
            df.to_sql(table_name, conn, if_exists="replace", index=False)

        prof = profile_dataframe(
            df,
            dataset_id=dataset_id,
            table_name=table_name,
            source="demo",
            original_filename=os.path.basename(demo_path),
        )
        _DATASETS[dataset_id] = prof
        _persist_profile(prof)
    except Exception:
        # Silent fail on demo load to prevent app crash; user will see error on access
        pass

def register_uploaded_dataset(df: pd.DataFrame, original_filename: str) -> DatasetProfile:
    """Register a new uploaded CSV as a dataset."""
    _load_registry_from_sqlite()
    
    timestamp = int(time.time())
    dataset_id = f"ds_{timestamp}"
    # Sanitize filename for table name safety
    safe_name = sanitize_identifier(original_filename.rsplit('.', 1)[0])
    table_name = f"t_{safe_name}_{timestamp}"

    df = sanitize_dataframe_columns(df)

    with sqlite_conn_rw() as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)

    prof = profile_dataframe(
        df,
        dataset_id=dataset_id,
        table_name=table_name,
        source="upload",
        original_filename=original_filename,
    )
    _DATASETS[dataset_id] = prof
    _persist_profile(prof)
    return prof

def get_dataset_profile(dataset_id: str) -> DatasetProfile:
    """Retrieve a dataset profile by ID."""
    _load_registry_from_sqlite()
    if dataset_id not in _DATASETS:
        # If not in memory, try a fresh load
        global _LOADED_FROM_DB
        _LOADED_FROM_DB = False
        _load_registry_from_sqlite()
        
    if dataset_id not in _DATASETS:
        raise ValueError(f"Unknown dataset_id: {dataset_id}. Please upload a CSV first.")
    return _DATASETS[dataset_id]

def list_datasets() -> List[DatasetProfile]:
    """List all registered datasets."""
    _load_registry_from_sqlite()
    return list(_DATASETS.values())

def get_dataset_schema(dataset_id: str) -> List[DatasetSchemaColumn]:
    """Get the SQLite schema for a specific dataset."""
    prof = get_dataset_profile(dataset_id)
    rows = inspect_table_schema(prof.table_name)
    return [DatasetSchemaColumn(name=name, sqlite_type=sqlite_type) for (name, sqlite_type) in rows]

def get_dataset_preview(dataset_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch a few rows from the dataset table."""
    prof = get_dataset_profile(dataset_id)
    return fetch_preview_rows(prof.table_name, limit=limit)
