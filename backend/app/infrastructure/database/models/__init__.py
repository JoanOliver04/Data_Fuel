"""ORM model registry. Importing here ensures models are registered with Base.metadata."""

from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM
from app.infrastructure.database.models.vehicle_profile import VehicleProfileORM

__all__ = ["PriceHistoryORM", "StationORM", "VehicleProfileORM"]
