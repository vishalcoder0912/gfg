"""
SQL safety validator.

FIX: _reject_comments() used to BLOCK any SQL that contained -- or /* */
     comments. Gemini almost always adds inline comments to its generated SQL,
     so this was blocking every single query.

     New behaviour: comments are STRIPPED before any other validation step.
     The rest of the validation pipeline (forbidden keywords, table restriction,
     LIMIT enforcement, single-statement check) is unchanged.
"""

from __future__ import annotations
import re
from typing import List
import sqlparse


_FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "truncate", "create",
    "replace", "pragma", "attach", "detach", "vacuum", "reindex", "grant", "revoke",
}
_FORBIDDEN_SUBSTRINGS = {"sqlite_master", "sqlite_temp_master"}


def _strip(sql: str) -> str:
    return sql.strip().strip("\ufeff").strip()


# ── FIX: strip comments instead of rejecting them ────────────────────────────
def _strip_comments(sql: str) -> str:
    """Remove /* block */ and -- line comments before validation."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)   # block comments
    sql = re.sub(r"--[^\n]*", " ", sql)                      # line comments
    sql = re.sub(r"[ \t]+", " ", sql).strip()                # collapse whitespace
    return sql


def _normalize_sqlite_dialect(sql: str) -> str:
    out = sql
    out = re.sub(r"\bnow\s*\(\s*\)\b", "CURRENT_TIMESTAMP", out, flags=re.IGNORECASE)
    out = re.sub(r"\bilike\b", "LIKE", out, flags=re.IGNORECASE)
    out = re.sub(
        r"\bdate_trunc\s*\(\s*'month'\s*,\s*([^)]+?)\s*\)",
        r"date(\1, 'start of month')", out, flags=re.IGNORECASE,
    )
    out = re.sub(
        r"\bextract\s*\(\s*year\s+from\s+([^)]+?)\s*\)",
        r"CAST(strftime('%Y', \1) AS INTEGER)", out, flags=re.IGNORECASE,
    )
    return out


def _strip_trailing_semicolon(sql: str) -> str:
    if ";" not in sql:
        return sql
    if sql.rstrip().endswith(";") and sql.count(";") == 1:
        return sql.rstrip()[:-1].rstrip()
    raise ValueError("Semicolon chaining / multiple statements are not allowed.")


def _ensure_single_statement(sql: str) -> str:
    parts = [p.strip() for p in sqlparse.split(sql) if p.strip()]
    if len(parts) != 1:
        raise ValueError("Only a single SQL statement is allowed.")
    return parts[0]


def _statement_kind(sql: str) -> str:
    parsed = sqlparse.parse(sql)
    if not parsed:
        return ""
    for token in parsed[0].flatten():
        if token.is_whitespace or token.value in ("(", ")"):
            continue
        return token.value.upper()
    return ""


def _reject_forbidden(sql: str) -> None:
    low = sql.lower()
    for s in _FORBIDDEN_SUBSTRINGS:
        if s in low:
            raise ValueError(f"Forbidden reference detected: {s}")
    for kw in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", low):
            raise ValueError(f"Forbidden SQL keyword detected: {kw.upper()}")


def _extract_table_refs(sql: str) -> List[str]:
    refs: List[str] = []
    for m in re.finditer(
        r'\b(from|join)\s+(?:"([a-zA-Z0-9_]+)"|`([a-zA-Z0-9_]+)`|([a-zA-Z0-9_]+))',
        sql.lower(),
    ):
        refs.append(m.group(2) or m.group(3) or m.group(4))
    return refs


def _enforce_table(sql: str, allowed_tables: List[str]) -> None:
    if not allowed_tables:
        return
    allowed = {t.lower() for t in allowed_tables}
    for r in _extract_table_refs(sql):
        if r.lower() not in allowed:
            raise ValueError(
                f"Query references disallowed table '{r}'. Allowed: {', '.join(allowed_tables)}"
            )


def _ensure_limit(sql: str, max_limit: int = 1000) -> str:
    m = re.search(r"\blimit\s+(\d+)\b", sql, flags=re.IGNORECASE)
    if m:
        if int(m.group(1)) > max_limit:
            sql = re.sub(r"(\blimit\s+)\d+\b", rf"\g<1>{max_limit}", sql, flags=re.IGNORECASE)
        return sql
    return sql.rstrip() + f" LIMIT {max_limit}"


def validate_and_normalize_sql(raw_sql: str, allowed_tables: List[str]) -> str:
    sql = _strip(raw_sql)
    if not sql:
        raise ValueError("Empty SQL.")

    sql = _strip_comments(sql)               # ← FIX: strip first, don't reject
    if not sql:
        raise ValueError("SQL empty after stripping comments.")

    sql = _normalize_sqlite_dialect(sql)
    sql = _strip_trailing_semicolon(sql)
    sql = _ensure_single_statement(sql)
    _reject_forbidden(sql)

    kind = _statement_kind(sql)
    if kind not in ("SELECT", "WITH"):
        raise ValueError("Only SELECT or WITH statements are allowed.")

    _enforce_table(sql, allowed_tables=allowed_tables)
    sql = _ensure_limit(sql, max_limit=1000)
    return sql