"""Historical fuel price entity."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.fuel_type import FuelType


@dataclass(frozen=True, slots=True)
class Price:
    """A single fuel price observation at a given station and time."""

    station_id: int
    fuel_type: FuelType
    value: float
    recorded_at: datetime
