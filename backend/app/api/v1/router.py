"""Top-level v1 router that aggregates endpoint modules."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    health,
    predictions,
    recommendations,
    smart_advice,
    stations,
    vehicle_profiles,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(stations.router)
api_router.include_router(recommendations.router)
api_router.include_router(predictions.router)
api_router.include_router(smart_advice.router)
api_router.include_router(vehicle_profiles.router)
api_router.include_router(ai.router)
