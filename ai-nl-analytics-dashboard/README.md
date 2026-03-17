# Conversational AI for Instant Business Intelligence Dashboards

Hackathon prototype: non-technical executives can generate multi-chart, interactive dashboards using plain-English prompts.

## Problem Statement
Build an intelligent system that turns a business question into a cohesive dashboard in real time: multiple charts, KPIs, executive insights, and follow-up refinements, without requiring SQL or BI tool configuration.

## Why This Matters (CXO Persona)
Executives know the question, not the query language. They want instant, presentation-ready dashboards and clear explanations, not manual chart configuration.

## Key Features (Optimized for Judging)
- Built-in demo dataset (`demo_sales`) so judges can start immediately
- CSV upload (drag and drop + file picker), size/type validation, encoding detection
- Schema profiling: numeric/categorical/date columns + sample rows
- Natural language -> dashboard plan (Gemini): 1 to 4 chart intents + KPI intents
- Multi-query SQL generation (Gemini per chart) with strong SQL validation
- Deterministic chart selection engine to validate/override LLM suggestions
- Executive insights (Gemini) based only on returned query results
- Follow-up prompts with session memory (`/follow-up`) to refine dashboards
- SQL transparency panel + raw data table for trust

## Tech Stack
- Frontend: Next.js (App Router), React, TypeScript, Tailwind CSS, Recharts
- Backend: FastAPI, pandas, SQLite
- AI: Google Gemini API via Google AI Studio

## Architecture Flow (Text -> Dashboard)
```
Prompt
  -> Gemini: dashboard plan (1-4 chart intents + KPI intents)
  -> For each chart intent:
       Gemini: SQL (SQLite)
       Backend: validate SQL (SELECT/WITH only) + execute safely
       Backend: deterministic chart selection from actual results
  -> Gemini: executive insights from real results context
  -> Dashboard JSON spec returned
  -> Next.js renders KPI cards + multi-chart grid + insights + SQL panel + data table
  -> Follow-up prompts refine the dashboard using session memory
```

## Hallucination Handling Strategy
- Strict schema context is provided to Gemini (table name, columns, sample rows).
- SQL is validated:
  - Only single-statement SELECT/WITH
  - Blocks DDL/DML/PRAGMA/ATTACH/DETACH/VACUUM
  - Blocks sqlite_master references
  - Enforces LIMIT <= 1000
- Insights are requested as a JSON array and are generated from a JSON context derived from real results.
- If results are empty or the request is unsupported, the API returns a friendly message and lists available columns.

## Setup

### Backend
From `backend/`:
```bash
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt    # Windows
# or: source .venv/bin/activate && pip install -r requirements.txt
```

Create env:
- Copy `backend/.env.example` to `backend/.env`
- Set `GEMINI_API_KEY`

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
- Copy `frontend/.env.example` to `frontend/.env.local`

Run:
```bash
npm run dev
```

Open `http://localhost:3000`.

## API Endpoints
- GET `/health`
- POST `/upload-csv`
- POST `/generate-dashboard`
- POST `/follow-up`
- Optional:
  - GET `/datasets`
  - GET `/dataset/{dataset_id}/schema`
  - GET `/dataset/{dataset_id}/preview`

## Demo Prompts (For Presentation)
1. "Build an executive dashboard for sales performance"
2. "Show monthly revenue trend for Q3 broken down by region and highlight the top product category"
3. Follow-up: "Now filter this to East region"

## Unsupported Query Example (Show Honesty)
"Show margin by customer segment"
- If the dataset lacks `customer_segment`, the system refuses gracefully and suggests available columns.

## Future Improvements
- Persist datasets and sessions (auth + saved dashboards)
- Stronger AST-based SQL validation + column-level enforcement
- Better dashboard plan validation and automatic top-N selection for high-cardinality categories
- PostgreSQL support + row-level security

## Why Judges Will Like This
- End-to-end product flow: prompt -> multi-chart dashboard -> follow-up refinement
- Safe-by-design execution with SQL transparency
- Demo dataset and example prompts for fast evaluation

## Public Repo Submission Checklist
- [ ] Ensure `.env` and `.env.local` are not committed
- [ ] Include demo prompts and follow-up example in README
- [ ] Add a short demo video

