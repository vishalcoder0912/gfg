"""
SQLite database helpers.

We intentionally keep DB access isolated so PostgreSQL can be added later by
replacing this module and the query executor.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Sequence, Tuple

from app.config import settings


def ensure_sqlite_parent_dir() -> None:
    parent = os.path.dirname(os.path.abspath(settings.APP_DB_PATH))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def ensure_meta_tables() -> None:
    """
    Create metadata tables required for multi-dataset support.
    """
    ensure_sqlite_parent_dir()
    with sqlite_conn_rw() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets_meta (
              dataset_id TEXT PRIMARY KEY,
              table_name TEXT NOT NULL,
              source TEXT NOT NULL,
              original_filename TEXT,
              row_count INTEGER NOT NULL,
              column_count INTEGER NOT NULL,
              columns_json TEXT NOT NULL,
              numeric_columns_json TEXT NOT NULL,
              categorical_columns_json TEXT NOT NULL,
              date_columns_json TEXT NOT NULL,
              preview_rows_json TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            """.strip()
        )
        conn.commit()


def quote_ident(ident: str) -> str:
    """
    Quote a SQLite identifier safely.

    Identifiers are expected to already be sanitized (letters, numbers, underscores).
    We still validate to avoid accidental SQL injection via identifier strings.
    """
    ident = str(ident)
    if not ident or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in ident):
        raise ValueError(f"Unsafe SQLite identifier: {ident!r}")
    return f'"{ident}"'


@contextmanager
def sqlite_conn_rw():
    conn = sqlite3.connect(settings.APP_DB_PATH, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def sqlite_conn_ro():
    db_abs = os.path.abspath(settings.APP_DB_PATH)
    uri = f"file:{db_abs}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


def create_table_from_rows(
    table_name: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    if_exists: str = "replace",
) -> None:
    """
    Create (or replace) a SQLite table and insert rows.

    This is a minimal sqlite3-native helper. We keep types flexible (stored as TEXT/REAL/INTEGER by SQLite affinity).
    """
    if if_exists not in {"replace", "fail", "append"}:
        raise ValueError("if_exists must be one of: replace, fail, append")

    q_table = quote_ident(table_name)
    cols = [str(c) for c in columns]
    q_cols = [quote_ident(c) for c in cols]

    with sqlite_conn_rw() as conn:
        cur = conn.cursor()
        if if_exists == "replace":
            cur.execute(f"DROP TABLE IF EXISTS {q_table};")
        elif if_exists == "fail":
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?;",
                (table_name,),
            )
            if cur.fetchone():
                raise ValueError(f"Table already exists: {table_name}")

        cur.execute(f"CREATE TABLE IF NOT EXISTS {q_table} ({', '.join(f'{c} TEXT' for c in q_cols)});")

        if rows:
            placeholders = ", ".join(["?"] * len(cols))
            cur.executemany(
                f"INSERT INTO {q_table} ({', '.join(q_cols)}) VALUES ({placeholders});",
                list(rows),
            )
        conn.commit()


def inspect_table_schema(table_name: str) -> List[Tuple[str, str]]:
    """
    Return list of (column_name, sqlite_type) for a table.
    """
    q_table = quote_ident(table_name)
    with sqlite_conn_ro() as conn:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({q_table});")
        rows = cur.fetchall()
        return [(str(r[1]), str(r[2])) for r in rows]


def fetch_preview_rows(table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    q_table = quote_ident(table_name)
    limit = max(1, min(int(limit), 50))
    with sqlite_conn_ro() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {q_table} LIMIT ?;", (limit,))
        col_names = [d[0] for d in cur.description] if cur.description else []
        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            out.append({col_names[i]: r[i] for i in range(len(col_names))})
        return out
