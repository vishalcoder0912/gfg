from __future__ import annotations
import io
import os
import time
from typing import Any, Dict, List, Tuple
import chardet
import pandas as pd
from fastapi import UploadFile
from app.database import sqlite_conn_rw
from app.schemas import DatasetProfile
from app.utils.column_sanitizer import sanitize_identifier

def detect_encoding(data: bytes) -> str:
    """Detect the encoding of a given data block."""
    guess = chardet.detect(data[:20000])
    return str(guess.get("encoding", "utf-8"))

async def ingest_csv_to_sqlite(file: UploadFile) -> DatasetProfile:
    """Ingest a CSV file into SQLite and return its profile."""
    data = await file.read()
    enc = detect_encoding(data)
    try:
        df = pd.read_csv(io.BytesIO(data), encoding=enc)
    except Exception:
        df = pd.read_csv(io.BytesIO(data), encoding="latin-1")
    
    df.columns = [sanitize_identifier(str(c)) for c in df.columns]
    
    timestamp = int(time.time())
    table_name = f"data_{timestamp}"
    dataset_id = f"ds_{timestamp}"
    
    with sqlite_conn_rw() as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        
    numeric = list(df.select_dtypes(include=["number"]).columns)
    categorical = [c for c in df.columns if c not in set(numeric)]
    date_cols = []
    
    return DatasetProfile(
        dataset_id=dataset_id,
        table_name=table_name,
        source="upload",
        original_filename=file.filename or "unknown",
        row_count=len(df),
        column_count=len(df.columns),
        columns=list(df.columns),
        numeric_columns=numeric,
        categorical_columns=categorical,
        date_columns=date_cols,
        preview_rows=df.head(5).to_dict(orient="records")
    )

def ingest_demo_dataset_to_sqlite() -> DatasetProfile:
    """Ingest a demo dataset into SQLite."""
    # Look for demo sales data in the preferred location
    demo_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "demo", "demo_sales.csv")
    if not os.path.exists(demo_path):
        # Fallback to the one in the root if it exists
        demo_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sample_sales_data.csv")
        
    if not os.path.exists(demo_path):
        raise FileNotFoundError(f"Demo CSV not found at {demo_path}")
        
    with open(demo_path, "rb") as f:
        data = f.read()
    
    df = pd.read_csv(io.BytesIO(data))
    df.columns = [sanitize_identifier(str(c)) for c in df.columns]
    table_name = "demo_sales"
    dataset_id = "demo_sales"
    
    with sqlite_conn_rw() as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        
    numeric = list(df.select_dtypes(include=["number"]).columns)
    categorical = [c for c in df.columns if c not in set(numeric)]
    date_cols = []
    
    return DatasetProfile(
        dataset_id=dataset_id,
        table_name=table_name,
        source="demo",
        original_filename=os.path.basename(demo_path),
        row_count=len(df),
        column_count=len(df.columns),
        columns=list(df.columns),
        numeric_columns=numeric,
        categorical_columns=categorical,
        date_columns=date_cols,
        preview_rows=df.head(5).to_dict(orient="records")
    )
