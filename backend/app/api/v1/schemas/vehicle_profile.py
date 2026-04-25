"""Pydantic v2 schemas for the vehicle-profiles API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities.vehicle_profile import DrivingStyle


class VehicleProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    fuel_consumption_per_100km: float = Field(ge=0.0, le=50.0)
    tank_capacity_litres: float = Field(gt=0.0, le=300.0)
    driving_style: DrivingStyle = DrivingStyle.MIXED
    # Used only to compute the stored km_cost_per_km reference value on save.
    reference_fuel_price: float = Field(default=1.50, gt=0.0, le=10.0)


class VehicleProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    fuel_consumption_per_100km: float | None = Field(default=None, ge=0.0, le=50.0)
    tank_capacity_litres: float | None = Field(default=None, gt=0.0, le=300.0)
    driving_style: DrivingStyle | None = None
    reference_fuel_price: float | None = Field(default=None, gt=0.0, le=10.0)


class VehicleProfileOut(BaseModel):
    id: int
    name: str
    fuel_consumption_per_100km: float
    tank_capacity_litres: float
    km_cost_per_km: float
    driving_style: DrivingStyle
    created_at: datetime

    model_config = {"from_attributes": True}


class KmCostEstimate(BaseModel):
    consumption_l_per_100km: float
    fuel_price_eur_per_l: float
    km_cost_eur_per_km: float
