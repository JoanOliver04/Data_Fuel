"""Recommendations endpoint: cheapest stations ranked by total refuelling cost."""

import logging
from collections.abc import Sequence
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.recommendation import RecommendationOut
from app.core.cache import recommendations_cache
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.domain.entities.fuel_type import FuelType
from app.domain.entities.vehicle_profile import ConsumptionMode
from app.domain.services.cost_calculator import KmCostResolver, rank_stations
from app.domain.services.distance_service import DistanceMode, DistanceResult
from app.domain.services.vehicle_profile_service import (
    ConsumptionProfile,
    km_cost_for_distance,
)
from app.infrastructure.database.models.station import StationORM
from app.infrastructure.database.models.vehicle_profile import VehicleProfileORM
from app.infrastructure.database.session import get_async_session
from app.repositories.station_repository import StationRepository
from app.repositories.vehicle_profile_repository import VehicleProfileRepository
from app.services.routing import RouteLeg, get_routing_provider

log = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# When a driving mode is active, the routing matrix call (ORS or TomTom) is the
# bottleneck (network + rate limits + paid quota). We pre-rank candidates by
# haversine + price and only send the most promising subset to the provider.
# The driving distance ≥ haversine always, so the cheapest station by driving
# cost is virtually guaranteed to fall in the top-N by haversine cost when N is
# generous. This cap also protects the TomTom daily quota from large bboxes.
_ROUTING_CANDIDATE_MULTIPLIER = 4
_ROUTING_CANDIDATE_MIN = 30
_ROUTING_CANDIDATE_MAX = 100


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

    cache_key = _build_cache_key(
        lat, lon, liters, fuel_type, limit, km_cost,
        vehicle_profile_id, max_distance_km, north, south, east, west,
    )
    cached = await recommendations_cache.get(cache_key)
    if cached is not None:
        log.debug("recommendations cache hit (%d items)", len(cached))
        return cached

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

    bbox: tuple[float, float, float, float] | None = None
    if north is not None and south is not None and east is not None and west is not None:
        bbox = (south, north, west, east)

    radius_origin: tuple[float, float, float] | None = None
    if bbox is None and max_distance_km is not None:
        radius_origin = (lat, lon, max_distance_km)

    stations = await station_repo.find_candidates(
        fuel_type=fuel_type,
        bbox=bbox,
        radius_origin=radius_origin,
    )
    log.debug(
        "recommendations SQL prefilter: %d stations (bbox=%s, radius=%s)",
        len(stations),
        bbox is not None,
        radius_origin is not None,
    )

    resolver = _build_resolver(profile)

    # Routing pre-filter: shrink candidate set to top-N by haversine cost so the
    # Matrix call is bounded regardless of how many stations sit in the bbox.
    mode = DistanceMode(settings.distance_mode)
    if mode.is_driving and stations:
        prelim_limit = min(
            _ROUTING_CANDIDATE_MAX,
            max(_ROUTING_CANDIDATE_MIN, limit * _ROUTING_CANDIDATE_MULTIPLIER),
        )
        if len(stations) > prelim_limit:
            prelim = rank_stations(
                stations=stations,
                fuel_type=fuel_type,
                user_lat=lat,
                user_lon=lon,
                liters=liters,
                km_cost=effective_km_cost,
                max_distance_km=max_distance_km,
                limit=prelim_limit,
                distances=None,
                km_cost_resolver=resolver,
            )
            candidate_ids = {sc.station_id for sc in prelim}
            before = len(stations)
            stations = [s for s in stations if s.id in candidate_ids]
            log.debug(
                "routing pre-rank: %d → %d candidates (cap=%d)",
                before,
                len(stations),
                prelim_limit,
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
    result = [RecommendationOut.from_station_cost(sc) for sc in ranked]
    await recommendations_cache.set(cache_key, result)
    return result


def _build_cache_key(
    lat: float,
    lon: float,
    liters: float,
    fuel_type: FuelType,
    limit: int,
    km_cost: float | None,
    vehicle_profile_id: int | None,
    max_distance_km: float | None,
    north: float | None,
    south: float | None,
    east: float | None,
    west: float | None,
) -> tuple[Any, ...]:
    """Stable hashable key over every param that affects the response.

    Coordinates are quantised to ~10 m so trivial GPS jitter still hits the
    cache; coarser quantisation would mix nearby users and skew rankings.
    """
    def _q4(v: float | None) -> float | None:
        return None if v is None else round(v, 4)

    return (
        round(lat, 4),
        round(lon, 4),
        round(liters, 2),
        fuel_type.value,
        limit,
        _q4(km_cost),
        vehicle_profile_id,
        None if max_distance_km is None else round(max_distance_km, 3),
        _q4(north), _q4(south), _q4(east), _q4(west),
    )


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
    settings: Settings,
    user_lat: float,
    user_lon: float,
    stations: Sequence[StationORM],
) -> dict[int, DistanceResult] | None:
    """Return per-station driving distances when a driving mode is active; else None.

    Selects the provider via the routing factory (ORS / TomTom / haversine) and
    maps each ``RouteLeg`` back to the ``DistanceResult`` the cost calculator
    consumes, so ranking and the response contract are unchanged.
    """
    mode = DistanceMode(settings.distance_mode)
    if not mode.is_driving or not stations:
        return None

    provider = get_routing_provider(settings)
    destinations = [(s.latitude, s.longitude) for s in stations]
    legs = await provider.matrix((user_lat, user_lon), destinations)
    return {
        station.id: _leg_to_distance_result(leg)
        for station, leg in zip(stations, legs, strict=True)
    }


def _leg_to_distance_result(leg: RouteLeg) -> DistanceResult:
    """Map a routing ``RouteLeg`` to the cost calculator's ``DistanceResult``.

    A failed leg (provider degraded to haversine) or a provider without a
    duration (haversine itself) exposes no driving/traffic data, so ranking
    falls back to the straight-line distance exactly as before.
    """
    if leg.failed or leg.duration_seconds is None:
        return DistanceResult(
            distance_km=leg.distance_km,
            driving_distance_km=None,
            driving_duration_min=None,
            traffic_delay_seconds=None,
        )
    return DistanceResult(
        distance_km=leg.distance_km,
        driving_distance_km=leg.distance_km,
        driving_duration_min=leg.duration_seconds / 60.0,
        traffic_delay_seconds=leg.traffic_delay_seconds,
    )
