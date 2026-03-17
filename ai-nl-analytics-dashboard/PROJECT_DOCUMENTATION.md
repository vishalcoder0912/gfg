# Project Documentation — Conversational AI BI Dashboards

Hackathon prototype that lets non-technical users create interactive, multi-chart business dashboards from plain-English prompts.

## Table of contents
- [Overview](#overview)
- [Key features](#key-features)
- [System architecture](#system-architecture)
- [Data + storage](#data--storage)
- [Backend (FastAPI)](#backend-fastapi)
- [Frontend (Next.js)](#frontend-nextjs)
- [Environment variables](#environment-variables)
- [Setup (local)](#setup-local)
- [Usage (demo flow)](#usage-demo-flow)
- [Safety + reliability](#safety--reliability)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)

## Overview
This project converts a natural-language request (e.g., “Build an executive dashboard for sales performance”) into a dashboard spec containing:
- KPI summary cards
- 1–4 charts (bar/line/area/pie/table)
- Executive-friendly insights
- Transparent SQL queries used to compute results

It ships with a built-in demo dataset so the app is usable immediately.

## Key features
- Demo dataset auto-loaded on backend startup (`demo_sales`)
- CSV upload with validation (type, size cap) and encoding detection
- Schema profiling (numeric/categorical/date detection + preview rows)
- LLM-based dashboard planning + SQL generation (Gemini)
- Mandatory SQL safety validation before execution
- Deterministic chart selection based on returned data (for trust/consistency)
- Follow-up refinement with session memory (`/follow-up`)
- SQL panel and raw table preview for transparency

## System architecture
High-level components:
- **Frontend**: Next.js (App Router) UI that uploads CSVs, collects prompts, and renders charts/KPIs/insights.
- **Backend**: FastAPI API that ingests data into SQLite, calls Gemini, validates/executes SQL, and returns a `DashboardSpec`.
- **Database**: SQLite file used for persisted datasets + metadata.

Text pipeline (request → dashboard):
1. User selects a dataset (demo or uploaded) and submits a prompt.
2. Backend builds a schema context from the dataset profile.
3. Gemini returns a JSON “dashboard plan” containing chart intents + SQLite SQL per chart.
4. Backend validates and normalizes each SQL statement (SELECT/WITH only, table restricted, LIMIT enforced).
5. Backend executes validated SQL against SQLite (read-only connection).
6. Backend selects chart types deterministically from actual results.
7. Backend asks Gemini for executive insights based only on real results context.
8. Backend returns a `DashboardSpec` + warnings + session id.
9. Follow-ups refine the dashboard using prior dashboard context.

## Data + storage
SQLite is used for:
- **Dataset tables**: one table per uploaded dataset (sanitized name + timestamp) plus `demo_sales`.
- **Metadata**: `datasets_meta` table (dataset id → table name, column lists, preview rows, etc.).

Defaults:
- Backend DB path: `backend/data/app_data.db` (configurable via `APP_DB_PATH`)
- Upload cap: `50MB` (configurable via `APP_MAX_UPLOAD_BYTES`)

## Backend (FastAPI)
Location: `backend/`

### Key modules
- `backend/app/main.py`: app factory, middleware, and router registration.
- `backend/app/config.py`: env-driven settings (DB path, CORS, upload cap, Gemini config).
- `backend/app/database.py`: SQLite helpers + metadata table creation.
- `backend/app/services/dataset_registry.py`: dataset registry + demo dataset load + persistence to metadata.
- `backend/app/services/dashboard_engine.py`: core “prompt → dashboard spec” pipeline + follow-up handling.
- `backend/app/services/gemini_service.py`: Gemini calls (plan, insights, follow-up interpretation) with retry on 429s.
- `backend/app/services/sql_validator.py`: mandatory SQL validator/normalizer.
- `backend/app/services/query_executor.py`: executes validated SELECT queries using read-only SQLite connection.
- `backend/app/services/chart_selector.py`: deterministic chart selection from returned rows.
- `backend/app/schemas.py`: Pydantic API contracts (request/response models).

### API endpoints
- `GET /health`
  - Returns `{ "status": "ok" }`
- `POST /upload-csv`
  - Multipart form field: `file` (`.csv` only)
  - Returns `DatasetProfile` (dataset id, table name, detected schema, preview rows)
- `GET /datasets`
  - Returns a list of registered datasets (includes demo dataset if available)
- `GET /dataset/{dataset_id}/schema`
  - Returns SQLite column types for a dataset table
- `GET /dataset/{dataset_id}/preview?limit=10`
  - Returns a few rows from the dataset table
- `POST /generate-dashboard`
  - Body: `{ "dataset_id": "...", "prompt": "..." }`
  - Returns: `{ dashboard: DashboardSpec, session_id: string, warnings: string[] }`
- `POST /follow-up`
  - Body: `{ "session_id": "...", "prompt": "..." }`
  - Returns: `{ dashboard: DashboardSpec, warnings: string[] }`

### Session behavior
Follow-up sessions are kept **in memory** (`backend/app/services/session_service.py`). If the backend restarts, previous `session_id`s will no longer be valid.

## Frontend (Next.js)
Location: `frontend/`

### Key modules
- `frontend/app/page.tsx`: main UI (dataset selection, upload, prompt, dashboard render, follow-up).
- `frontend/lib/api.ts`: API client for dataset list/upload/dashboard generation/follow-up.
- `frontend/lib/types.ts`: shared TypeScript types matching backend schemas.
- `frontend/components/ChartRenderer.tsx`: renders charts using Recharts.
- `frontend/components/SqlPanel.tsx`: shows SQL transparency panel.
- `frontend/components/DataTable.tsx`: renders raw data table.
- `frontend/components/dashboard/FileUpload.tsx`: CSV upload UI.

### Backend API proxy (recommended)
`frontend/next.config.js` rewrites same-origin `/api/*` requests to the backend URL (default `http://localhost:8000`), so the browser can call the API without CORS issues in local dev.

## Environment variables

### Backend (`backend/.env`)
From `backend/.env.example`:
- `APP_DB_PATH` (default: `./data/app_data.db`)
- `APP_MAX_UPLOAD_BYTES` (default: `52428800`)
- `APP_CORS_ORIGINS` (comma-separated dev origins)
- `GEMINI_API_KEY` (required for LLM planning + insights)
- `GEMINI_MODEL` (default in code: `gemini-3.0-flash`)
- `GEMINI_TIMEOUT_SECONDS` (default in code: `15`)

### Frontend (`frontend/.env.local`)
From `frontend/.env.example`:
- `NEXT_PUBLIC_API_URL` (default: `/api`)
- `API_URL` (default: `http://localhost:8000` for Next.js rewrites)
- `NEXT_PUBLIC_MAX_UPLOAD_BYTES` (optional UI-side cap; keep aligned with backend)

## Setup (local)

### Requirements
- Python **3.10+**
- Node.js **20 LTS** (recommended) or **18 LTS**

### Backend
From `backend/`:
```bash
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt    # Windows
# or: source .venv/bin/activate && pip install -r requirements.txt
```

Create env:
- Copy `backend/.env.example` → `backend/.env`
- Set `GEMINI_API_KEY` (optional: if missing, backend uses a safe fallback plan but will be less accurate)

Run:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
From `frontend/`:
```bash
npm install
```

Create env:
- Copy `frontend/.env.example` → `frontend/.env.local`

Run:
```bash
npm run dev
```

Open `http://localhost:3000`.

## Usage (demo flow)
1. Start backend + frontend.
2. Load the built-in demo dataset (`demo_sales`) or upload a CSV.
3. Try prompts such as:
   - “Build an executive dashboard for sales performance”
   - “Show monthly revenue trend for Q3 broken down by region and highlight the top product category”
4. Use follow-ups to refine:
   - “Now filter this to East region”
   - “Show top 10 products by revenue”
5. Review the SQL panel for transparency.

## Safety + reliability
This prototype is designed to avoid “invented” answers:
- **Schema-bounded planning**: LLM prompts include table/columns + sample rows.
- **SQL validation** (`backend/app/services/sql_validator.py`):
  - Single statement only (no chaining)
  - `SELECT`/`WITH` only
  - Blocks DDL/DML/PRAGMA/ATTACH/DETACH/VACUUM/etc.
  - Blocks `sqlite_master` references
  - Restricts queries to the dataset table name
  - Enforces `LIMIT <= 1000` (adds a LIMIT if missing)
- **Read-only query execution**: queries run via a SQLite read-only connection.
- **Deterministic chart selection**: chart type is derived from actual returned data, not solely LLM suggestions.
- **Fallback behavior**: if Gemini is unavailable or returns invalid JSON, backend generates a safe fallback plan and surfaces warnings.

## Limitations
- Sessions are in-memory only (not persisted).
- SQLite only (no warehouse connectors, no auth/tenant isolation).
- Chart selection is heuristic and may not always match the user’s ideal visualization.
- Complex metric definitions (e.g., “margin”, “LTV”) require the relevant columns in the dataset.

## Troubleshooting
- **Gemini errors / empty insights**: confirm `GEMINI_API_KEY` is set in `backend/.env`.
- **CORS issues**: prefer Next rewrites (`NEXT_PUBLIC_API_URL=/api`). If calling backend directly, ensure `APP_CORS_ORIGINS` includes the frontend origin.
- **CSV upload rejected**: check file extension is `.csv` and size is under `APP_MAX_UPLOAD_BYTES`.
- **Windows `spawn EPERM` in Next.js**: use Node 20 LTS (see `frontend/README.md`).
- **“Unknown session_id”**: backend restarted; regenerate the dashboard to create a new session.
