"""
FastAPI entrypoint.

FIX: ensure_demo_dataset_loaded() was imported but never called.
     Added the call inside create_app() so the demo dataset is
     available immediately on startup.
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
    ensure_demo_dataset_loaded()           # ← THIS LINE WAS MISSING

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")

    @app.get("/")
    def read_root():
        return {"message": "Conversational BI Dashboard API is running. Check /api/datasets for available data."}

    return app


app = create_app()