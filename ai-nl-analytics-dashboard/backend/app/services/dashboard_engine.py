"""
Dashboard engine: Natural Language → SQL → Dashboard.

Every step has a fallback — a dashboard is ALWAYS returned even when
Gemini is unavailable or returns bad output.

Pipeline:
  Step 1: get plan from Gemini      → fallback: auto-build from column types
  Step 2: fill missing SQL          → fallback: auto-generate varied SQL
  Step 3: validate SQL              → fallback: replace with safe query
  Step 4: execute SQL               → fallback: bare SELECT *, then empty rows
  Step 5: generate insights         → fallback: derive from real chart numbers
"""

from __future__ import annotations

import json
import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple

from app.schemas import (
    ChartSpec, DashboardSpec, FollowUpResponse,
    GenerateDashboardResponse, SqlQuerySpec, SummaryCard,
)
from app.services.chart_selector import choose_chart
from app.services.dataset_registry import get_dataset_profile
from app.services.gemini_service import (
    generate_dashboard_plan, generate_executive_insights, interpret_follow_up,
)
from app.services.query_executor import execute_select
from app.services.session_service import create_session, get_session, update_session
from app.services.sql_validator import validate_and_normalize_sql

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Schema context builder
# ─────────────────────────────────────────────

def _schema_ctx(dataset_id: str) -> Tuple[Any, str]:
    """Build a rich schema context string for Gemini including real column names."""
    prof = get_dataset_profile(dataset_id)
    ctx = {
        "table_name": prof.table_name,
        "total_rows": prof.row_count,
        "columns": prof.columns,
        "numeric_columns": prof.numeric_columns,
        "categorical_columns": prof.categorical_columns,
        "date_columns": prof.date_columns,
        "sample_rows": prof.preview_rows[:5],
        "tip": (
            f'Use ONLY the column names listed above. '
            f'The table name is "{prof.table_name}". '
            'Always double-quote column names.'
        ),
    }
    return prof, json.dumps(ctx, ensure_ascii=True, indent=2)


# ─────────────────────────────────────────────
# Fallback plan (no Gemini required)
# ─────────────────────────────────────────────

def _fallback_plan(prof: Any) -> Dict[str, Any]:
    """Build a meaningful dashboard plan from column types alone."""
    t, nc, cc, dc = prof.table_name, prof.numeric_columns, prof.categorical_columns, prof.date_columns
    charts = []

    if cc and nc:
        charts.append({
            "id": "chart_1",
            "title": f"{nc[0].replace('_',' ').title()} by {cc[0].replace('_',' ').title()}",
            "intent": f"Total {nc[0]} grouped by {cc[0]}",
            "suggested_chart_type": "bar",
            "sql": (
                f'SELECT "{cc[0]}", ROUND(SUM(CAST("{nc[0]}" AS REAL)),2) AS total_{nc[0]} '
                f'FROM "{t}" GROUP BY "{cc[0]}" ORDER BY total_{nc[0]} DESC LIMIT 15'
            ),
        })

    if dc and nc:
        charts.append({
            "id": "chart_2",
            "title": f"{nc[0].replace('_',' ').title()} Over Time",
            "intent": f"Monthly trend of {nc[0]}",
            "suggested_chart_type": "line",
            "sql": (
                f"SELECT strftime('%Y-%m', \"{dc[0]}\") AS month, "
                f'ROUND(SUM(CAST("{nc[0]}" AS REAL)),2) AS total_{nc[0]} '
                f'FROM "{t}" GROUP BY month ORDER BY month ASC LIMIT 24'
            ),
        })

    if len(cc) >= 2 and nc:
        charts.append({
            "id": "chart_3",
            "title": f"Breakdown by {cc[1].replace('_',' ').title()}",
            "intent": f"Proportion of {nc[0]} by {cc[1]}",
            "suggested_chart_type": "pie",
            "sql": (
                f'SELECT "{cc[1]}", ROUND(SUM(CAST("{nc[0]}" AS REAL)),2) AS total_{nc[0]} '
                f'FROM "{t}" GROUP BY "{cc[1]}" ORDER BY total_{nc[0]} DESC LIMIT 8'
            ),
        })

    if len(nc) >= 2 and cc:
        charts.append({
            "id": "chart_4",
            "title": f"{nc[0].replace('_',' ').title()} vs {nc[1].replace('_',' ').title()}",
            "intent": f"Compare {nc[0]} and {nc[1]}",
            "suggested_chart_type": "stacked_bar",
            "sql": (
                f'SELECT "{cc[0]}", '
                f'ROUND(SUM(CAST("{nc[0]}" AS REAL)),2) AS total_{nc[0]}, '
                f'ROUND(SUM(CAST("{nc[1]}" AS REAL)),2) AS total_{nc[1]} '
                f'FROM "{t}" GROUP BY "{cc[0]}" ORDER BY total_{nc[0]} DESC LIMIT 15'
            ),
        })

    if not charts:
        charts.append({"id": "chart_1", "title": "Data Preview",
                       "intent": "Sample rows", "suggested_chart_type": "table",
                       "sql": f'SELECT * FROM "{t}" LIMIT 50'})

    return {
        "title": "Data Overview Dashboard", "charts": charts[:4],
    }


