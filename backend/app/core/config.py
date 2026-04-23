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

    # ─── Database ─────────────────────────────────────────
    database_url: str = Field(default="sqlite+aiosqlite:///./datafuel.db")

    # ─── MITECO API ───────────────────────────────────────
    miteco_base_url: str = Field(
        default="https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes",
    )
    miteco_request_timeout: float = 30.0

    # ─── Cost calculation ─────────────────────────────────
    default_km_cost: float = Field(default=0.13, ge=0.0)

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
