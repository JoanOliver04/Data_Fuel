"""ORM model registry. Importing here ensures models are registered with Base.metadata."""

from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM

__all__ = ["PriceHistoryORM", "StationORM"]
