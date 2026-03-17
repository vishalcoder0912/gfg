"""
Google Gemini (AI Studio) integration.

Gemini is used for:
1) Dashboard planning
2) SQL generation for each chart intent
3) Executive insight generation
4) Follow-up interpretation

Backend still validates outputs (SQL safety, schema compliance) to avoid
hallucinations and unsafe queries.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from app.config import settings


def _require_api_key() -> str:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Add it to backend/.env (see .env.example).")
    return settings.GEMINI_API_KEY


def _client():
    import google.generativeai as genai

    genai.configure(api_key=_require_api_key())
    return genai


def _generate_with_retry(model, prompt: str, max_retries: int = 3) -> str:
    """Call model.generate_content with automatic retry on 429 rate-limit errors."""
    request_options = None
    try:
        from google.generativeai.types import RequestOptions

        request_options = RequestOptions(timeout=float(settings.GEMINI_TIMEOUT_SECONDS))
    except Exception:
        request_options = None

    for attempt in range(max_retries):
        try:
            resp = model.generate_content(prompt, request_options=request_options)
            return (resp.text or "").strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < max_retries - 1:
                wait = min(2 ** attempt * 15, 60)  # 15s, 30s, 60s
                time.sleep(wait)
                continue
            raise
    return ""



def generate_dashboard_plan(prompt: str, schema_context: str, prior_context: Optional[str] = None) -> Dict[str, Any]:
    genai = _client()
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    prior = prior_context or ""
    system = """
You are a BI analyst and product designer building an executive dashboard for a non-technical executive.
You MUST use only the columns provided in the schema context.
If the user asks for fields that do not exist, add a warning and avoid inventing fields.

Output must be STRICT JSON ONLY with this exact shape:
{
  "title": "...",
  "kpis": [{"label": "...", "intent": "..."}],
  "charts": [
    {"id": "chart_1", "title": "...", "intent": "...", "suggested_chart_type": "line|bar|area|pie|table", "sql": "SELECT ..."}
  ],
  "insight_goals": ["..."],
  "warnings": ["..."]
}

Rules:
- 1 to 4 charts max
- Each chart intent must be specific about metric + dimension + timeframe/filter if needed
- Provide STRICT SQLite SQL for each chart in the `sql` field. Use ONLY the given table and columns. Limit 1000. Use only standard SQLite.
- Do NOT include markdown fences, comments, or explanation text outside JSON.
""".strip()

    full_prompt = f"""
{system}

Schema context (JSON):
{schema_context}

Prior dashboard context (may be empty):
{prior}

User request:
{prompt}
""".strip()

    text = _generate_with_retry(model, full_prompt)
    return json.loads(text)

def generate_executive_insights(prompt: str, dashboard_results: Dict[str, Any]) -> List[str]:
    genai = _client()
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    ctx = json.dumps(dashboard_results, ensure_ascii=True)
    p = f"""
You are a business analyst writing executive insights.

User request:
{prompt}

Dashboard results context (JSON, derived from real query results):
{ctx}

Write 2-5 short, factual, business-friendly insights.
Rules:
- Use only numbers and facts present in the JSON context.
- If something is not supported, say it cannot be concluded from the data.
- Output must be a JSON array of strings only.
""".strip()

    text = _generate_with_retry(model, p)
    return json.loads(text)


def interpret_follow_up(prompt: str, prior_dashboard_context: str, schema_context: str) -> Dict[str, Any]:
    genai = _client()
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    p = f"""
You are refining an existing BI dashboard based on a follow-up instruction.

Schema context (JSON):
{schema_context}

Prior dashboard context (JSON):
{prior_dashboard_context}

Follow-up instruction:
{prompt}

Rules:
- Treat the follow-up as a refinement unless explicitly asking for a brand new dashboard.
- Infer filters, metric swaps, regrouping, top-N, and period comparisons.
- Output STRICT JSON ONLY with shape:
  {{"refined_prompt": "...", "notes": ["..."]}}
""".strip()

    text = _generate_with_retry(model, p)
    return json.loads(text)
