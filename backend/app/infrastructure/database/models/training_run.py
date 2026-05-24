"""ORM model for ML retraining-run history (one row per retraining attempt)."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TrainingRunORM(Base):
    """Audit trail of every retraining attempt: timings, metrics, and outcome.

    Rows are append-only and support a future training-history dashboard.
    Metric columns are nullable because a run that fails before training (e.g.
    dataset export error) has no metrics to record.
    """

    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # "activated" | "rejected" | "failed" (see TrainingRunStatus).
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    # Archived artifact version id; null when the run failed before versioning.
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dataset_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)

    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2_oob: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Rejection or failure explanation; null on a clean activation.
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_training_runs_started_at", "started_at"),)
