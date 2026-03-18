"""
Google Gemini service — Natural Language → SQL → Dashboard pipeline.

Key fixes vs the original:
  - Rich NL→SQL system prompts that include the actual column names so Gemini
    never invents columns that don't exist.
  - Strip markdown fences (```json ... ```) that Gemini wraps around JSON output.
  - Cache plan + insights (same question = same answer, 30-min TTL).
  - Do NOT cache follow-up (always session-dependent).
  - Surface expired/invalid key errors immediately instead of after 3 retries.
  - Retry only on 429 rate-limit, raise everything else immediately.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Simple in-memory response cache (30 min TTL)
# ─────────────────────────────────────────────
_CACHE_TTL  = 60 * 30   # 30 minutes
_CACHE_MAX  = 200

class _Entry:
    __slots__ = ("value", "born")
    def __init__(self, v: str): self.value = v; self.born = time.monotonic()
    def expired(self): return (time.monotonic() - self.born) > _CACHE_TTL

class _Cache:
    def __init__(self): self._d: Dict[str, _Entry] = {}; self.hits = self.misses = 0

    def get(self, k: str) -> Optional[str]:
        e = self._d.get(k)
        if not e: self.misses += 1; return None
        if e.expired(): del self._d[k]; self.misses += 1; return None
        self.hits += 1; return e.value

    def set(self, k: str, v: str):
        if len(self._d) >= _CACHE_MAX: del self._d[next(iter(self._d))]
        self._d[k] = _Entry(v)

    def clear(self) -> int: n = len(self._d); self._d.clear(); return n

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {"size": len(self._d), "max_size": _CACHE_MAX, "ttl_seconds": _CACHE_TTL,
                "hits": self.hits, "misses": self.misses,
                "hit_rate_pct": round(self.hits / total * 100, 1) if total else 0.0}

_cache = _Cache()


def _key(fn: str, *parts: str) -> str:
    return hashlib.sha256((fn + "|" + "|".join(p.strip().lower() for p in parts)).encode()).hexdigest()

def _stable(d: Any) -> str:
    return json.dumps(d, sort_keys=True, ensure_ascii=True)


# ─────────────────────────────────────────────
# Raw Gemini call
# ─────────────────────────────────────────────

def _require_key() -> str:
    k = settings.GEMINI_API_KEY
    if not k or not k.strip():
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Get a free key at https://aistudio.google.com and add it to backend/.env"
        )
    return k.strip()


def _get_model():
    import google.generativeai as genai
    genai.configure(api_key=_require_key())
    return genai.GenerativeModel((settings.GEMINI_MODEL or "gemini-3-flash-preview").strip())


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` markdown fences Gemini often adds."""
    if not text:
        raise ValueError("Gemini returned an empty response.")
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    return m.group(1).strip() if m else text.strip()


def _call_gemini(prompt: str, max_retries: int = 3) -> str:
    """Raw Gemini call — retries only on 429, surfaces key errors immediately."""
    model = _get_model()
    req_opts = None
    try:
        from google.generativeai.types import RequestOptions
        req_opts = RequestOptions(timeout=float(settings.GEMINI_TIMEOUT_SECONDS))
    except Exception:
        pass

    last: Exception = RuntimeError("Unknown")
    for attempt in range(max_retries):
        try:
            r = (model.generate_content(prompt, request_options=req_opts)
                 if req_opts else model.generate_content(prompt))
            t = (r.text or "").strip()
            if not t:
                raise ValueError("Gemini returned empty body.")
            return t
        except Exception as e:
            last = e
            s = str(e)
            if ("429" in s or "RESOURCE_EXHAUSTED" in s) and attempt < max_retries - 1:
                wait = min(2 ** attempt * 15, 60)
                logger.warning("Rate-limited — retrying in %ds", wait)
                time.sleep(wait)
                continue
            # Surface key errors immediately — no retries
            if "API_KEY_INVALID" in s or "API key expired" in s:
                raise ValueError(
                    "Gemini API key expired or invalid. "
                ) from e
            raise
    raise last


