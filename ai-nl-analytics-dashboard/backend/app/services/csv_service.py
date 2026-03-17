"""
CSV upload service.

Validates upload and parses CSV with safe encoding detection.
Registers dataset into SQLite and the in-memory dataset registry.
"""

from __future__ import annotations
import io
import chardet
import pandas as pd
from fastapi import UploadFile
from app.config import settings
from app.schemas import DatasetProfile
from app.services.dataset_registry import register_uploaded_dataset

def _format_bytes(n: int) -> str:
    """Format a byte count into a human-readable string."""
    units = ["B", "KB", "MB", "GB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    decimals = 0 if i == 0 else 1
    return f"{v:.{decimals}f} {units[i]}"

def _detect_encoding(data: bytes) -> str:
    """
    Detect the encoding of a given data block.
    Checks common UTF-8 variants first, then falls back to chardet.
    """
    # Check for UTF-8 variants on a prefix to avoid full file decoding twice
    prefix = data[:1024 * 1024]
    for enc in ("utf-8-sig", "utf-8"):
        try:
            prefix.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
            
    # Fallback to chardet detection on a reasonably sized sample
    guess = chardet.detect(data[:50000])
    if guess and guess.get("encoding"):
        return str(guess["encoding"])
    return "latin-1"

def _validate_upload(file: UploadFile, size_bytes: int) -> None:
    """Validate basic upload constraints like filename and size."""
    if not file.filename:
        raise ValueError("Missing filename.")
    if not file.filename.lower().endswith(".csv"):
        raise ValueError("Only .csv files are supported.")
    if size_bytes <= 0:
        raise ValueError("Empty file.")
    if size_bytes > settings.APP_MAX_UPLOAD_BYTES:
        raise ValueError(
            f"File too large. Max is {settings.APP_MAX_UPLOAD_BYTES} bytes ({_format_bytes(settings.APP_MAX_UPLOAD_BYTES)}). "
            "Increase APP_MAX_UPLOAD_BYTES in backend/.env to allow larger uploads."
        )

async def ingest_csv_upload(file: UploadFile) -> DatasetProfile:
    """
    Main entry point for CSV file ingestion.
    Reads, validates, parses, and registers the dataset.
    """
    data = await file.read()
    _validate_upload(file, len(data))

    enc = _detect_encoding(data)
    try:
        # We use low_memory=False to ensure better type inference for hackathon data
        df = pd.read_csv(io.BytesIO(data), encoding=enc, low_memory=False)
    except Exception:
        # Common fallback for Windows-encoded CSVs
        try:
            df = pd.read_csv(io.BytesIO(data), encoding="latin-1", low_memory=False)
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {e}")

    if df.empty:
        raise ValueError("CSV parsed successfully but contains zero data rows.")

    # Delegate registration and DB insertion to the registry
    return register_uploaded_dataset(df, original_filename=file.filename)
