"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Data Fuel backend."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application metadata ─────────────────────────────
    app_name: str = "Data Fuel API"
    app_version: str = "0.1.0"
    debug: bool = False

    # ─── Logging ──────────────────────────────────────────
    # DEBUG | INFO | WARNING | ERROR. Use DEBUG locally to see HTTP/SQL detail.
    log_level: str = Field(default="INFO")

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        v = str(value).strip().upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return v

    # ─── Database ─────────────────────────────────────────
    database_url: str = Field(default="sqlite+aiosqlite:///./datafuel.db")

    # ─── MITECO API ───────────────────────────────────────
    miteco_base_url: str = Field(
        default="https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes",
    )
    miteco_request_timeout: float = 30.0

    # ─── Cost calculation ─────────────────────────────────
    default_km_cost: float = Field(default=0.13, ge=0.0)

    # ─── Distance calculation ─────────────────────────────
    distance_mode: str = Field(default="EUCLIDEAN")
    ors_api_key: str | None = None
    ors_base_url: str = Field(default="https://api.openrouteservice.org")
    ors_request_timeout: float = 10.0
    ors_matrix_chunk_size: int = Field(default=50, ge=1, le=50)

    @field_validator("distance_mode", mode="before")
    @classmethod
    def _normalize_distance_mode(cls, value: str) -> str:
        v = str(value).strip().upper()
        valid = {"EUCLIDEAN", "HAVERSINE", "DRIVING", "DRIVING_ORS", "DRIVING_TOMTOM"}
        if v not in valid:
            raise ValueError(
                "DISTANCE_MODE must be one of: EUCLIDEAN, HAVERSINE, DRIVING, "
                "DRIVING_ORS, DRIVING_TOMTOM"
            )
        return v

    # ─── TomTom Routing (Matrix Routing v2) ───────────────
    # Second driving-distance provider, traffic-aware. Only the client layer
    # is wired here; provider selection lives in a later routing phase.
    tomtom_api_key: str | None = None
    tomtom_base_url: str = Field(default="https://api.tomtom.com")
    tomtom_request_timeout: float = Field(default=20.0, gt=0.0)
    # Free tier is ~2500 req/day; default leaves a 100-request safety margin.
    # The routing adapter short-circuits to haversine once this is hit (UTC daily).
    tomtom_daily_quota_limit: int = Field(default=2400, ge=1)

    # ─── Sync scheduler ───────────────────────────────────
    sync_interval_seconds: int = Field(default=3600, ge=60)
    sync_on_startup: bool = True
    scheduler_enabled: bool = True

    # ─── ML retraining acceptance gate ────────────────────
    # Absolute guards (optional): a candidate breaching either is always rejected.
    retrain_max_mae: float | None = Field(default=None, ge=0.0)
    retrain_min_r2: float | None = None
    # Relative guards vs the active model: candidate MAE may be at most this
    # fraction worse, and R² may drop at most this many absolute points.
    retrain_max_mae_regression_pct: float = Field(default=0.10, ge=0.0)
    retrain_max_r2_absolute_drop: float = Field(default=0.05, ge=0.0)

    # ─── ML retraining schedule ───────────────────────────
    # Opt-in: the weekly retrain is heavy, so it is disabled by default.
    retrain_enabled: bool = False
    # 5-field cron (UTC). Default: every Sunday at 03:00.
    retrain_cron: str = Field(default="0 3 * * 0")
    # Hard wall-clock ceiling for one scheduled run; the job aborts past this.
    retrain_timeout_seconds: int = Field(default=3600, ge=60)

    @field_validator("retrain_cron", mode="before")
    @classmethod
    def _validate_cron(cls, value: str) -> str:
        v = str(value).strip()
        if len(v.split()) != 5:
            raise ValueError("RETRAIN_CRON must be a 5-field cron expression, e.g. '0 3 * * 0'")
        return v

    # ─── Rate limiting ────────────────────────────────────
    geocoding_rate_limit: str = "10/minute"
    predictions_rate_limit: str = "30/minute"

    # ─── CORS ─────────────────────────────────────────────
    # NoDecode skips pydantic-settings' default JSON decoding for list fields,
    # so the comma-separated env value reaches the validator as a raw string.
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        """Allow ALLOWED_ORIGINS to be a comma-separated string from .env."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings instance."""
    return Settings()
