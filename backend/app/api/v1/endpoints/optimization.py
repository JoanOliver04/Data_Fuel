"""Optimization analytics endpoint.

``GET /api/v1/analytics/optimization-summary`` aggregates the traffic-aware
optimization over the candidate stations for a query: average ETA, average
traffic delay, average fuel savings and the best-profile distribution (which
station each profile would pick). It is read-only, cached, and reuses the exact
candidate-ranking pipeline behind ``GET /recommendations`` so the numbers match.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.recommendations import _build_resolver, _compute_distances
from app.api.v1.schemas.optimization import (
    OptimizationSummaryOut,
    ProfileWinnerOut,
)
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import rank_stations
from app.infrastructure.database.session import get_async_session
from app.repositories.station_repository import StationRepository
from app.services.optimization import (
    DEFAULT_PROFILE,
    OptimizationProfile,
    summarize,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["optimization"])

# Candidate cap for the summary: large enough to be representative, small enough
# to bound the routing matrix call and keep the endpoint responsive.
_SUMMARY_CANDIDATE_LIMIT = 50


@router.get(
    "/optimization-summary",
    response_model=OptimizationSummaryOut,
    summary="Aggregate traffic-aware optimization metrics for a query",
)
@limiter.limit(lambda: get_settings().geocoding_rate_limit)
async def optimization_summary(
    request: Request,
    lat: Annotated[float, Query(ge=-90, le=90, description="User latitude (WGS84)")],
    lon: Annotated[float, Query(ge=-180, le=180, description="User longitude (WGS84)")],
    liters: Annotated[float, Query(gt=0, le=200, description="Litres to refuel")],
    fuel_type: Annotated[FuelType, Query(description="Fuel type")],
    profile: Annotated[
        OptimizationProfile, Query(description="Reference profile for the summary")
    ] = DEFAULT_PROFILE,
    km_cost: Annotated[
        float | None, Query(ge=0, description="Vehicle cost per km (€/km)")
    ] = None,
    max_distance_km: Annotated[
        float | None, Query(ge=0, description="Exclude stations beyond this distance")
    ] = None,
    session: AsyncSession = Depends(get_async_session),
) -> OptimizationSummaryOut:
    settings = get_settings()
    effective_km_cost = km_cost if km_cost is not None else settings.default_km_cost

    radius_origin = (lat, lon, max_distance_km) if max_distance_km is not None else None
    stations = await StationRepository(session).find_candidates(
        fuel_type=fuel_type,
        bbox=None,
        radius_origin=radius_origin,
    )

    distances = await _compute_distances(settings, lat, lon, stations)
    ranked = rank_stations(
        stations=stations,
        fuel_type=fuel_type,
        user_lat=lat,
        user_lon=lon,
        liters=liters,
        km_cost=effective_km_cost,
        max_distance_km=max_distance_km,
        limit=_SUMMARY_CANDIDATE_LIMIT,
        distances=distances,
        km_cost_resolver=_build_resolver(None),
    )

    summary = summarize(
        ranked,
        profile=profile,
        time_cost_per_hour=settings.time_cost_per_hour,
        traffic_penalty_factor=settings.traffic_penalty_factor,
    )
    log.info(
        "optimization-summary: %d candidates, profile=%s, fuel=%s",
        summary.station_count,
        profile,
        fuel_type,
    )
    return OptimizationSummaryOut(
        profile=summary.profile,
        station_count=summary.station_count,
        average_eta_minutes=summary.average_eta_minutes,
        average_traffic_delay_minutes=summary.average_traffic_delay_minutes,
        average_fuel_savings_eur=summary.average_fuel_savings_eur,
        best_profile_distribution=summary.best_profile_distribution,
        profile_winners=[
            ProfileWinnerOut(
                profile=w.profile,
                station_id=w.station_id,
                optimization_score=w.optimization_score,
            )
            for w in summary.profile_winners
        ],
    )
