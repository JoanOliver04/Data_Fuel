"""SQLAlchemy repository for fuel price history."""

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.price_history import PriceHistoryORM

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
