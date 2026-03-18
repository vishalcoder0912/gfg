"""
Application configuration (env-driven).

GEMINI_MODEL default is "gemini-2.0-flash" — the current stable Gemini model.
"""

from __future__ import annotations
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    APP_DB_PATH: str = "./data/app_data.db"
    APP_MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024
    APP_CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 15.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.APP_CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()