"""Recommendations endpoint: cheapest stations ranked by total refuelling cost."""

import logging
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.recommendation import RecommendationOut
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.domain.entities.fuel_type import FuelType
from app.domain.entities.vehicle_profile import ConsumptionMode
from app.domain.services.cost_calculator import KmCostResolver, rank_stations
from app.domain.services.distance_service import (
    DistanceMode,
    DistanceResult,
    DistanceService,
)
from app.domain.services.vehicle_profile_service import (
    ConsumptionProfile,
    km_cost_for_distance,
)
from app.infrastructure.database.models.vehicle_profile import VehicleProfileORM
from app.infrastructure.database.session import get_async_session
from app.infrastructure.external.ors import ORSClient
from app.repositories.station_repository import StationRepository
from app.repositories.vehicle_profile_repository import VehicleProfileRepository

log = logging.getLogger(__name__)

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

    log.debug(
        "recommendations: lat=%.4f lon=%.4f fuel=%s liters=%s limit=%d profile=%s km_cost=%s bbox=%s",
        lat,
        lon,
        fuel_type,
        liters,
        limit,
        vehicle_profile_id,
        km_cost,
        all(v is not None for v in (north, south, east, west)),
    )

    profile: VehicleProfileORM | None = None
    if vehicle_profile_id is not None:
        profile = await VehicleProfileRepository(session).get_by_id(vehicle_profile_id)
        if profile is None:
            log.info("recommendations: vehicle_profile_id=%d not found", vehicle_profile_id)
            raise HTTPException(status_code=404, detail="Vehicle profile not found")
        effective_km_cost = profile.km_cost_per_km
    elif km_cost is not None:
        effective_km_cost = km_cost
    else:
        effective_km_cost = settings.default_km_cost

    stations = await station_repo.list_all()
    total_stations = len(stations)

    # Pre-filter by bounding box when all four edges are provided
    if north is not None and south is not None and east is not None and west is not None:
        stations = [
            s
            for s in stations
            if south <= s.latitude <= north and west <= s.longitude <= east
        ]
        log.debug(
            "recommendations bbox filter: %d → %d stations",
            total_stations,
            len(stations),
        )

    distances = await _compute_distances(settings, lat, lon, stations)
    resolver = _build_resolver(profile)

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
        km_cost_resolver=resolver,
    )
    log.info(
        "recommendations: %d/%d stations ranked (fuel=%s, distance_mode=%s)",
        len(ranked),
        len(stations),
        fuel_type,
        settings.distance_mode,
    )
    return [RecommendationOut.from_station_cost(sc) for sc in ranked]


def _build_resolver(profile: VehicleProfileORM | None) -> KmCostResolver | None:
    """Return a per-station K resolver from a vehicle profile, or None."""
    if profile is None:
        return None
    consumption_profile = ConsumptionProfile(
        urban=profile.fuel_consumption_urban,
        mixed=profile.fuel_consumption_mixed,
        highway=profile.fuel_consumption_highway,
    )

    def resolve(distance_km: float, fuel_price: Decimal) -> tuple[float, ConsumptionMode, float]:
        price_float = float(fuel_price)
        k_value, mode = km_cost_for_distance(consumption_profile, distance_km, price_float)
        consumption_used = consumption_profile.consumption_for(mode)
        return k_value, mode, consumption_used

    return resolve


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