# ─────────────────────────────────────────────
# Fallback SQL per chart index
# ─────────────────────────────────────────────

def _fallback_sql(prof: Any, intent: str, idx: int) -> str:
    t, nc, cc, dc = prof.table_name, prof.numeric_columns, prof.categorical_columns, prof.date_columns
    low = intent.lower()
    if ("time" in low or "trend" in low or "month" in low) and dc and nc:
        return (
            f"SELECT strftime('%Y-%m', \"{dc[0]}\") AS month, "
            f'ROUND(SUM(CAST("{nc[0]}" AS REAL)),2) AS total '
            f'FROM "{t}" GROUP BY month ORDER BY month LIMIT 24'
        )
    if cc and nc:
        num = nc[min(idx, len(nc) - 1)]
        cat = cc[min(idx, len(cc) - 1)]
        return (
            f'SELECT "{cat}", ROUND(SUM(CAST("{num}" AS REAL)),2) AS total_{num} '
            f'FROM "{t}" GROUP BY "{cat}" ORDER BY total_{num} DESC LIMIT 20'
        )
    if nc:
        return f'SELECT "{nc[0]}" FROM "{t}" ORDER BY CAST("{nc[0]}" AS REAL) DESC LIMIT 100'
    return f'SELECT * FROM "{t}" LIMIT 50'


# ─────────────────────────────────────────────
# Plan validation
# ─────────────────────────────────────────────

