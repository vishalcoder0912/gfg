"""
Google Gemini service — single-call dashboard pipeline.

KEY CHANGES vs original:
─────────────────────────────────────────────────────────────────────────────
PROBLEM: The original code made 2–3 separate Gemini API calls per dashboard:
  1. generate_dashboard_plan()    → plan + SQL
  2. generate_executive_insights() → insights
  3. interpret_follow_up()        → follow-up interpretation
  This caused "429 Too Many Requests" on the free tier (15 RPM limit).

FIX: Collapse to ONE call per user action:
  • generate_full_dashboard() replaces calls 1+2 → plan + SQL + insights combined
  • interpret_follow_up() still 1 call (unavoidable — needs prior context)
  • Follow-up then calls generate_full_dashboard() → total 2 calls for refinement
    (down from 3)

RATE LIMITING:
  • Threading lock ensures calls are serialized (no concurrent burst)
  • Configurable minimum interval between calls (GEMINI_MIN_CALL_INTERVAL_SECONDS)
  • Exponential backoff only on 429, immediate raise on key errors

CACHING:
  • 30-minute LRU cache for identical prompts (same question on same schema)
  • Follow-up NOT cached (always session-specific)

MODEL:
  • Default: gemini-2.0-flash — best for free-tier SQL generation
  • Set GEMINI_MODEL= in backend/.env to override
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import threading
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Simple in-memory response cache (30 min TTL)
# ─────────────────────────────────────────────────────────────────────────────
_CACHE_TTL = 60 * 30   # 30 minutes
_CACHE_MAX = 200


class _Entry:
    __slots__ = ("value", "born")

    def __init__(self, v: str):
        self.value = v
        self.born = time.monotonic()

    def expired(self) -> bool:
        return (time.monotonic() - self.born) > _CACHE_TTL


class _Cache:
    def __init__(self):
        self._d: Dict[str, _Entry] = {}
        self.hits = self.misses = 0

    def get(self, k: str) -> Optional[str]:
        e = self._d.get(k)
        if not e:
            self.misses += 1
            return None
        if e.expired():
            del self._d[k]
            self.misses += 1
            return None
        self.hits += 1
        return e.value

    def set(self, k: str, v: str) -> None:
        if len(self._d) >= _CACHE_MAX:
            del self._d[next(iter(self._d))]
        self._d[k] = _Entry(v)

    def clear(self) -> int:
        n = len(self._d)
        self._d.clear()
        return n

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "size": len(self._d),
            "max_size": _CACHE_MAX,
            "ttl_seconds": _CACHE_TTL,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(self.hits / total * 100, 1) if total else 0.0,
        }


_cache = _Cache()

# ─────────────────────────────────────────────────────────────────────────────
# Rate-limit lock: serializes Gemini calls to avoid 429 bursts
# ─────────────────────────────────────────────────────────────────────────────
_rate_lock = threading.Lock()
_last_call_time: float = 0.0


def _wait_for_rate_limit() -> None:
    """
    Enforce a minimum interval between Gemini API calls.
    Controlled by GEMINI_MIN_CALL_INTERVAL_SECONDS (default 4s → safe for 15 RPM).
    Set to 0 in .env to disable throttling (e.g. if you have a paid plan).
    """
    global _last_call_time
    min_interval = float(settings.GEMINI_MIN_CALL_INTERVAL_SECONDS) # type: ignore
    if min_interval <= 0:
        return

    with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_call_time
        if elapsed < min_interval:
            sleep_for = min_interval - elapsed
            logger.debug("Rate-limit throttle: sleeping %.1fs", sleep_for)
            time.sleep(sleep_for)
        _last_call_time = time.monotonic()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _key(fn: str, *parts: str) -> str:
    return hashlib.sha256(
        (fn + "|" + "|".join(p.strip().lower() for p in parts)).encode()
    ).hexdigest()


def _stable(d: Any) -> str:
    return json.dumps(d, sort_keys=True, ensure_ascii=True)


def _strip_fences(text: str) -> str:
    """Remove ```json … ``` or ``` … ``` fences Gemini often wraps around JSON."""
    if not text:
        raise ValueError("Gemini returned an empty response.")
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    return m.group(1).strip() if m else text.strip()


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
    model_name = (settings.GEMINI_MODEL or "gemini-2.0-flash").strip()
    return genai.GenerativeModel(model_name)


# ─────────────────────────────────────────────────────────────────────────────
# Core Gemini call — with rate-limit throttle + 429 retry
# ─────────────────────────────────────────────────────────────────────────────

def _call_gemini(prompt: str, max_retries: int = 3) -> str:
    """
    Make one Gemini call.
    - Waits for the rate-limit window before calling.
    - Retries only on 429/RESOURCE_EXHAUSTED.
    - Raises immediately on key errors or empty responses.
    """
    _wait_for_rate_limit()

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
            r = (
                model.generate_content(prompt, request_options=req_opts)
                if req_opts
                else model.generate_content(prompt)
            )
            t = (r.text or "").strip()
            if not t:
                raise ValueError("Gemini returned empty body.")
            logger.info("Gemini call succeeded (attempt %d)", attempt + 1)
            return t
        except Exception as e:
            last = e
            s = str(e)

            # Surface key errors immediately — no retries
            if "API_KEY_INVALID" in s or "API key expired" in s:
                raise ValueError(
                    "Gemini API key is expired or invalid. "
                    "Visit https://aistudio.google.com to refresh it."
                ) from e

            # Retry on rate-limit errors with exponential back-off
            if ("429" in s or "RESOURCE_EXHAUSTED" in s) and attempt < max_retries - 1:
                wait = min(2 ** attempt * 15, 60)
                logger.warning(
                    "Gemini 429 rate-limited (attempt %d/%d) — retrying in %ds",
                    attempt + 1, max_retries, wait,
                )
                time.sleep(wait)
                continue

            raise

    raise last


def _cached_call(cache_key_prefix: str, prompt: str, *extra_key_parts: str) -> str:
    k = _key(cache_key_prefix, prompt, *extra_key_parts)
    cached = _cache.get(k)
    if cached:
        logger.info("[%s] cache HIT — skipping Gemini call", cache_key_prefix)
        return cached
    logger.info("[%s] cache MISS — calling Gemini", cache_key_prefix)
    result = _call_gemini(prompt)
    _cache.set(k, result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# System prompts
# ─────────────────────────────────────────────────────────────────────────────

_COMBINED_SYS = """
You are a senior data analyst. Your job is to turn a plain-English business question into a
complete dashboard plan — including SQLite SQL queries AND executive insights — in a SINGLE
JSON response.

