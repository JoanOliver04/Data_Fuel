"""SQLAlchemy repository for fuel price history."""

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM

# Safe chunk size: 999 // 4 cols = 249.
_CHUNK = 200


class PriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_many(self, rows: list[dict]) -> int:
        """Bulk-insert price history rows. No conflict resolution — each row is a new observation."""
        if not rows:
            return 0
        total = 0
        for i in range(0, len(rows), _CHUNK):
            result = await self._session.execute(
                sqlite_insert(PriceHistoryORM).values(rows[i : i + _CHUNK])
            )
            total += result.rowcount
        return total

    async def get_training_data(self, fuel_type: FuelType) -> list[dict]:
        """Return price rows joined with station metadata for ML training."""
        stmt = (
            select(
                PriceHistoryORM.price,
                PriceHistoryORM.recorded_at,
                StationORM.brand,
                StationORM.province,
            )
            .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
            .where(PriceHistoryORM.fuel_type == fuel_type)
        )
        result = await self._session.execute(stmt)
        return [
            {
                "price": float(row.price),
                "recorded_at": row.recorded_at,
                "brand": row.brand,
                "province": row.province,
            }
            for row in result
        ]
