"""API schemas for recommendations: station ranking and AI refuel advice."""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

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
    traffic_delay_seconds: int | None = None
    consumption_mode: ConsumptionMode | None = None
    consumption_l_per_100km: float | None = None

    @classmethod
    def from_station_cost(cls, sc: StationCost) -> RecommendationOut:
        return cls(**dataclasses.asdict(sc))


# ── AI refuel-advice schemas ───────────────────────────────────────────────────


class RecommendationRequest(BaseModel):
    """Input for the AI refuel-advice endpoint."""

    lat: float = Field(ge=-90, le=90, description="User latitude (WGS84)")
    lon: float = Field(ge=-180, le=180, description="User longitude (WGS84)")
    fuel_type: FuelType
    municipio: str
    comarca: str
    precio_actual: float = Field(gt=0, description="Current fuel price at the station (€/L)")


class RecommendationResponse(BaseModel):
    """AI refuel-advice response from the Random Forest model."""

    veredicto: Literal["REPOSTA AHORA", "ESPERA"]
    precio_actual: float
    precio_predicho: float
    variacion_pct: float
    advice: str
    confianza: float
