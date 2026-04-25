"""Recommendations endpoint: cheapest stations ranked by total refuelling cost."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.recommendation import RecommendationOut
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import rank_stations
from app.domain.services.distance_service import (
    DistanceMode,
    DistanceResult,
    DistanceService,
)
from app.domain.services.vehicle_profile_service import compute_km_cost
from app.infrastructure.database.session import get_async_session
from app.infrastructure.external.ors import ORSClient
from app.repositories.station_repository import StationRepository
from app.repositories.vehicle_profile_repository import VehicleProfileRepository

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationOut], summary="Rank stations by total cost")
@limiter.limit(lambda: get_settings().geocoding_rate_limit)
async def get_recommendations(
    request: Request,
    lat: Annotated[float, Query(ge=-90, le=90, description="User latitude (WGS84)")],
    lon: Annotated[float, Query(ge=-180, le=180, description="User longitude (WGS84)")],
    liters: Annotated[float, Query(gt=0, le=200, description="Litres to refuel")],
    fuel_type: Annotated[FuelType, Query(description="Fuel type")],
    limit: Annotated[int, Query(ge=1, le=50, description="Max results")] = 10,
    km_cost: Annotated[
        float | None, Query(ge=0, description="Vehicle cost per km (€/km) — manual override")
    ] = None,
    vehicle_profile_id: Annotated[
        int | None, Query(description="Vehicle profile ID — overrides km_cost when set")
    ] = None,
    max_distance_km: Annotated[
        float | None, Query(ge=0, description="Exclude stations beyond this distance")
    ] = None,
    north: Annotated[
        float | None, Query(ge=-90, le=90, description="Bounding box north latitude")
    ] = None,
    south: Annotated[
        float | None, Query(ge=-90, le=90, description="Bounding box south latitude")
    ] = None,
    east: Annotated[
        float | None, Query(ge=-180, le=180, description="Bounding box east longitude")
    ] = None,
    west: Annotated[
        float | None, Query(ge=-180, le=180, description="Bounding box west longitude")
    ] = None,
    session: AsyncSession = Depends(get_async_session),
) -> list[RecommendationOut]:
    settings = get_settings()
    station_repo = StationRepository(session)

    if vehicle_profile_id is not None:
        profile = await VehicleProfileRepository(session).get_by_id(vehicle_profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Vehicle profile not found")
        avg_price = await station_repo.avg_price_for_fuel_type(fuel_type)
        if avg_price is not None:
            effective_km_cost = compute_km_cost(profile.fuel_consumption_per_100km, avg_price)
        else:
            # Fallback to the profile's reference K when no live prices are available.
            effective_km_cost = profile.km_cost_per_km
    elif km_cost is not None:
        effective_km_cost = km_cost
    else:
        effective_km_cost = settings.default_km_cost

    stations = await station_repo.list_all()

    # Pre-filter by bounding box when all four edges are provided
    if north is not None and south is not None and east is not None and west is not None:
        stations = [
            s
            for s in stations
            if south <= s.latitude <= north and west <= s.longitude <= east
        ]

    distances = await _compute_distances(settings, lat, lon, stations)

    ranked = rank_stations(
        stations=stations,
        fuel_type=fuel_type,
        user_lat=lat,
        user_lon=lon,
        liters=liters,
        km_cost=effective_km_cost,
        max_distance_km=max_distance_km,
        limit=limit,
        distances=distances,
    )
    return [RecommendationOut.from_station_cost(sc) for sc in ranked]


async def _compute_distances(
    settings,
    user_lat: float,
    user_lon: float,
    stations: list,
) -> dict[int, DistanceResult] | None:
    """Return per-station driving distances when DRIVING mode is active; else None."""
    mode = DistanceMode(settings.distance_mode)
    if mode is DistanceMode.EUCLIDEAN or not stations:
        return None

    ors_client = ORSClient() if settings.ors_api_key else None
    service = DistanceService(mode=mode, ors_client=ors_client)
    destinations = [(s.latitude, s.longitude) for s in stations]
    results = await service.compute((user_lat, user_lon), destinations)
    return {station.id: result for station, result in zip(stations, results, strict=True)}
