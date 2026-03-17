"""
Follow-up / chat route.

Endpoint:
- POST /follow-up
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import FollowUpRequest, FollowUpResponse
from app.services.dashboard_engine import follow_up

router = APIRouter()


@router.post("/follow-up", response_model=FollowUpResponse)
def follow_up_endpoint(req: FollowUpRequest):
    try:
        return follow_up(session_id=req.session_id, prompt=req.prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Follow-up failed: {e}") from e

