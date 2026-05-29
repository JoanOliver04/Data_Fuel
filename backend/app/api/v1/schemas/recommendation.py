"""API schemas for recommendations: station ranking and AI refuel advice."""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.entities.fuel_type import FuelType
from app.domain.entities.vehicle_profile import ConsumptionMode
from app.domain.services.cost_calculator import StationCost
from app.services.optimization import OptimizationProfile, OptimizedStation


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

    # ── Traffic-aware optimization (additive, opt-in) ──────────────────────────
    # All None unless an `optimization_profile` was requested. The score and its
    # time/traffic components are euro-denominated; `eta_minutes` mirrors the
    # driving duration used to price the time cost. Backwards compatible: legacy
    # clients ignore these and ranking-by-total_cost is unchanged when omitted.
    optimization_profile: OptimizationProfile | None = None
    optimization_score: float | None = None
    time_cost: float | None = None
    traffic_penalty: float | None = None
    eta_minutes: float | None = None

    @classmethod
    def from_station_cost(cls, sc: StationCost) -> RecommendationOut:
        return cls(**dataclasses.asdict(sc))

    @classmethod
    def from_optimized(cls, opt: OptimizedStation) -> RecommendationOut:
        """Build from an optimized station: base cost fields + optimization fields."""
        comp = opt.result.components
        return cls(
            **dataclasses.asdict(opt.station),
            optimization_profile=opt.result.profile,
            optimization_score=opt.result.score,
            time_cost=comp.time_cost,
            traffic_penalty=comp.traffic_penalty,
            eta_minutes=comp.eta_minutes,
        )


# ── AI refuel-advice schemas ───────────────────────────────────────────────────


class RecommendationRequest(BaseModel):
    """Input for the AI refuel-advice endpoint."""

    lat: float = Field(ge=-90, le=90, description="User latitude (WGS84)")
    lon: float = Field(ge=-180, le=180, description="User longitude (WGS84)")
    fuel_type: FuelType
    municipio: str
    # Optional: the server derives the real comarca from ``municipio``. Accepted
    # only as a fallback for municipios outside the comarca map.
    comarca: str | None = Field(default=None)
    # Coordinates of the station being advised about. When present, the model's
    # `distancia` feature is computed station-side (matching training); when
    # absent it falls back to the user's (lat, lon) as a proxy.
    station_lat: float | None = Field(default=None, ge=-90, le=90)
    station_lon: float | None = Field(default=None, ge=-180, le=180)
    precio_actual: float = Field(gt=0, description="Current fuel price at the station (€/L)")


class RecommendationResponse(BaseModel):
    """AI refuel-advice response from the Random Forest model."""

    veredicto: Literal["REPOSTA AHORA", "ESPERA"]
    precio_actual: float
    precio_predicho: float
    variacion_pct: float
    advice: str
    confianza: float
