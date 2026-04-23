"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response payload for the /health endpoint."""

    status: str
    version: str
    name: str


@router.get("/health", response_model=HealthResponse, summary="Service liveness probe")
def health() -> HealthResponse:
    """Return basic service status. Used by orchestrators and uptime monitors."""
    settings: Settings = get_settings()
    return HealthResponse(status="ok", version=settings.app_version, name=settings.app_name)
