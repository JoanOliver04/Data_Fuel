"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Data Fuel backend."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,  # allow field-name init alongside env aliases
    )

    # ─── Application metadata ─────────────────────────────
    app_name: str = "Data Fuel API"
    app_version: str = "0.1.0"
    debug: bool = False

    # ─── Logging ──────────────────────────────────────────
    # DEBUG | INFO | WARNING | ERROR. Use DEBUG locally to see HTTP/SQL detail.
    log_level: str = Field(default="INFO")

    # ─── Observability ────────────────────────────────────
    # Expose Prometheus metrics at GET /metrics and instrument requests. Kept
    # as a kill-switch so metrics can be turned off without a code change.
    metrics_enabled: bool = True
    # Requests slower than this are logged at WARNING (production debugging aid).
    slow_request_ms: float = Field(default=1000.0, gt=0.0)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        v = str(value).strip().upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return v

    # ─── Database ─────────────────────────────────────────
    # SQLite (default, dev/CI) or PostgreSQL (production). Both async drivers:
    #   sqlite+aiosqlite:///./datafuel.db
    #   postgresql+asyncpg://user:pass@host:5432/datafuel
    database_url: str = Field(default="sqlite+aiosqlite:///./datafuel.db")
    # PostgreSQL connection-pool tuning (ignored for SQLite). Production-safe
    # defaults sized for a single app instance; raise pool_size for more workers.
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_recycle_seconds: int = Field(default=1800, ge=1)
    db_pool_timeout_seconds: float = Field(default=30.0, gt=0.0)
    db_connect_timeout_seconds: float = Field(default=10.0, gt=0.0)
    # Server-side statement timeout (ms) applied per asyncpg connection; 0 = off.
    db_statement_timeout_ms: int = Field(default=30000, ge=0)
    # Queries slower than this are counted + logged (production debugging aid).
    db_slow_query_ms: float = Field(default=500.0, gt=0.0)

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        """Accept SQLite/Postgres async URLs; upgrade bare postgres schemes that
        managed hosts (Railway/Render/Heroku) hand out to the asyncpg driver."""
        v = str(value).strip()
        if v.startswith("postgres://"):
            v = "postgresql+asyncpg://" + v[len("postgres://") :]
        elif v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://") :]
        if not (v.startswith("sqlite+aiosqlite:") or v.startswith("postgresql+asyncpg:")):
            raise ValueError(
                "DATABASE_URL must use sqlite+aiosqlite or postgresql+asyncpg (async drivers)"
            )
        return v

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

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
    ai_rate_limit: str = "20/minute"

    # ─── AI assistant (LLM) ───────────────────────────────
    # The conversational layer enriches existing deterministic explanations. It
    # is fully optional: with the default "fallback" provider (or no API key) it
    # returns deterministic explanations and makes no network calls, so the app
    # and its tests never depend on a live LLM.
    ai_enabled: bool = True
    # Provider id: fallback | openrouter | groq | ollama | openai (all real ones
    # are OpenAI-compatible /chat/completions APIs; "anthropic" is reserved). The
    # code default stays "fallback" so a keyless checkout makes zero network
    # calls; production sets DATAFUEL_LLM_PROVIDER=openrouter via env.
    llm_provider: str = Field(
        default="fallback",
        validation_alias=AliasChoices("llm_provider", "datafuel_llm_provider"),
    )
    # Generic key + per-provider keys (per-provider wins; see the factory).
    llm_api_key: str | None = None
    openrouter_api_key: str | None = None
    groq_api_key: str | None = None
    # Optional overrides; when unset the factory uses the provider preset.
    llm_base_url: str | None = None
    llm_model: str | None = None
    # Default model for OpenRouter (DeepSeek Chat).
    openrouter_model: str = Field(default="deepseek/deepseek-chat")
    llm_timeout_seconds: float = Field(default=8.0, gt=0.0)
    llm_max_retries: int = Field(default=1, ge=0)
    llm_max_output_tokens: int = Field(default=600, gt=0)
    # Hard cap on free-text chat input length (prompt-injection / cost guard).
    llm_max_input_chars: int = Field(default=2000, gt=0)
    ai_cache_ttl_seconds: float = Field(default=900.0, gt=0.0)
    # Analytics insights are deterministic by default. Flip this on (with an LLM
    # provider configured) to rephrase them via the LLM; failures silently keep
    # the deterministic text — analytics never depends on LLM availability.
    analytics_llm_insights: bool = False
    analytics_cache_ttl_seconds: float = Field(default=300.0, gt=0.0)

    # ─── Alerts ───────────────────────────────────────────
    # Intelligent fuel-alert engine. Evaluated on an interval job by the
    # scheduler; fully isolated from recommendation/ML internals (consumes their
    # public outputs only). Failures degrade gracefully and never crash the loop.
    alerts_enabled: bool = True
    alerts_eval_interval_seconds: int = Field(default=900, ge=30)
    # Hard cap on alerts evaluated per batch tick (back-pressure / loop safety).
    alerts_eval_batch_size: int = Field(default=200, ge=1)
    # Default per-alert cooldown when the user does not set one (anti-spam).
    alerts_default_cooldown_minutes: int = Field(default=360, ge=0)
    # A notification with the same dedup key inside this window is suppressed.
    alerts_dedup_window_minutes: int = Field(default=1440, ge=1)
    alerts_max_per_user: int = Field(default=50, ge=1)
    alerts_rate_limit: str = "30/minute"
    # Optional LLM rephrase of the deterministic alert message (off by default).
    alerts_llm_explanations: bool = False

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_llm_provider(cls, value: str) -> str:
        v = str(value).strip().lower()
        allowed = {"fallback", "openrouter", "groq", "ollama", "openai", "anthropic"}
        if v not in allowed:
            raise ValueError(f"LLM_PROVIDER must be one of {sorted(allowed)}")
        return v

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
