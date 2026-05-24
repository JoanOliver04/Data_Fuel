"""SQLAlchemy repository for ML retraining-run history."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.training_run import TrainingRunORM
from app.ml.lifecycle.history import TrainingRunRecord


class TrainingRunRepository:
    """Append-only persistence for retraining attempts.

    Follows the repository convention used across the codebase: writes flush
    (so the generated id is available) but do not commit — the caller owns the
    transaction boundary.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, run: TrainingRunRecord) -> int:
        """Insert one run and return its primary key."""
        orm = TrainingRunORM(
            status=run.status.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_seconds=run.duration_seconds,
            version=run.version,
            dataset_rows=run.dataset_rows,
            mae=run.mae,
            rmse=run.rmse,
            r2=run.r2,
            r2_oob=run.r2_oob,
            reason=run.reason,
        )
        self._session.add(orm)
        await self._session.flush()
        return orm.id

    async def list_recent(self, limit: int = 20) -> list[TrainingRunORM]:
        """Return the most recent runs, newest first."""
        stmt = (
            select(TrainingRunORM)
            .order_by(TrainingRunORM.started_at.desc(), TrainingRunORM.id.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
