"""API response schema for the recommendations endpoint."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

from pydantic import BaseModel

from app.domain.entities.fuel_type import FuelType
from app.domain.entities.vehicle_profile import ConsumptionMode
from app.domain.services.cost_calculator import StationCost


class RecommendationOut(BaseModel):
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
    consumption_mode: ConsumptionMode | None = None
    consumption_l_per_100km: float | None = None

    @classmethod
    def from_station_cost(cls, sc: StationCost) -> RecommendationOut:
        return cls(**dataclasses.asdict(sc))
