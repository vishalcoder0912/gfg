"""
Dashboard generation route.

Endpoint:
- POST /generate-dashboard

Pipeline:
prompt -> schema_context -> Gemini plan -> validate plan -> generate SQL per chart intent
-> validate SQL -> execute -> chart selection -> KPIs -> insights -> dashboard JSON
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import GenerateDashboardRequest, GenerateDashboardResponse
from app.services.dashboard_engine import generate_dashboard

router = APIRouter()


@router.post("/generate-dashboard", response_model=GenerateDashboardResponse)
def generate_dashboard_endpoint(req: GenerateDashboardRequest):
    try:
        return generate_dashboard(dataset_id=req.dataset_id, prompt=req.prompt, prior_session=None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {e}") from e

