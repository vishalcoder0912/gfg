# Codex 2.0: Full Folder Analysis (gfg)

This document maps how files connect, why they exist, and which files are unused or framework-only. Scope is the entire `gfg` folder.

## Scope and Exclusions
The analysis focuses on source code and configuration. These paths are **not** treated as source dependencies:
- `ai-nl-analytics-dashboard/frontend/node_modules/**` (third-party packages)
- `.venv/**` (local Python env)
- `**/__pycache__/**`, `**/*.pyc` (bytecode)
- `**/*.log` (runtime logs)
- `**/*.db` (runtime databases)
- `**/*.csv` (data assets, not code)

## High-Level Architecture Map

```
Next.js Frontend (ai-nl-analytics-dashboard/frontend)
  app/page.tsx
    -> lib/api.ts (HTTP calls)
    -> backend API (FastAPI)

FastAPI Backend (ai-nl-analytics-dashboard/backend)
  app/main.py
    -> routes/*
      -> services/*
        -> database.py (SQLite)
        -> schemas.py (Pydantic contracts)
        -> utils/*
    -> services/gemini_service.py (LLM)
```

### Visual Graph (Mermaid)

```mermaid
flowchart LR
  subgraph Frontend[Next.js Frontend]
    page["app/page.tsx"]
    api["lib/api.ts"]
    types["lib/types.ts"]
    components["components/*"]
  end

  subgraph Backend[FastAPI Backend]
    main["app/main.py"]
    routes["app/routes/*"]
    services["app/services/*"]
    db["app/database.py"]
    schemas["app/schemas.py"]
    utils["app/utils/*"]
    gemini["app/services/gemini_service.py"]
  end

  page --> api --> routes
  page --> components
  api --> types
  routes --> services
  services --> db
  services --> schemas
  services --> utils
  services --> gemini
  main --> routes
  main --> services
```

Runtime flow:
1) UI calls `listDatasets`, `uploadCsv`, `generateDashboard`, `followUp`.
2) FastAPI routes call services.
3) Services read/write SQLite and optionally call Gemini for plan/insights.
4) Response JSON returns to frontend to render charts/tables.

## Backend Dependency Graph (Imports)

Entry point:
- `ai-nl-analytics-dashboard/backend/app/main.py`
  - imports `app.config`, `app.database`
  - imports routers: `app.routes.health`, `app.routes.upload`, `app.routes.dashboard`, `app.routes.chat`
  - calls `app.services.dataset_registry.ensure_demo_dataset_loaded`

Routers:
- `backend/app/routes/health.py`
  - no internal imports (simple health response)
- `backend/app/routes/upload.py`
  - imports `app.schemas`
  - imports `app.services.csv_service`
  - imports `app.services.dataset_registry`
- `backend/app/routes/dashboard.py`
  - imports `app.schemas`
  - imports `app.services.dashboard_engine`
- `backend/app/routes/chat.py`
  - imports `app.schemas`
  - imports `app.services.dashboard_engine`

Core services:
- `backend/app/services/dashboard_engine.py`
  - imports `app.schemas`
  - imports `app.services.dataset_registry`
  - imports `app.services.gemini_service`
  - imports `app.services.sql_validator`
  - imports `app.services.query_executor`
  - imports `app.services.chart_selector`
  - imports `app.services.session_service`
- `backend/app/services/gemini_service.py`
  - imports `app.config`
  - imports `google.generativeai` (runtime dependency)
- `backend/app/services/csv_service.py`
  - imports `app.config`
  - imports `app.schemas`
  - imports `app.services.dataset_registry`
  - uses `pandas`, `chardet`
- `backend/app/services/dataset_registry.py`
  - imports `app.database`
  - imports `app.schemas`
  - imports `app.services.schema_profiler`
  - imports `app.utils.column_sanitizer`
  - uses `pandas`
- `backend/app/services/query_executor.py`
  - imports `app.database`
- `backend/app/services/sql_validator.py`
  - imports `sqlparse`
- `backend/app/services/chart_selector.py`
  - uses `pandas` to pick chart type from data
- `backend/app/services/session_service.py`
  - no internal imports (in-memory session store)
- `backend/app/services/schema_profiler.py`
  - imports `app.schemas`
  - imports `app.utils.date_utils`

Database + schemas + utils:
- `backend/app/database.py` -> `app.config`
- `backend/app/config.py` -> env-based settings
- `backend/app/schemas.py` -> shared API contracts
- `backend/app/utils/column_sanitizer.py` -> identifier cleaning used by registry
- `backend/app/utils/date_utils.py` -> date detection used by schema profiler
- `backend/app/utils/response_helpers.py` -> not used by any module

## Frontend Dependency Graph (Imports)

App entry:
- `frontend/app/layout.tsx`
  - imports `./globals.css`
  - imports `next/font/google`

Main UI:
- `frontend/app/page.tsx`
  - imports `../components/layout/Sidebar`
  - imports `../components/layout/Navbar`
  - imports `../components/dashboard/FileUpload`
  - imports `../components/SqlPanel`
  - imports `../components/ChartRenderer`
  - imports `../components/DataTable`
  - imports `../lib/api`
  - imports `../lib/types`
  - uses `lucide-react`, `clsx`, React hooks

Components:
- `frontend/components/ChartRenderer.tsx`
  - imports `../lib/types`
  - imports `./DataTable`
  - uses `recharts`
- `frontend/components/DataTable.tsx`
  - no internal imports
- `frontend/components/SqlPanel.tsx`
  - imports `../lib/types`
