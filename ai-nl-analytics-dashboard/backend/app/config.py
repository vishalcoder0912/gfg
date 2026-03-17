"""
Application configuration (env-driven).

This file keeps all knobs in one place:
- SQLite path
- Upload limits
- CORS origins
- Gemini API key / model name
"""

from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    # SQLite DB path (prototype default). Swap to Postgres later by replacing database.py + executor.
    APP_DB_PATH: str = "./data/app_data.db"

    # 50MB upload cap by default.
    APP_MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024

    # Comma-separated origins for local dev (Next default is 3000).
    APP_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

    # Gemini (Google AI Studio)
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 15.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.APP_CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
