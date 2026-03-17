"""
Upload + dataset profile routes.

Endpoints:
- POST /upload-csv
- GET  /datasets
- GET  /dataset/{dataset_id}/schema
- GET  /dataset/{dataset_id}/preview
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas import (
    DatasetProfile,
    DatasetSchemaResponse,
    DatasetPreviewResponse,
    DatasetsListResponse,
)
from app.services.csv_service import ingest_csv_upload
from app.services.dataset_registry import (
    get_dataset_profile,
    list_datasets,
    get_dataset_schema,
    get_dataset_preview,
)

router = APIRouter()


@router.post("/upload-csv", response_model=DatasetProfile)
async def upload_csv(file: UploadFile = File(...)):
    try:
        return await ingest_csv_upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}") from e


@router.get("/datasets", response_model=DatasetsListResponse)
def datasets_list():
    return DatasetsListResponse(datasets=list_datasets())


@router.get("/dataset/{dataset_id}/schema", response_model=DatasetSchemaResponse)
def dataset_schema(dataset_id: str):
    try:
        prof = get_dataset_profile(dataset_id)
        cols = get_dataset_schema(dataset_id)
        return DatasetSchemaResponse(dataset_id=dataset_id, table_name=prof.table_name, columns=cols)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema failed: {e}") from e


@router.get("/dataset/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def dataset_preview(dataset_id: str, limit: int = 10):
    try:
        prof = get_dataset_profile(dataset_id)
        rows = get_dataset_preview(dataset_id, limit=limit)
        return DatasetPreviewResponse(dataset_id=dataset_id, table_name=prof.table_name, rows=rows)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {e}") from e

