"""
Executes SQL queries against SQLite (read-only).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.database import sqlite_conn_ro


def execute_select(sql: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    with sqlite_conn_ro() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows_raw = cur.fetchmany(1000)
        rows: List[Dict[str, Any]] = []
        for r in rows_raw:
            rows.append({cols[i]: r[i] for i in range(len(cols))})
        return cols, rows

