"""
chat.py — Follow-up / chat route.

FIX: Same JSON-safety fix as dashboard.py.
     raise HTTPException produced plain text which crashed the frontend parser.
"""

from __future__ import annotations
import logging
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import FollowUpRequest, FollowUpResponse
from app.services.dashboard_engine import follow_up

router  = APIRouter()
logger  = logging.getLogger(__name__)


@router.post("/follow-up", response_model=FollowUpResponse)
def follow_up_endpoint(req: FollowUpRequest):
    try:
        return follow_up(session_id=req.session_id, prompt=req.prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_safe(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("follow_up error:\n%s", traceback.format_exc())
        # Always return JSON — never plain text
        return JSONResponse(
            status_code=500,
            content={"detail": f"Follow-up failed: {_safe(e)}"},
        )


def _safe(e: Exception) -> str:
    return str(e).replace("\n", " ").strip()[:500]