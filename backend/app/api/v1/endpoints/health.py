"""Health, liveness, readiness and detailed status endpoints.

* ``GET /health``         — legacy liveness probe (unchanged contract).
* ``GET /health/live``    — liveness: the process is up and serving.
* ``GET /health/ready``   — readiness: dependency checks; 503 when not ready.
* ``GET /health/details`` — rich operational snapshot for dashboards/debugging.

Readiness gates only on the database (the one hard dependency); a missing
model, idle scheduler or keyless routing provider degrade specific features
but the service can still serve traffic, so they are reported as ``degraded``
(HTTP 200) rather than failing the probe.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.domain.services.distance_service import DistanceMode
from app.infrastructure.database.session import get_session_factory
from app.ml.inference.model_loader import get_modelo
from app.repositories.training_run_repository import TrainingRunRepository
from app.services.routing.quota import default_quota_guard

router = APIRouter(tags=["health"])


# ── Legacy /health (unchanged contract) ───────────────────────────────────────
class TomTomQuotaOut(BaseModel):
    """Daily TomTom routing quota usage (only present in DRIVING_TOMTOM mode)."""

    date: str
    used: int
    limit: int
    exhausted: bool


class HealthResponse(BaseModel):
    """Response payload for the /health endpoint."""

    status: str
    version: str
    name: str
    tomtom_quota: TomTomQuotaOut | None = None


def _tomtom_quota(settings: Settings) -> TomTomQuotaOut | None:
    if DistanceMode(settings.distance_mode) is not DistanceMode.DRIVING_TOMTOM:
        return None
    snap = default_quota_guard.snapshot(settings.tomtom_daily_quota_limit)
    return TomTomQuotaOut(
        date=snap.date.isoformat(),
        used=snap.used,
        limit=snap.limit,
        exhausted=snap.exhausted,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    response_model_exclude_none=True,
    summary="Service liveness probe",
)
def health() -> HealthResponse:
    """Return basic service status. Used by orchestrators and uptime monitors."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        name=settings.app_name,
        tomtom_quota=_tomtom_quota(settings),
    )


# ── Liveness ───────────────────────────────────────────────────────────────────
class LivenessResponse(BaseModel):
    status: str
    uptime_seconds: float


@router.get("/health/live", response_model=LivenessResponse, summary="Liveness probe")
def liveness(request: Request) -> LivenessResponse:
    """Always 200 while the event loop is running — for orchestrator restarts."""
    started: float = getattr(request.app.state, "started_at", time.monotonic())
    return LivenessResponse(status="alive", uptime_seconds=round(time.monotonic() - started, 1))


# ── Readiness ───────────────────────────────────────────────────────────────────
class CheckResult(BaseModel):
    ok: bool
    detail: str | None = None


class ReadinessResponse(BaseModel):
    # ready | degraded | not_ready
    status: str
    checks: dict[str, CheckResult]


