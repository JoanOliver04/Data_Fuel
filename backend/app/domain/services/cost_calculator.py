"""Core cost formula: Cᵢ = (V · Pᵢ) + (Dᵢ · K).

V  = liters to refuel
Pᵢ = price per litre at station i  (€/L)
Dᵢ = distance to station i (km) — haversine by default, real road distance
     when a `DistanceResult` with `driving_distance_km` is supplied
K  = vehicle cost per km  (€/km, default 0.13)
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database.models.station import StationORM

if TYPE_CHECKING:
    from app.domain.services.distance_service import DistanceResult

_EARTH_RADIUS_KM = 6_371.0
_CENT = Decimal("0.001")


@dataclass(frozen=True, slots=True)
class StationCost:
    station_id: int
    brand: str
    address: str
    locality: str
    municipality: str
    province: str
    latitude: float
    longitude: float
    schedule: str
    fuel_type: FuelType
    price_per_liter: Decimal
    liters: float
    distance_km: float
    km_cost: float
    fuel_cost: Decimal
    travel_cost: Decimal
    total_cost: Decimal
    driving_distance_km: float | None = None
    driving_duration_min: float | None = None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance between two WGS84 points in kilometres."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * math.sin(dlon / 2) ** 2
    return _EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


def rank_stations(
    stations: Sequence[StationORM],
    fuel_type: FuelType,
    user_lat: float,
    user_lon: float,
    liters: float,
    km_cost: float,
    max_distance_km: float | None = None,
    limit: int = 10,
    distances: Mapping[int, DistanceResult] | None = None,
) -> list[StationCost]:
    """Rank stations by total refuelling cost for the given parameters.

    Stations lacking a price for `fuel_type` or beyond `max_distance_km` are excluded.
    Returns at most `limit` results, cheapest first.

    When `distances` is provided (keyed by `station.id`), the travel cost uses the
    driving distance from that mapping; otherwise haversine is used. Haversine
    remains the value of `distance_km` so frontends retain the straight-line metric.
    """
    results: list[StationCost] = []
    liters_d = Decimal(str(liters))
    km_cost_d = Decimal(str(km_cost))

    for station in stations:
        price = _price_for(station, fuel_type)
        if price is None:
            continue

        straight_line = haversine_km(user_lat, user_lon, station.latitude, station.longitude)
        dist_info = distances.get(station.id) if distances is not None else None

        cost_dist = (
            dist_info.driving_distance_km
            if dist_info is not None and dist_info.driving_distance_km is not None
            else straight_line
        )
        if max_distance_km is not None and cost_dist > max_distance_km:
            continue

        dist_d = Decimal(str(round(cost_dist, 3)))
        fuel_cost = (liters_d * price).quantize(_CENT, ROUND_HALF_UP)
        travel_cost = (dist_d * km_cost_d).quantize(_CENT, ROUND_HALF_UP)
        total_cost = fuel_cost + travel_cost

        results.append(
            StationCost(
                station_id=station.id,
                brand=station.brand,
                address=station.address,
                locality=station.locality,
                municipality=station.municipality,
                province=station.province,
                latitude=station.latitude,
                longitude=station.longitude,
                schedule=station.schedule,
                fuel_type=fuel_type,
                price_per_liter=price,
                liters=liters,
                distance_km=round(straight_line, 3),
                km_cost=km_cost,
                fuel_cost=fuel_cost,
                travel_cost=travel_cost,
                total_cost=total_cost,
                driving_distance_km=(
                    round(dist_info.driving_distance_km, 3)
                    if dist_info is not None and dist_info.driving_distance_km is not None
                    else None
                ),
                driving_duration_min=(
                    round(dist_info.driving_duration_min, 1)
                    if dist_info is not None and dist_info.driving_duration_min is not None
                    else None
                ),
            )
        )

    results.sort(key=lambda sc: sc.total_cost)
    return results[:limit]


def _price_for(station: StationORM, fuel_type: FuelType) -> Decimal | None:
    return {
        FuelType.GASOLINA_95: station.price_gasoline_95_e5,
        FuelType.GASOLINA_95_E10: station.price_gasoline_95_e10,
        FuelType.GASOLINA_98: station.price_gasoline_98_e5,
        FuelType.GASOIL: station.price_diesel_a,
        FuelType.GASOIL_PREMIUM: station.price_diesel_premium,
    }.get(fuel_type)