════════════════════════════════════════════════
COLUMN RULES (CRITICAL — follow exactly):
════════════════════════════════════════════════
  • Use ONLY the exact column names listed in the schema below.
  • NEVER invent column names not in the schema.
  • Always double-quote column names: "column_name"
  • Always use the exact table name from the schema.

════════════════════════════════════════════════
SQL RULES (SQLite only — CRITICAL):
════════════════════════════════════════════════
  • No ILIKE, DATE_TRUNC, NOW(), ARRAY_AGG — these do NOT exist in SQLite.
  • Date grouping: strftime('%Y-%m', "date_col") AS month
  • Year only:    CAST(strftime('%Y', "date_col") AS INTEGER) AS year
  • Cast numbers: CAST("col" AS REAL) for text-stored numbers.
  • Always end with LIMIT 500 or less.
  • NO SQL comments (-- or /* */).
  • No semicolons inside the sql field.

════════════════════════════════════════════════
CHART TYPE GUIDE:
════════════════════════════════════════════════
  bar         → compare categories (top N, ranking)
  line        → trends over time
  area        → cumulative trends over time
  pie         → proportions / share (max 8 slices)
  stacked_bar → multiple metrics per category
  table       → raw rows, detailed breakdowns

════════════════════════════════════════════════
INSIGHTS RULES:
════════════════════════════════════════════════
  • Write 3–5 short plain-English executive insights.
  • Base them ONLY on what the SQL queries could realistically return.
  • Do NOT invent specific numbers — describe the expected pattern instead.
  • Each insight must start with the most important finding.
  • Keep each insight to 1–2 sentences.

════════════════════════════════════════════════
OUTPUT — strict JSON, no markdown, no explanation:
════════════════════════════════════════════════
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
  "insights": [
    "First key finding from the data.",
    "Second finding.",
    "Third finding."
  ],
  "warnings": []
}

Return 1 to 4 charts. Return exactly 3 to 5 insight strings.
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
  • Treat as refinement unless user says "start over" or "new dashboard".
  • Use only columns listed in the schema — NEVER invent column names.
  • Output strict JSON only (no markdown):
    {"refined_prompt": "...", "notes": ["what changed and why"]}
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_full_dashboard(
    prompt: str,
    schema_context: str,
    prior_context: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    ONE Gemini call → complete dashboard (plan + SQL per chart + insights).

    Previously this required two separate calls (plan call + insights call).
    Now everything is returned in a single JSON response, cutting API usage in half.

    Returns:
        (plan_dict, insights_list)

    CACHED — same question on same schema returns cached result immediately.
    """
    prior = (prior_context or "").strip()

    full_prompt = f"""{_COMBINED_SYS}

━━━ DATASET SCHEMA (use ONLY these columns) ━━━
{schema_context}

━━━ PRIOR DASHBOARD CONTEXT (empty = first request) ━━━
{prior if prior else "(none — this is a fresh request)"}

━━━ USER QUESTION ━━━
{prompt}

Output JSON only. No markdown. No explanation. No code fences."""

    raw = _cached_call("full_dashboard", full_prompt, schema_context, prior)
    parsed = json.loads(_strip_fences(raw))

    # Extract insights from the combined response
    insights: List[str] = []
    if isinstance(parsed.get("insights"), list):
        insights = [str(i) for i in parsed["insights"] if str(i).strip()]

    # Remove insights from the plan dict so dashboard_engine treats it normally
    plan = {k: v for k, v in parsed.items() if k != "insights"}

    return plan, insights


def interpret_follow_up(
    prompt: str,
    prior_dashboard_context: str,
    schema_context: str,
) -> Dict[str, Any]:
    """
    Interpret a follow-up instruction and return a refined prompt.

    NOT CACHED — always fresh because session context changes each call.
    This is 1 of the 2 total Gemini calls made during a follow-up flow
    (the other is generate_full_dashboard with the refined prompt).
    """
    full_prompt = f"""{_FOLLOWUP_SYS}

━━━ SCHEMA ━━━
{schema_context}

━━━ CURRENT DASHBOARD ━━━
{prior_dashboard_context}

━━━ USER FOLLOW-UP ━━━
{prompt}

Output JSON only: {{"refined_prompt": "...", "notes": ["..."]}}"""

    logger.info("[follow_up] calling Gemini (not cached)")
    raw = _call_gemini(full_prompt)
    return json.loads(_strip_fences(raw))


# ─────────────────────────────────────────────────────────────────────────────
# Cache admin
# ─────────────────────────────────────────────────────────────────────────────

def get_cache_stats() -> Dict[str, Any]:
    return _cache.stats()


def clear_cache() -> int:
    return _cache.clear()