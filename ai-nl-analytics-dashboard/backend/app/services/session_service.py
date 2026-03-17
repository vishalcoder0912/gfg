"""
In-memory session memory for follow-up prompts (prototype).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class SessionState:
    session_id: str
    dataset_id: str
    original_prompt: str
    last_dashboard: Dict[str, Any]
    last_plan: Dict[str, Any]
    last_sql_queries: Any
    updated_at: float


_SESSIONS: Dict[str, SessionState] = {}


def create_session(dataset_id: str, original_prompt: str, dashboard: Dict[str, Any], plan: Dict[str, Any], sql_queries: Any) -> str:
    sid = str(uuid.uuid4())
    _SESSIONS[sid] = SessionState(
        session_id=sid,
        dataset_id=dataset_id,
        original_prompt=original_prompt,
        last_dashboard=dashboard,
        last_plan=plan,
        last_sql_queries=sql_queries,
        updated_at=time.time(),
    )
    return sid


def get_session(session_id: str) -> SessionState:
    if session_id not in _SESSIONS:
        raise ValueError("Unknown session_id. Generate a dashboard first.")
    return _SESSIONS[session_id]


def update_session(session_id: str, dashboard: Dict[str, Any], plan: Dict[str, Any], sql_queries: Any) -> None:
    s = get_session(session_id)
    s.last_dashboard = dashboard
    s.last_plan = plan
    s.last_sql_queries = sql_queries
    s.updated_at = time.time()

