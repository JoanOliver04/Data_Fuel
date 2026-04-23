"""Domain entities."""

from app.domain.entities.fuel_type import FuelType
from app.domain.entities.price import Price
from app.domain.entities.station import Coordinates, Station

__all__ = ["Coordinates", "FuelType", "Price", "Station"]