def _cached_call(fn: str, prompt: str, *key_parts: str) -> str:
    k = _key(fn, prompt, *key_parts)
    cached = _cache.get(k)
    if cached:
        logger.info("[%s] cache HIT", fn)
        return cached
    logger.info("[%s] calling Gemini", fn)
    result = _call_gemini(prompt)
    _cache.set(k, result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# System prompts
# ─────────────────────────────────────────────────────────────────────────────

_PLAN_SYS = """
You are an expert data analyst. Convert the user's plain-English question into a
dashboard plan with precise SQLite SQL queries.

COLUMN RULES — CRITICAL:
  - Use ONLY the exact column names listed in the schema below.
  - Never invent column names not in the schema.
  - Always double-quote column names: "column_name"
  - Always use the exact table name from the schema.

SQL RULES — CRITICAL (SQLite only):
  - No ILIKE, DATE_TRUNC, NOW(), ARRAY_AGG — these do not exist in SQLite.
  - Date grouping: strftime('%Y-%m', "date_col") AS month
  - Year only: CAST(strftime('%Y', "date_col") AS INTEGER) AS year
  - Always CAST text-stored numbers: CAST("col" AS REAL)
  - Always end with LIMIT 1000 or less.
  - NO SQL comments (-- or /* */).
  - No semicolons inside the sql field.

CHART TYPES:
  bar         → compare categories (top N, ranking, side-by-side)
  line        → trends over time
  area        → cumulative trends over time
  pie         → proportion/share (max 8 slices)
  stacked_bar → multiple metrics per category
  table       → raw rows, detailed breakdown

INTENT TRANSLATION GUIDE:
  "show me sales"           → bar: SUM(revenue) by category + line: monthly trend
  "which region is best"    → bar: SUM GROUP BY region ORDER BY SUM DESC
  "how has X trended"       → line: strftime month + SUM of X
  "top products"            → bar: top 10 products ORDER BY revenue DESC
  "compare regions"         → stacked_bar or side-by-side bar
  "breakdown / distribution"→ pie (≤8 categories) or bar
  "how are we doing"        → line trend + bar category breakdown

OUTPUT: strict JSON only. No markdown. No explanation text. No code fences.

{
  "title": "Dashboard title reflecting the user's question",
  "charts": [
    {
      "id": "chart_1",
      "title": "Concise chart title",
      "intent": "One sentence explaining what this chart shows",
      "suggested_chart_type": "bar|line|area|pie|stacked_bar|table",
      "sql": "SELECT ..."
    }
  ],
  "warnings": []
}
""".strip()


_INSIGHTS_SYS = """
You are a senior data analyst writing executive insights for a business leader.

Use ONLY numbers and facts that appear in the query results provided.
Never invent figures, percentages, or trends not visible in the data.
Write 3 to 5 short, plain-English, business-friendly insights.
Start each with the most important fact.
Output a JSON array of strings only. No markdown. No explanation.
""".strip()


_FOLLOWUP_SYS = """
You are refining an existing BI dashboard based on a follow-up instruction.

The user may say things like:
  "filter to East region only"    → add WHERE "region" = 'East'
  "show top 5 instead"            → change LIMIT or add RANK
  "break down by category"        → change GROUP BY
  "show as a table"               → change chart type to table
  "compare with profit"           → add second metric column
  "show monthly trend"            → switch to time-series line chart

RULES:
  - Treat as refinement unless user says "start over" or "new dashboard".
  - Use only columns listed in the schema.
  - Output strict JSON only:
    {"refined_prompt": "...", "notes": ["what changed and why"]}
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_dashboard_plan(
    prompt: str,
    schema_context: str,
    prior_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert a plain-English question into a dashboard plan with SQL queries.
    The schema_context includes the exact column names so Gemini never invents
    columns that don't exist.

    CACHED — same question on same schema returns the cached plan.
    """
    prior = (prior_context or "").strip()

    full = f"""{_PLAN_SYS}

━━━ DATASET SCHEMA (use ONLY these columns) ━━━
{schema_context}

━━━ PRIOR DASHBOARD CONTEXT (empty = first request) ━━━
{prior}

━━━ USER QUESTION ━━━
{prompt}

Output JSON only. No markdown. No explanation."""

    raw = _cached_call("plan", full, schema_context, prior)
    return json.loads(_strip_fences(raw))


def generate_executive_insights(
    prompt: str,
    dashboard_results: Dict[str, Any],
) -> List[str]:
    """
    Write plain-English insights from real query results.
    Only states facts that appear in the actual data — never invents numbers.

    CACHED — same results always produce the same insights.
    """
    results_str = _stable(dashboard_results)
    full = f"""{_INSIGHTS_SYS}

User question: {prompt}

Query results (ONLY use facts from here):
{results_str}

Output a JSON array of 3-5 insight strings. No markdown."""

    raw    = _cached_call("insights", full, results_str)
    result = json.loads(_strip_fences(raw))
    if isinstance(result, list):
        return [str(i) for i in result]
    if isinstance(result, dict) and "insights" in result:
        return [str(i) for i in result["insights"]]
    return [str(result)]


def interpret_follow_up(
    prompt: str,
    prior_dashboard_context: str,
    schema_context: str,
) -> Dict[str, Any]:
    """
    Interpret a follow-up instruction and return a refined prompt.

    NOT CACHED — always fresh because session context changes each call.
    """
    full = f"""{_FOLLOWUP_SYS}

━━━ SCHEMA ━━━
{schema_context}

━━━ CURRENT DASHBOARD ━━━
{prior_dashboard_context}

━━━ USER FOLLOW-UP ━━━
{prompt}

Output JSON: {{"refined_prompt": "...", "notes": ["..."]}}"""

    logger.info("[follow_up] calling Gemini (not cached)")
    raw = _call_gemini(full)
    return json.loads(_strip_fences(raw))


def get_cache_stats() -> Dict[str, Any]:
    return _cache.stats()

def clear_cache() -> int:
    return _cache.clear()