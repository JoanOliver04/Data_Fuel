"""SQLAlchemy repository for gas stations."""

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import CursorResult, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.station import StationORM

# Safe chunk size for SQLite's 999-parameter limit: 999 // 16 cols ≈ 62.
_CHUNK = 60


class StationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, rows: list[dict[str, Any]]) -> int:
        """Bulk upsert stations. Skips created_at on conflict to preserve original value."""
        if not rows:
            return 0

        update_cols = {
            col.key
            for col in StationORM.__table__.columns
            if col.key not in ("id", "created_at")
        }
        total = 0
        for i in range(0, len(rows), _CHUNK):
            chunk = rows[i : i + _CHUNK]
            stmt = sqlite_insert(StationORM).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={k: getattr(stmt.excluded, k) for k in update_cols},
            )
            result = cast(CursorResult[Any], await self._session.execute(stmt))
            total += result.rowcount
        return total

    async def get_by_id(self, station_id: int) -> StationORM | None:
        return await self._session.get(StationORM, station_id)

    async def list_all(
        self,
        province: str | None = None,
        municipality: str | None = None,
    ) -> Sequence[StationORM]:
        q = select(StationORM)
        if province:
            q = q.where(StationORM.province.ilike(f"%{province}%"))
        if municipality:
            q = q.where(StationORM.municipality.ilike(f"%{municipality}%"))
        result = await self._session.execute(q)
        return result.scalars().all()
