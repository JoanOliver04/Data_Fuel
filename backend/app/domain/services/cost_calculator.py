"""Core cost formula: Cᵢ = (V · Pᵢ) + (Dᵢ · K).

V  = liters to refuel
Pᵢ = price per litre at station i  (€/L)
Dᵢ = straight-line distance to station i  (km, haversine)
K  = vehicle cost per km  (€/km, default 0.13)
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database.models.station import StationORM

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
) -> list[StationCost]:
    """Rank stations by total refuelling cost for the given parameters.

    Stations lacking a price for `fuel_type` or beyond `max_distance_km` are excluded.
    Returns at most `limit` results, cheapest first.
    """
    results: list[StationCost] = []
    liters_d = Decimal(str(liters))
    km_cost_d = Decimal(str(km_cost))

    for station in stations:
        price = _price_for(station, fuel_type)
        if price is None:
            continue

        dist = haversine_km(user_lat, user_lon, station.latitude, station.longitude)
        if max_distance_km is not None and dist > max_distance_km:
            continue

        dist_d = Decimal(str(round(dist, 3)))
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
                distance_km=round(dist, 3),
                km_cost=km_cost,
                fuel_cost=fuel_cost,
                travel_cost=travel_cost,
                total_cost=total_cost,
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
