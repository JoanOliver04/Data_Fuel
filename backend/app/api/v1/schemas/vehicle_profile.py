"""Pydantic v2 schemas for the vehicle-profiles API.

Three consumption values are required so K can be selected dynamically from
the trip distance toward each station. All consumptions are validated to a
realistic 1.0-25.0 L/100km range; tanks to 10-200 L.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.vehicle_profile import ConsumptionMode, DrivingStyle

CONSUMPTION_MIN = 1.0
CONSUMPTION_MAX = 25.0
TANK_MIN = 10.0
TANK_MAX = 200.0


class VehicleProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    fuel_consumption_urban: float = Field(ge=CONSUMPTION_MIN, le=CONSUMPTION_MAX)
    fuel_consumption_mixed: float = Field(ge=CONSUMPTION_MIN, le=CONSUMPTION_MAX)
    fuel_consumption_highway: float = Field(ge=CONSUMPTION_MIN, le=CONSUMPTION_MAX)
    tank_capacity_litres: float = Field(ge=TANK_MIN, le=TANK_MAX)
    driving_style: DrivingStyle = DrivingStyle.MIXED
    # Used only to compute the stored km_cost_per_km reference value on save.
    reference_fuel_price: float = Field(default=1.50, gt=0.0, le=10.0)


class VehicleProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    fuel_consumption_urban: float | None = Field(
        default=None, ge=CONSUMPTION_MIN, le=CONSUMPTION_MAX
    )
    fuel_consumption_mixed: float | None = Field(
        default=None, ge=CONSUMPTION_MIN, le=CONSUMPTION_MAX
    )
    fuel_consumption_highway: float | None = Field(
        default=None, ge=CONSUMPTION_MIN, le=CONSUMPTION_MAX
    )
    tank_capacity_litres: float | None = Field(default=None, ge=TANK_MIN, le=TANK_MAX)
    driving_style: DrivingStyle | None = None
    reference_fuel_price: float | None = Field(default=None, gt=0.0, le=10.0)


class VehicleProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    fuel_consumption_urban: float
    fuel_consumption_mixed: float
    fuel_consumption_highway: float
    tank_capacity_litres: float
    km_cost_per_km: float
    driving_style: DrivingStyle
    created_at: datetime


class KmCostEstimate(BaseModel):
    consumption_l_per_100km: float
    fuel_price_eur_per_l: float
    km_cost_eur_per_km: float


class KmCostBreakdown(BaseModel):
    """Per-mode K preview: what €/km would apply for each distance band."""

    fuel_price_eur_per_l: float
    urban_km_cost: float
    mixed_km_cost: float
    highway_km_cost: float


class AppliedConsumption(BaseModel):
    """Which consumption mode was applied at calculation time."""

    mode: ConsumptionMode
    consumption_l_per_100km: float
