"""DTOs for the training-run history (status enum + persisted record).

These are pure data carriers with no I/O. The orchestrator builds a
``TrainingRunRecord`` for every retraining attempt — success, rejection, or
failure — and ``TrainingRunRepository`` persists it. Keeping the DTO here (not
in the repository) lets the service layer assemble runs without importing the
infrastructure layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TrainingRunStatus(StrEnum):
    """Terminal state of a single retraining attempt."""

    ACTIVATED = "activated"  # trained, passed the gate, swapped live
    REJECTED = "rejected"  # trained but rejected by the acceptance gate
    FAILED = "failed"  # export / training / activation errored out


@dataclass(frozen=True, slots=True)
class TrainingRunRecord:
    """Everything worth persisting about one retraining attempt."""

    status: TrainingRunStatus
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    version: str | None = None
    dataset_rows: int | None = None
    mae: float | None = None
    rmse: float | None = None
    r2: float | None = None
    r2_oob: float | None = None
    reason: str | None = None
