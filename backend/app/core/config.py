"""
Centralised application configuration.

All values are overridable via environment variables (see ../../.env.example
at the repo root). Nothing secret is hard-coded here.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General -----------------------------------------------------------
    PROJECT_NAME: str = "PedesPi"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | staging | production

    # --- Security ------------------------------------------------------------
    SECRET_KEY: str = "change-me-in-.env"  # noqa: S105 - placeholder default
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # --- CORS ----------------------------------------------------------------
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # --- Database --------------------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+psycopg2://pds_user:pds_pass@localhost:5432/pds_db"
    )

    # --- Redis (pub/sub for websocket alert fan-out, task queue backend) -----
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Detection pipeline (NFR-01, NFR-02, Section 9 decision tree) --------
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.5
    LOW_LIGHT_CONFIDENCE_THRESHOLD: float = 0.4
    SAFE_DISTANCE_METERS: float = 3.0
    CLOSING_SPEED_CRITICAL_MPS: float = 2.0
    TARGET_FPS: int = 15  # NFR-01
    WORKER_POLL_INTERVAL_SECONDS: int = 10  # how long the worker waits between passes

    # --- Model registry (FR-13) ------------------------------------------------
    MODEL_WEIGHTS_DIR: str = "/models"
    ACTIVE_MODEL_NAME: str = "yolov8n-pedestrian"

    # --- Data retention (NFR-07, Ghana Data Protection Act 2012 / Act 843) ---
    FOOTAGE_RETENTION_DAYS: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
