"""Typed schemas for the intelligent alert system.

These are the only shapes that cross the alert API boundary. Per-type required
fields are validated strictly at creation so an evaluator never runs on an
under-specified alert.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.entities.fuel_type import FuelType

AlertType = Literal[
    "PRICE_BELOW_THRESHOLD",
    "PRICE_CHANGE",
    "FAVORITE_STATION_CHANGE",
    "CHEAPEST_BRAND",
    "WEEKLY_SUMMARY",
    "WAIT_VS_REFUEL_SIGNAL",
    "PREDICTION_TREND",
    "TOTAL_COST_DROP",
]
NotificationChannel = Literal["in_app"]
TriggerSource = Literal["deterministic", "llm"]

# Fields each alert type requires beyond fuel_type. Adding a type here keeps
# validation declarative — no branching logic to touch.
_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "PRICE_BELOW_THRESHOLD": ("threshold_price",),
    "PRICE_CHANGE": ("threshold_pct",),
    "FAVORITE_STATION_CHANGE": ("station_id",),
    "CHEAPEST_BRAND": ("brand", "latitude", "longitude"),
    "WEEKLY_SUMMARY": (),
    "WAIT_VS_REFUEL_SIGNAL": ("threshold_pct", "latitude", "longitude"),
    "PREDICTION_TREND": ("latitude", "longitude"),
    "TOTAL_COST_DROP": ("threshold_pct", "latitude", "longitude"),
}


class AlertBase(BaseModel):
    """Shared, user-settable alert configuration."""

    user_identifier: str = Field(min_length=1, max_length=120)
    alert_type: AlertType
    fuel_type: str
    station_id: int | None = None
    brand: str | None = Field(default=None, max_length=120)
    threshold_price: Decimal | None = Field(default=None, gt=0, le=20)
    threshold_pct: float | None = Field(default=None, gt=0, le=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float = Field(default=10.0, gt=0, le=200)
    liters: float = Field(default=50.0, gt=0, le=200)
    cooldown_minutes: int | None = Field(default=None, ge=0, le=20160)

    @model_validator(mode="after")
    def _validate(self) -> AlertBase:
        try:
            FuelType(self.fuel_type)
        except ValueError as exc:
            raise ValueError(f"Invalid fuel_type: {self.fuel_type!r}") from exc
        missing = [f for f in _REQUIRED_FIELDS[self.alert_type] if getattr(self, f) is None]
        if missing:
            raise ValueError(f"{self.alert_type} requires: {', '.join(missing)}")
        return self


class AlertCreate(AlertBase):
    """Payload for creating an alert."""


class AlertUpdate(BaseModel):
    """Partial update — only mutable fields, all optional."""

    is_enabled: bool | None = None
    threshold_price: Decimal | None = Field(default=None, gt=0, le=20)
    threshold_pct: float | None = Field(default=None, gt=0, le=100)
    radius_km: float | None = Field(default=None, gt=0, le=200)
    liters: float | None = Field(default=None, gt=0, le=200)
    brand: str | None = Field(default=None, max_length=120)
    cooldown_minutes: int | None = Field(default=None, ge=0, le=20160)


class AlertOut(BaseModel):
    """Public representation of a stored alert."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_identifier: str
    alert_type: AlertType
    fuel_type: str
    station_id: int | None
    brand: str | None
    threshold_price: Decimal | None
    threshold_pct: float | None
    latitude: float | None
    longitude: float | None
    radius_km: float
    liters: float
    is_enabled: bool
    cooldown_minutes: int
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationOut(BaseModel):
    """Public representation of a delivered notification."""

    id: int
    alert_id: int | None
    user_identifier: str
    alert_type: str
    channel: NotificationChannel
    title: str
    message: str
    source: TriggerSource
    data: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
