"""
FastAPI entrypoint for the Conversational BI prototype.

Required endpoints:
- GET  /health
- POST /upload-csv
- POST /generate-dashboard
- POST /follow-up

Optional:
- GET /datasets
- GET /dataset/{dataset_id}/schema
- GET /dataset/{dataset_id}/preview
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import ensure_meta_tables, ensure_sqlite_parent_dir
from app.routes.health import router as health_router
from app.routes.upload import router as upload_router
from app.routes.dashboard import router as dashboard_router
from app.routes.chat import router as chat_router
from app.services.dataset_registry import ensure_demo_dataset_loaded


def create_app() -> FastAPI:
    app = FastAPI(title="Conversational BI Dashboard API", version="1.0.0")

    ensure_sqlite_parent_dir()
    ensure_meta_tables()
    ensure_demo_dataset_loaded()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(upload_router)
    app.include_router(dashboard_router)
    app.include_router(chat_router)
    return app


app = create_app()
