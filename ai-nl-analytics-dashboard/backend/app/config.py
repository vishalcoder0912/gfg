"""
Application configuration (env-driven).

MODEL RECOMMENDATION:
  gemini-2.0-flash  ← BEST choice for this app
    - Fastest response time for JSON + SQL generation tasks
    - 1M context window (handles large schemas)
    - 15 RPM free tier, 1500 RPD — enough for most demo usage
    - Superior at structured JSON output vs older models
    - gemini-3-flash-preview does NOT exist (was in old .env.example by mistake)
    - gemini-1.5-flash works but is slower and older

  Upgrade path if you hit quotas:
    gemini-2.5-flash → higher RPM, smarter reasoning
    gemini-2.0-flash-lite → cheaper, 30 RPM, good for simple SQL
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

    # ── Gemini ────────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str | None = None

    # Best model for SQL generation + structured JSON output at free tier
    # Do NOT use: gemini-3-flash-preview (doesn't exist), gemini-1.5-flash (deprecated)
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Generous timeout — Gemini can be slow when combining plan+SQL+insights
    GEMINI_TIMEOUT_SECONDS: float = 30.0

    # Rate-limit guard: minimum seconds between Gemini API calls (per process)
    # Free tier = 15 RPM = 4s between calls to stay safe; set 0 to disable
    GEMINI_MIN_CALL_INTERVAL_SECONDS: float = 4.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.APP_CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()