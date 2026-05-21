"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.domain.services.distance_service import DistanceMode
from app.services.routing.quota import default_quota_guard

router = APIRouter(tags=["health"])


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
    # Omitted from the response unless DISTANCE_MODE=DRIVING_TOMTOM
    # (route uses response_model_exclude_none).
    tomtom_quota: TomTomQuotaOut | None = None


@router.get(
    "/health",
    response_model=HealthResponse,
    response_model_exclude_none=True,
    summary="Service liveness probe",
)
def health() -> HealthResponse:
    """Return basic service status. Used by orchestrators and uptime monitors."""
    settings: Settings = get_settings()

    tomtom_quota: TomTomQuotaOut | None = None
    if DistanceMode(settings.distance_mode) is DistanceMode.DRIVING_TOMTOM:
        snap = default_quota_guard.snapshot(settings.tomtom_daily_quota_limit)
        tomtom_quota = TomTomQuotaOut(
            date=snap.date.isoformat(),
            used=snap.used,
            limit=snap.limit,
            exhausted=snap.exhausted,
        )

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        name=settings.app_name,
        tomtom_quota=tomtom_quota,
    )
