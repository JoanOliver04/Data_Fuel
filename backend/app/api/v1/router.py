"""Top-level v1 router that aggregates endpoint modules."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, recommendations, stations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(stations.router)
api_router.include_router(recommendations.router)
