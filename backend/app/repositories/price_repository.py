"""SQLAlchemy repository for fuel price history."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM

# Safe chunk size: 999 // 4 cols = 249.
_CHUNK = 200

# Cap the in-process Ridge predictor's training pull. A multi-GB history would
# otherwise be materialised in full on every cold-cache predict, freezing the
# event loop and risking OOM. We take the most-recent rows (an index-ordered
# range scan on ix_price_history_fuel_time, no full-table scan) — recent prices
# are the most predictive, and the cap is large enough not to starve the model.
_TRAIN_ROW_CAP = 100_000


class PriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_many(self, rows: list[dict[str, Any]]) -> int:
        """Bulk-insert price history rows. No conflict resolution — each row is a new observation."""
        if not rows:
            return 0
        total = 0
        for i in range(0, len(rows), _CHUNK):
            result = cast(
                CursorResult[Any],
                await self._session.execute(
                    insert(PriceHistoryORM).values(rows[i : i + _CHUNK])
                ),
            )
            total += result.rowcount
        return total

    async def get_price_history(
        self, station_id: int, fuel_type: FuelType, days: int = 30
    ) -> list[dict[str, Any]]:
        """Return recent price points for a station/fuel_type sorted by time."""
        cutoff = datetime.now(tz=UTC) - timedelta(days=days)
        stmt = (
            select(PriceHistoryORM.recorded_at, PriceHistoryORM.price)
            .where(
                PriceHistoryORM.station_id == station_id,
                PriceHistoryORM.fuel_type == fuel_type,
                PriceHistoryORM.recorded_at >= cutoff,
            )
            .order_by(PriceHistoryORM.recorded_at)
        )
        result = await self._session.execute(stmt)
        return [{"recorded_at": row.recorded_at, "price": float(row.price)} for row in result]

    async def get_training_data(
        self,
        fuel_type: FuelType,
        *,
        limit: int = _TRAIN_ROW_CAP,
    ) -> list[dict[str, Any]]:
        """Return the most-recent price rows joined with station metadata for ML
        training, capped at ``limit`` so the pull stays bounded regardless of
        total history size.
        """
        stmt = (
            select(
                PriceHistoryORM.price,
                PriceHistoryORM.recorded_at,
                StationORM.brand,
                StationORM.province,
            )
            .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
            .where(PriceHistoryORM.fuel_type == fuel_type)
            .order_by(PriceHistoryORM.recorded_at.desc())
            .limit(limit)
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
