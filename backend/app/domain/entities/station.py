"""Gas station domain entity."""

from dataclasses import dataclass, field

from app.domain.entities.fuel_type import FuelType


@dataclass(frozen=True, slots=True)
class Coordinates:
    """Geographic coordinates (WGS84)."""

    latitude: float
    longitude: float


@dataclass(slots=True)
class Station:
    """A gas station with current fuel prices.

    `prices` maps each FuelType to its current price in €/L,
    or None if the station does not sell that fuel.
    """

    id: int
    brand: str
    address: str
    locality: str
    municipality: str
    province: str
    postal_code: str
    coordinates: Coordinates
    schedule: str
    prices: dict[FuelType, float | None] = field(default_factory=dict)
