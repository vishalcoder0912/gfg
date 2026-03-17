from __future__ import annotations
import re
from typing import List
import sqlparse

_FORBIDDEN = {"insert", "update", "delete", "drop", "alter", "create", "pragma", "attach", "detach"}

def _ensure_single_statement(sql: str) -> str:
    parts = [p.strip() for p in sqlparse.split(sql) if p.strip()]
    if len(parts) != 1: raise ValueError("Only single SQL allowed.")
    return parts[0]

def _reject_forbidden(sql: str) -> None:
    lowered = sql.lower()
    for kw in _FORBIDDEN:
        if re.search(rf"\b{kw}\b", lowered): raise ValueError(f"Forbidden: {kw}")

def guard_and_normalize_sql(raw_sql: str, allowed_tables: List[str]) -> str:
    sql = raw_sql.strip()
    if not sql: raise ValueError("Empty SQL.")
    sql = _ensure_single_statement(sql)
    _reject_forbidden(sql)
    
    # Simple table validation
    lowered = sql.lower()
    if "from" in lowered:
        table_ref = re.search(r"from\s+([a-zA-Z0-9_]+)", lowered)
        if table_ref:
            table_name = table_ref.group(1)
            if table_name not in [t.lower() for t in allowed_tables]:
                raise ValueError(f"Disallowed table: {table_name}")

    if "limit" not in lowered:
        sql += " LIMIT 1000"
    return sql