def _validate_plan(plan: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    warnings: List[str] = []
    if not isinstance(plan, dict):
        raise ValueError("Plan is not a dict.")
    if isinstance(plan.get("warnings"), list):
        warnings.extend(str(w) for w in plan["warnings"])

    charts = plan.get("charts") or []
    if not isinstance(charts, list) or not charts:
        warnings.append("No charts returned — added table preview.")
        plan["charts"] = [{"id": "chart_1", "title": "Data Preview",
                           "intent": "Show sample rows", "suggested_chart_type": "table"}]

    if len(plan["charts"]) > 4:
        plan["charts"] = plan["charts"][:4]

    for i, c in enumerate(plan["charts"]):
        if not isinstance(c, dict):
            plan["charts"][i] = {"id": f"chart_{i+1}", "title": f"Chart {i+1}", "intent": ""}
            continue
        c.setdefault("id", f"chart_{i+1}")
        c.setdefault("title", f"Chart {i+1}")
        c.setdefault("intent", "Summarize dataset")

    return plan, warnings


# ─────────────────────────────────────────────
# Execute single chart (with nested fallbacks)
# ─────────────────────────────────────────────

def _exec_chart(
    chart_def: Dict[str, Any],
    idx: int,
    prof: Any,
    warnings: List[str],
) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    title  = str(chart_def.get("title",  f"Chart {idx+1}"))
    intent = str(chart_def.get("intent", ""))
    raw    = str(chart_def.get("sql",    "")).strip()

    # Step 1: fill missing SQL
    if not raw:
        raw = _fallback_sql(prof, intent, idx)

    safe = raw

    # Step 2: validate
    try:
        safe = validate_and_normalize_sql(raw, allowed_tables=[prof.table_name])
    except Exception as e:
        warnings.append(f"'{title}': SQL invalid ({e}) — using fallback query.")
        fallback = _fallback_sql(prof, intent, idx)
        try:
            safe = validate_and_normalize_sql(fallback, allowed_tables=[prof.table_name])
        except Exception:
            safe = f'SELECT * FROM "{prof.table_name}" LIMIT 50'

    # Step 3: execute
    try:
        cols, rows = execute_select(safe)
        return safe, cols, rows
    except Exception as e:
        warnings.append(f"'{title}': query failed ({e}).")

    # Step 4: last resort
    bare = f'SELECT * FROM "{prof.table_name}" LIMIT 50'
    try:
        cols, rows = execute_select(bare)
        return bare, cols, rows
    except Exception:
        return safe, [], []


# ─────────────────────────────────────────────
# Summary cards
# ─────────────────────────────────────────────

def _build_summary_cards(charts: List[ChartSpec], prof: Any) -> List[SummaryCard]:
    cards: List[SummaryCard] = []
    for ch in charts:
        if not ch.data or not ch.yKeys or ch.chartType == "table":
            continue
        y = ch.yKeys[0]
        vals = []
        for r in ch.data:
            try: vals.append(float(r[y]))
            except (TypeError, ValueError, KeyError): pass
        if vals:
            label = y.replace("_", " ").replace("total ", "").title()
            cards.append(SummaryCard(label=f"Total {label}", value=round(sum(vals), 2)))
            cards.append(SummaryCard(label=f"Peak {label}",  value=round(max(vals), 2)))
            cards.append(SummaryCard(label=f"Avg {label}",   value=round(sum(vals)/len(vals), 2)))
            break
    cards.append(SummaryCard(label="Total Rows", value=prof.row_count))
    return cards


# ─────────────────────────────────────────────
# Data-derived fallback insights
# ─────────────────────────────────────────────

def _fallback_insights(dashboard: DashboardSpec) -> List[str]:
    insights: List[str] = []
    for ch in dashboard.charts:
        if not ch.data or ch.chartType == "table" or not ch.yKeys:
            continue
        y = ch.yKeys[0]
        vals = []
        for r in ch.data:
            try: vals.append((str(r.get(ch.xKey or "", "")), float(r[y])))
            except (TypeError, ValueError, KeyError): pass
        if not vals:
            continue
        vals.sort(key=lambda x: x[1], reverse=True)
        total = sum(v for _, v in vals)
        top   = vals[0]
        label = y.replace("_", " ").replace("total ", "").title()
        insights.append(
            f"{top[0]} leads with {label.lower()} of {top[1]:,.2f}"
            + (f" ({top[1]/total*100:.1f}% of total)." if total > 0 else ".")
        )
        if len(vals) >= 2:
            bot = vals[-1]
            insights.append(f"{bot[0]} has the lowest {label.lower()} at {bot[1]:,.2f}.")
        if len(insights) >= 4:
            break
    if not insights:
        insights.append(
            "Dashboard ready. Use the chat below to filter, compare, or drill down."
        )
    return insights


# ─────────────────────────────────────────────
# Main public functions
# ─────────────────────────────────────────────

def generate_dashboard(
    dataset_id: str,
    prompt: str,
    prior_session: Optional[Any] = None,
) -> GenerateDashboardResponse:
    """Full NL → SQL → Dashboard pipeline with fallbacks at every step."""

    warnings: List[str] = []
    prof, schema_context = _schema_ctx(dataset_id)

    prior_context = ""
    if prior_session:
        prior_context = json.dumps({
            "original_prompt": prior_session.original_prompt,
            "last_dashboard":  prior_session.last_dashboard,
            "last_plan":       prior_session.last_plan,
        }, ensure_ascii=True, indent=2)

    # ── Step 1: Plan ──────────────────────────────────────────────────────────
    try:
        plan = generate_dashboard_plan(
            prompt=prompt, schema_context=schema_context, prior_context=prior_context
        )
    except Exception as e:
        logger.warning("generate_dashboard_plan failed, using fallback: %s", e)
        plan = _fallback_plan(prof)

    try:
        plan, pw = _validate_plan(plan)
        warnings.extend(pw)
    except Exception as e:
        warnings.append(f"Plan validation failed ({e}).")
        plan = _fallback_plan(prof)
        plan, _ = _validate_plan(plan)

    title = str(plan.get("title") or "Data Analysis Dashboard")

    # ── Steps 2–4: SQL per chart ──────────────────────────────────────────────
    sql_specs: List[SqlQuerySpec] = []
    charts:    List[ChartSpec]    = []

    for i, cdef in enumerate(plan.get("charts", [])[:4]):
        cid     = str(cdef.get("id",     f"chart_{i+1}"))
        ctitle  = str(cdef.get("title",  f"Chart {i+1}"))
        cintent = str(cdef.get("intent", ""))
        user_chart_type = cdef.get("chartType") or cdef.get("suggested_chart_type")

        safe, cols, rows = _exec_chart(cdef, i, prof, warnings)
        sql_specs.append(SqlQuerySpec(id=cid, title=ctitle, intent=cintent, sql=safe))

        chart_type, x_key, y_keys = choose_chart(rows)
        chart_type = user_chart_type or chart_type
        charts.append(ChartSpec(
            id=cid, title=ctitle, chartType=chart_type if chart_type else "table", # type: ignore
            xKey=x_key, yKeys=y_keys, data=rows, columns=cols,
        ))

    dashboard = DashboardSpec(
        title=title,
        summary_cards=_build_summary_cards(charts, prof),
        charts=charts,
        insights=[],
        sql_queries=sql_specs,
        message=None,
    )

    if all(not ch.data for ch in dashboard.charts):
        dashboard.message = (
            f"No data returned. Try rephrasing — "
            f"available columns: {', '.join(prof.columns)}"
        )

    # ── Step 5: Insights ──────────────────────────────────────────────────────
    try:
        rctx = {
            "summary_cards": [c.model_dump() for c in dashboard.summary_cards],
            "charts": [
                {"id": ch.id, "title": ch.title, "chartType": ch.chartType,
                 "xKey": ch.xKey, "yKeys": ch.yKeys, "sample": ch.data[:15]}
                for ch in dashboard.charts
            ],
        }
        dashboard.insights = generate_executive_insights(prompt=prompt, dashboard_results=rctx)
    except Exception as e:
        logger.warning("generate_executive_insights failed, using fallback: %s", e)
        dashboard.insights = _fallback_insights(dashboard)

    # ── Session ───────────────────────────────────────────────────────────────
    if prior_session:
        session_id = prior_session.session_id
        update_session(session_id, dashboard=dashboard.model_dump(), plan=plan,
                       sql_queries=[s.model_dump() for s in sql_specs])
    else:
        session_id = create_session(
            dataset_id=dataset_id, original_prompt=prompt,
            dashboard=dashboard.model_dump(), plan=plan,
            sql_queries=[s.model_dump() for s in sql_specs],
        )

    return GenerateDashboardResponse(
        dashboard=dashboard, session_id=session_id, warnings=warnings
    )


def follow_up(session_id: str, prompt: str) -> FollowUpResponse:
    """Refine an existing dashboard based on a follow-up chat message."""
    session = get_session(session_id)
    _, schema_context = _schema_ctx(session.dataset_id)
    prior_ctx = json.dumps(session.last_dashboard, ensure_ascii=True, indent=2)

    refined   = prompt
    warnings: List[str] = []

    try:
        interp  = interpret_follow_up(
            prompt=prompt, prior_dashboard_context=prior_ctx,
            schema_context=schema_context,
        )
        refined = str(interp.get("refined_prompt") or prompt)
        for n in (interp.get("notes") or [])[:5]:
            warnings.append(str(n))
    except Exception as e:
        warnings.append(f"Could not interpret follow-up ({e}) — applying directly.")

    out = generate_dashboard(
        dataset_id=session.dataset_id, prompt=refined, prior_session=session
    )
    return FollowUpResponse(dashboard=out.dashboard, warnings=warnings + out.warnings)