async def _check_db() -> CheckResult:
    """Open a session and run SELECT 1. Only the exception *type* is surfaced."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return CheckResult(ok=True)
    except Exception as exc:  # health must never raise; report the type only
        return CheckResult(ok=False, detail=type(exc).__name__)


def _scheduler_running(request: Request) -> bool:
    scheduler = getattr(request.app.state, "scheduler", None)
    return bool(getattr(scheduler, "running", False))


@router.get("/health/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    settings = get_settings()
    db = await _check_db()
    model_loaded = get_modelo() is not None
    scheduler_expected = settings.scheduler_enabled or settings.retrain_enabled
    scheduler_ok = (not scheduler_expected) or _scheduler_running(request)

    checks = {
        "database": db,
        "cache": CheckResult(ok=True),  # in-process TTL cache is always reachable
        "model": CheckResult(
            ok=model_loaded, detail=None if model_loaded else "model not loaded"
        ),
        "scheduler": CheckResult(
            ok=scheduler_ok, detail=None if scheduler_ok else "scheduler not running"
        ),
    }

    if not db.ok:
        status = "not_ready"
        response.status_code = 503
    elif all(c.ok for c in checks.values()):
        status = "ready"
    else:
        status = "degraded"
    return ReadinessResponse(status=status, checks=checks)


# ── Detailed status ─────────────────────────────────────────────────────────────
class ModelHealth(BaseModel):
    loaded: bool
    version: str | None = None
    trained_at: str | None = None
    mae: float | None = None
    r2: float | None = None


class SchedulerJob(BaseModel):
    id: str
    next_run: str | None = None


class SchedulerHealth(BaseModel):
    enabled: bool
    running: bool
    jobs: list[SchedulerJob]


class ProvidersHealth(BaseModel):
    distance_mode: str
    routing_provider: str
    api_key_configured: bool
    tomtom_quota: TomTomQuotaOut | None = None


class HealthDetails(BaseModel):
    status: str
    version: str
    name: str
    uptime_seconds: float
    database: CheckResult
    model: ModelHealth
    cache: dict[str, int]
    scheduler: SchedulerHealth
    providers: ProvidersHealth
    last_retraining: str | None = None


def _model_health() -> ModelHealth:
    artifact: dict[str, Any] | None = get_modelo()
    if artifact is None:
        return ModelHealth(loaded=False)
    trained_at = artifact.get("trained_at")
    return ModelHealth(
        loaded=True,
        version=artifact.get("version"),
        trained_at=str(trained_at) if trained_at is not None else None,
        mae=artifact.get("mae"),
        r2=artifact.get("r2"),
    )


def _scheduler_health(request: Request, settings: Settings) -> SchedulerHealth:
    scheduler = getattr(request.app.state, "scheduler", None)
    running = bool(getattr(scheduler, "running", False))
    jobs: list[SchedulerJob] = []
    if scheduler is not None and running:
        for job in scheduler.get_jobs():
            nxt = getattr(job, "next_run_time", None)
            jobs.append(SchedulerJob(id=job.id, next_run=nxt.isoformat() if nxt else None))
    return SchedulerHealth(
        enabled=settings.scheduler_enabled or settings.retrain_enabled,
        running=running,
        jobs=jobs,
    )


def _providers_health(settings: Settings) -> ProvidersHealth:
    mode = DistanceMode(settings.distance_mode)
    if mode in (DistanceMode.DRIVING, DistanceMode.DRIVING_ORS):
        provider = "OrsMatrixProvider" if settings.ors_api_key else "HaversineProvider"
        configured = bool(settings.ors_api_key)
    elif mode is DistanceMode.DRIVING_TOMTOM:
        provider = "TomTomMatrixProvider" if settings.tomtom_api_key else "HaversineProvider"
        configured = bool(settings.tomtom_api_key)
    else:
        provider, configured = "HaversineProvider", True
    return ProvidersHealth(
        distance_mode=mode.value,
        routing_provider=provider,
        api_key_configured=configured,
        tomtom_quota=_tomtom_quota(settings),
    )


async def _last_retraining() -> str | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            runs = await TrainingRunRepository(session).list_recent(1)
    except Exception:  # health must never raise (e.g. table missing)
        return None
    if not runs:
        return None
    when = runs[0].finished_at or runs[0].started_at
    return when.isoformat() if when is not None else None


@router.get("/health/details", response_model=HealthDetails, summary="Detailed status")
async def health_details(request: Request) -> HealthDetails:
    settings = get_settings()
    started: float = getattr(request.app.state, "started_at", time.monotonic())
    db = await _check_db()
    return HealthDetails(
        status="ok" if db.ok else "degraded",
        version=settings.app_version,
        name=settings.app_name,
        uptime_seconds=round(time.monotonic() - started, 1),
        database=db,
        model=_model_health(),
        cache={"recommendations_size": _recommendations_cache_size()},
        scheduler=_scheduler_health(request, settings),
        providers=_providers_health(settings),
        last_retraining=await _last_retraining(),
    )


def _recommendations_cache_size() -> int:
    from app.core.cache import recommendations_cache

    return recommendations_cache.size()
