"""
SQLite-backed session storage for follow-up chat prompts.

Previously sessions were held in a plain Python dict (_SESSIONS) which was wiped
on every backend restart, causing "Unknown session_id" errors on the follow-up
chat endpoint.

Fix: every session is now written to the `sessions_meta` table in app_data.db.
Sessions older than SESSION_TTL_SECONDS (24 hours) are considered expired.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict

from app.database import sqlite_conn_ro, sqlite_conn_rw

# Sessions expire after 24 hours of inactivity
SESSION_TTL_SECONDS: float = 60 * 60 * 24


@dataclass
class SessionState:
    session_id: str
    dataset_id: str
    original_prompt: str
    last_dashboard: Dict[str, Any]
    last_plan: Dict[str, Any]
    last_sql_queries: Any
    updated_at: float


def create_session(
    dataset_id: str,
    original_prompt: str,
    dashboard: Dict[str, Any],
    plan: Dict[str, Any],
    sql_queries: Any,
) -> str:
    sid = str(uuid.uuid4())
    now = time.time()
    with sqlite_conn_rw() as conn:
        conn.execute(
            """
            INSERT INTO sessions_meta
              (session_id, dataset_id, original_prompt,
               last_dashboard, last_plan, last_sql_queries, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sid,
                dataset_id,
                original_prompt,
                json.dumps(dashboard,    ensure_ascii=True),
                json.dumps(plan,         ensure_ascii=True),
                json.dumps(sql_queries,  ensure_ascii=True),
                now,
            ),
        )
        conn.commit()
    return sid


def get_session(session_id: str) -> SessionState:
    with sqlite_conn_ro() as conn:
        cur = conn.execute(
            """
            SELECT session_id, dataset_id, original_prompt,
                   last_dashboard, last_plan, last_sql_queries, updated_at
            FROM sessions_meta
            WHERE session_id = ?
            """,
            (session_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise ValueError("Unknown session_id. Generate a dashboard first.")

    (sid, dataset_id, original_prompt,
     last_dashboard_raw, last_plan_raw, last_sql_raw, updated_at) = row

    # Enforce TTL
    if (time.time() - float(updated_at)) > SESSION_TTL_SECONDS:
        _delete_session(session_id)
        raise ValueError("Session expired. Please generate a new dashboard.")

    return SessionState(
        session_id=sid,
        dataset_id=dataset_id,
        original_prompt=original_prompt,
        last_dashboard=json.loads(last_dashboard_raw),
        last_plan=json.loads(last_plan_raw),
        last_sql_queries=json.loads(last_sql_raw),
        updated_at=float(updated_at),
    )


def update_session(
    session_id: str,
    dashboard: Dict[str, Any],
    plan: Dict[str, Any],
    sql_queries: Any,
) -> None:
    # Verify it exists first (raises ValueError if not found / expired)
    get_session(session_id)
    now = time.time()
    with sqlite_conn_rw() as conn:
        conn.execute(
            """
            UPDATE sessions_meta
            SET last_dashboard = ?,
                last_plan = ?,
                last_sql_queries = ?,
                updated_at = ?
            WHERE session_id = ?
            """,
            (
                json.dumps(dashboard,   ensure_ascii=True),
                json.dumps(plan,        ensure_ascii=True),
                json.dumps(sql_queries, ensure_ascii=True),
                now,
                session_id,
            ),
        )
        conn.commit()


def _delete_session(session_id: str) -> None:
    """Remove a single expired session row."""
    with sqlite_conn_rw() as conn:
        conn.execute("DELETE FROM sessions_meta WHERE session_id = ?", (session_id,))
        conn.commit()