- `frontend/components/dashboard/FileUpload.tsx`
  - imports `../../lib/api`
  - imports `../../lib/types`

API + types:
- `frontend/lib/api.ts` -> `frontend/lib/types`
- `frontend/lib/types.ts` -> pure type definitions

Framework files (Next.js conventions):
- `frontend/app/error.tsx`
- `frontend/app/global-error.tsx`
- `frontend/app/not-found.tsx`
These are used by Next.js via filename conventions, not explicit imports.

## File-by-File Purpose and Logic

Top-level:
- `package.json`: placeholder project manifest. Not used by backend/frontend runtime.

Backend:
- `backend/app/main.py`: FastAPI app creation, middleware setup, route registration, and demo dataset preload.
- `backend/app/config.py`: environment-driven settings for SQLite path, CORS, upload limits, and Gemini config.
- `backend/app/database.py`: SQLite connections, table setup, safe identifier quoting, schema inspection, preview fetch.
- `backend/app/schemas.py`: Pydantic models for request/response payloads.
- `backend/app/routes/health.py`: health check endpoint.
- `backend/app/routes/upload.py`: CSV upload and dataset metadata endpoints.
- `backend/app/routes/dashboard.py`: dashboard generation entrypoint.
- `backend/app/routes/chat.py`: follow-up refinement entrypoint.
- `backend/app/services/dashboard_engine.py`: orchestrates plan -> SQL -> query -> chart -> insights -> session.
- `backend/app/services/gemini_service.py`: Gemini API calls with retry and strict JSON responses.
- `backend/app/services/csv_service.py`: upload validation + CSV parse + register dataset.
- `backend/app/services/dataset_registry.py`: in-memory dataset registry + SQLite persistence; loads demo dataset.
- `backend/app/services/query_executor.py`: executes validated SELECT queries.
- `backend/app/services/sql_validator.py`: strict SQL safety validation and normalization.
- `backend/app/services/chart_selector.py`: deterministic chart type choice from query result shape.
- `backend/app/services/session_service.py`: in-memory session store for follow-ups.
- `backend/app/services/schema_profiler.py`: infers numeric/categorical/date columns and preview rows.
- `backend/app/utils/column_sanitizer.py`: cleans and dedupes column names.
- `backend/app/utils/date_utils.py`: detects datetime-like columns.
- `backend/app/utils/response_helpers.py`: helper for error payloads (unused).

Frontend:
- `frontend/app/layout.tsx`: global layout, fonts, and metadata.
- `frontend/app/page.tsx`: main UI, state, dataset selection, dashboard rendering, follow-up flow.
- `frontend/app/error.tsx`: per-route error UI.
- `frontend/app/global-error.tsx`: app-level error UI.
- `frontend/app/not-found.tsx`: 404 UI.
- `frontend/components/ChartRenderer.tsx`: render charts or table from `ChartSpec`.
- `frontend/components/DataTable.tsx`: generic table for row arrays.
- `frontend/components/SqlPanel.tsx`: collapsible SQL transparency panel.
- `frontend/components/dashboard/FileUpload.tsx`: CSV upload UI and interaction.
- `frontend/lib/api.ts`: API calls to backend endpoints.
- `frontend/lib/types.ts`: shared TS types matching backend schemas.

Config:
- `frontend/package.json`: frontend scripts and dependencies (Next.js, Recharts, etc).
- `backend/requirements.txt`: backend deps (FastAPI, pandas, sqlparse, Gemini).
- `frontend/next.config.js`, `frontend/tsconfig.json`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/next-env.d.ts`: build/tooling configs.

## Unused or Not Referenced by Code

Backend (unused modules):
- `backend/app/services/sql_guard.py`: never imported; superseded by `sql_validator.py`.
- `backend/app/services/csv_handler.py`: never imported; superseded by `csv_service.py`.
- `backend/app/utils/response_helpers.py`: never imported.

Backend data artifacts:
- `backend/data/app.db`: not referenced; actual path is `./data/app_data.db` via `config.py`.
- `backend/data/app_data.db`: runtime DB file, not source code.
- `backend/data/demo/demo_sales.csv`: data asset used by `dataset_registry` when present.

Frontend (unused components):
- `frontend/components/dashboard/ChartCard.tsx`: not imported anywhere.
- `frontend/components/FileDropzone.tsx`: not imported anywhere.
- `frontend/components/layout/Navbar.tsx`: imported in `app/page.tsx` but not rendered.
- `frontend/components/layout/Sidebar.tsx`: imported in `app/page.tsx` but not rendered.

Root-level data assets (not code):
- `ai-nl-analytics-dashboard/sample_sales_data.csv`: only used if backend runs with CWD at repo root; otherwise unused.
- `ai-nl-analytics-dashboard/demo_sales.csv`: not referenced by backend loader paths.
- `ai-nl-analytics-dashboard/sample_sales_data.csv` (and `demo_sales.csv`): data assets, not code dependencies.

Logs and bytecode:
- `backend/*.log`, `frontend/*.log`, `**/*.pyc`, `**/__pycache__/**`: runtime artifacts only.

## Notes on Cross-Project Coupling

Contract coupling:
- `backend/app/schemas.py` and `frontend/lib/types.ts` mirror each other. Changes to API fields require updates in both.

API routing:
- Frontend uses `NEXT_PUBLIC_API_URL` or defaults to `/api`. If there is no proxy, the backend must be reachable at that base.

Gemini dependency:
- `GEMINI_API_KEY` is required for plan and insight generation, but the backend has fallbacks for plan/insight failure.



ollama launch claude --model qwen3.5