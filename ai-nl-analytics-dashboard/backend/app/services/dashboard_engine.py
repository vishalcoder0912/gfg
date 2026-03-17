"""
Dashboard engine: the core pipeline from prompt -> dashboard JSON.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from app.schemas import (
    DashboardSpec,
    ChartSpec,
    SummaryCard,
    SqlQuerySpec,
    GenerateDashboardResponse,
    FollowUpResponse,
)
from app.services.dataset_registry import get_dataset_profile
from app.services.gemini_service import (
    generate_dashboard_plan,
    generate_executive_insights,
    interpret_follow_up,
)
from app.services.sql_validator import validate_and_normalize_sql
from app.services.query_executor import execute_select
from app.services.chart_selector import choose_chart
from app.services.session_service import create_session, get_session, update_session


def _schema_context(dataset_id: str) -> str:
    prof = get_dataset_profile(dataset_id)
    ctx = {
        "dataset_id": prof.dataset_id,
        "table_name": prof.table_name,
        "columns": prof.columns,
        "numeric_columns": prof.numeric_columns,
        "categorical_columns": prof.categorical_columns,
        "date_columns": prof.date_columns,
        "sample_rows": prof.preview_rows[:5],
    }
    return json.dumps(ctx, ensure_ascii=True, indent=2)


def _prior_context_for_llm(session_state: Any) -> str:
    if not session_state:
        return ""
    return json.dumps(
        {
            "original_prompt": session_state.original_prompt,
            "last_dashboard": session_state.last_dashboard,
            "last_plan": session_state.last_plan,
        },
        ensure_ascii=True,
        indent=2,
    )


def _validate_plan(plan: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    warnings: List[str] = []
    if not isinstance(plan, dict):
        raise ValueError("Invalid dashboard plan returned by Gemini.")
    if isinstance(plan.get("warnings"), list):
        warnings.extend([str(w) for w in plan["warnings"]])

    charts = plan.get("charts") or []
    if not isinstance(charts, list) or len(charts) == 0:
        warnings.append("Planner returned no charts. Falling back to a simple table preview.")
        plan["charts"] = [
            {"id": "chart_1", "title": "Dataset preview", "intent": "Show a sample of rows", "suggested_chart_type": "table"}
        ]

    if len(plan["charts"]) > 4:
        warnings.append("Planner returned more than 4 charts; truncating to 4 for clarity.")
        plan["charts"] = plan["charts"][:4]

    for i, c in enumerate(plan["charts"]):
        if not isinstance(c, dict):
            continue
        if "id" not in c:
            c["id"] = f"chart_{i+1}"
        if "title" not in c:
            c["title"] = f"Chart {i+1}"
        if "intent" not in c:
            c["intent"] = "Summarize the dataset"

    return plan, warnings


def _build_summary_cards(dashboard_charts: List[ChartSpec]) -> List[SummaryCard]:
    cards: List[SummaryCard] = []
    for ch in dashboard_charts:
        if not ch.data:
            continue
        if ch.yKeys and len(ch.yKeys) == 1:
            y = ch.yKeys[0]
            vals = [r.get(y) for r in ch.data if isinstance(r.get(y), (int, float))]
            if vals:
                cards.append(SummaryCard(label=f"Total {y}", value=round(float(sum(vals)), 2)))
                cards.append(SummaryCard(label=f"Max {y}", value=round(float(max(vals)), 2)))
                break
    return cards


def _fallback_insights(dashboard: DashboardSpec) -> List[str]:
    if dashboard.message:
        return [dashboard.message]
    if not dashboard.charts:
        return ["No charts could be generated from this request."]
    if all(not c.data for c in dashboard.charts):
        return ["No results returned. Try a broader prompt or remove filters."]
    return ["Dashboard generated. Use follow-ups to refine filters, metrics, and breakdowns."]


def generate_dashboard(dataset_id: str, prompt: str, prior_session: Optional[Any]) -> GenerateDashboardResponse:
    prof = get_dataset_profile(dataset_id)
    schema_context = _schema_context(dataset_id)
    prior_context = _prior_context_for_llm(prior_session)

    warnings: List[str] = []

    try:
        plan = generate_dashboard_plan(prompt=prompt, schema_context=schema_context, prior_context=prior_context)
    except Exception as e:
        plan = {
            "title": "Executive Dashboard",
            "kpis": [],
            "charts": [
                {"id": "chart_1", "title": "Metric by category", "intent": "Summarize a main numeric metric by a main category", "suggested_chart_type": "bar"},
                {"id": "chart_2", "title": "Trend over time", "intent": "Show the main numeric metric over time if a date column exists", "suggested_chart_type": "line"},
            ],
            "insight_goals": ["Highlight top performers and trends."],
            "warnings": [f"Gemini planning unavailable: {e}"],
        }
        warnings.append("Gemini API not configured or returned invalid JSON; used a safe fallback plan.")

    plan, plan_warnings = _validate_plan(plan)
    warnings.extend(plan_warnings)

    title = str(plan.get("title") or "Executive Dashboard")

    sql_specs: List[SqlQuerySpec] = []
    charts: List[ChartSpec] = []

    for c in plan.get("charts", [])[:4]:
        chart_id = str(c.get("id"))
        chart_title = str(c.get("title"))
        chart_intent = str(c.get("intent"))

        raw_sql = ""
        safe_sql = ""
        cols: List[str] = []
        rows: List[Dict[str, Any]] = []

        try:
            raw_sql = str(c.get("sql", ""))
            safe_sql = validate_and_normalize_sql(raw_sql, allowed_tables=[prof.table_name])
            cols, rows = execute_select(safe_sql)
        except Exception as e:
            warnings.append(f"{chart_title}: {e}")

        sql_specs.append(SqlQuerySpec(id=chart_id, title=chart_title, intent=chart_intent, sql=safe_sql or raw_sql or ""))

        chart_type, x_key, y_keys = choose_chart(rows)
        charts.append(
            ChartSpec(
                id=chart_id,
                title=chart_title,
                chartType=chart_type,
                xKey=x_key,
                yKeys=y_keys,
                data=rows,
                columns=cols,
            )
        )

    dashboard = DashboardSpec(
        title=title,
        summary_cards=_build_summary_cards(charts),
        charts=charts,
        insights=[],
        sql_queries=sql_specs,
        message=None,
    )

    if all((not ch.data) for ch in dashboard.charts):
        dashboard.message = (
            "I can't answer that from the available data without inventing fields or numbers. "
            "Try referencing existing columns."
        )
        warnings.append(f"Available columns: {', '.join(prof.columns)}")

    try:
        results_ctx = {
            "summary_cards": [c.model_dump() for c in dashboard.summary_cards],
            "charts": [
                {
                    "id": ch.id,
                    "title": ch.title,
                    "chartType": ch.chartType,
                    "xKey": ch.xKey,
                    "yKeys": ch.yKeys,
                    "sample": ch.data[:10],
                }
                for ch in dashboard.charts
            ],
        }
        dashboard.insights = generate_executive_insights(prompt=prompt, dashboard_results=results_ctx)
    except Exception:
        dashboard.insights = _fallback_insights(dashboard)

    if prior_session:
        session_id = prior_session.session_id
        update_session(session_id, dashboard=dashboard.model_dump(), plan=plan, sql_queries=[s.model_dump() for s in sql_specs])
    else:
        session_id = create_session(
            dataset_id=dataset_id,
            original_prompt=prompt,
            dashboard=dashboard.model_dump(),
            plan=plan,
            sql_queries=[s.model_dump() for s in sql_specs],
        )

    return GenerateDashboardResponse(dashboard=dashboard, session_id=session_id, warnings=warnings)


def follow_up(session_id: str, prompt: str) -> FollowUpResponse:
    session = get_session(session_id)
    schema_context = _schema_context(session.dataset_id)
    prior_ctx = json.dumps(session.last_dashboard, ensure_ascii=True, indent=2)

    refined_prompt = prompt
    warnings: List[str] = []

    try:
        interp = interpret_follow_up(prompt=prompt, prior_dashboard_context=prior_ctx, schema_context=schema_context)
        refined_prompt = str(interp.get("refined_prompt") or prompt)
        for n in (interp.get("notes") or [])[:5]:
            warnings.append(str(n))
    except Exception as e:
        warnings.append(f"Follow-up interpretation fallback: {e}")

    out = generate_dashboard(dataset_id=session.dataset_id, prompt=refined_prompt, prior_session=session)
    return FollowUpResponse(dashboard=out.dashboard, warnings=warnings + out.warnings)

