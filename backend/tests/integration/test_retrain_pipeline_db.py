"""Integration test: RetrainPipeline persists history through the real repository.

Uses the in-memory DB factory (default record path) but still injects fake
export/train so no MITECO call or real forest fit happens.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database import session as db_session
from app.ml.lifecycle.history import TrainingRunStatus
from app.ml.lifecycle.pipeline import RetrainPipeline
from app.ml.lifecycle.versioning import ArtifactStore
from app.repositories.training_run_repository import TrainingRunRepository


async def _export(output_path: Path) -> None:
    output_path.write_text("fecha,precio\n2026-01-01,1.5\n2026-01-02,1.6\n", encoding="utf-8")


def _train(csv_path: Path, model_path: Path) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "model": "fake",
        "mae": 0.03,
        "rmse": 0.05,
        "r2": 0.9,
        "r2_oob": 0.88,
        "trained_at": "2026-05-24T03:00:00+00:00",
        "features_names": ["a"],
        "hyperparameters": {},
    }
    joblib.dump(artifact, model_path)
    return artifact


async def test_pipeline_persists_history_via_repository(engine: Any, tmp_path: Path) -> None:
    factory: async_sessionmaker[AsyncSession] = db_session.get_session_factory()
    store = ArtifactStore(tmp_path)

    pipeline = RetrainPipeline(
        store=store,
        session_factory=factory,
        export_fn=_export,
        train_fn=_train,
        reload_fn=lambda: True,
        cache_clear=lambda: None,
        app_version="test",
    )
    outcome = await pipeline.run()
    assert outcome.status is TrainingRunStatus.ACTIVATED

    async with factory() as session:
        rows = await TrainingRunRepository(session).list_recent()
    assert len(rows) == 1
    assert rows[0].status == "activated"
    assert rows[0].version == outcome.version
    assert rows[0].r2 == 0.9
    assert rows[0].dataset_rows == 2
