"""Integration tests for TrainingRunRepository (in-memory SQLite round-trip)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.lifecycle.history import TrainingRunRecord, TrainingRunStatus
from app.repositories.training_run_repository import TrainingRunRepository

_T0 = datetime(2026, 5, 24, 3, 0, 0, tzinfo=UTC)


def _activated(started: datetime, *, version: str) -> TrainingRunRecord:
    return TrainingRunRecord(
        status=TrainingRunStatus.ACTIVATED,
        started_at=started,
        finished_at=started + timedelta(seconds=42),
        duration_seconds=42.0,
        version=version,
        dataset_rows=12345,
        mae=0.011,
        rmse=0.017,
        r2=0.93,
        r2_oob=0.90,
    )


async def test_record_returns_id_and_persists(db: AsyncSession) -> None:
    repo = TrainingRunRepository(db)
    run_id = await repo.record(_activated(_T0, version="2026-05-24T03-00-00"))
    await db.commit()

    assert run_id > 0
    rows = await repo.list_recent()
    assert len(rows) == 1
    row = rows[0]
    assert row.status == "activated"
    assert row.version == "2026-05-24T03-00-00"
    assert row.dataset_rows == 12345
    assert row.r2 == 0.93
    assert row.reason is None
    assert row.created_at is not None  # server_default populated


async def test_record_failed_run_with_null_metrics(db: AsyncSession) -> None:
    repo = TrainingRunRepository(db)
    await repo.record(
        TrainingRunRecord(
            status=TrainingRunStatus.FAILED,
            started_at=_T0,
            finished_at=_T0 + timedelta(seconds=3),
            duration_seconds=3.0,
            reason="dataset export failed: no rows in price_history",
        )
    )
    await db.commit()

    row = (await repo.list_recent())[0]
    assert row.status == "failed"
    assert row.mae is None and row.r2 is None and row.version is None
    assert "export failed" in (row.reason or "")


async def test_record_rejected_run_keeps_reason(db: AsyncSession) -> None:
    repo = TrainingRunRepository(db)
    await repo.record(
        TrainingRunRecord(
            status=TrainingRunStatus.REJECTED,
            started_at=_T0,
            finished_at=_T0 + timedelta(seconds=50),
            duration_seconds=50.0,
            version="2026-05-31T03-00-00",
            dataset_rows=20000,
            mae=0.06,
            rmse=0.08,
            r2=0.70,
            r2_oob=0.68,
            reason="MAE 0.06000 worse than allowed 0.05500",
        )
    )
    await db.commit()

    row = (await repo.list_recent())[0]
    assert row.status == "rejected"
    assert "worse than allowed" in (row.reason or "")


async def test_list_recent_orders_newest_first_and_limits(db: AsyncSession) -> None:
    repo = TrainingRunRepository(db)
    for i in range(5):
        await repo.record(
            _activated(_T0 + timedelta(days=i), version=f"2026-05-{24 + i:02d}T03-00-00")
        )
    await db.commit()

    recent = await repo.list_recent(limit=3)
    assert len(recent) == 3
    versions = [r.version for r in recent]
    assert versions == [
        "2026-05-28T03-00-00",
        "2026-05-27T03-00-00",
        "2026-05-26T03-00-00",
    ]
