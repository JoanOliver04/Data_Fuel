"""Unit tests for RetrainPipeline with fully injected collaborators.

No database, no MITECO, no real Random Forest: a fake export writes a tiny CSV
and a fake trainer writes a dummy pkl and returns a metrics dict. This isolates
the orchestration logic (versioning, evaluation, activation, rollback, history).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import joblib

from app.ml.lifecycle.evaluation import AcceptanceThresholds
from app.ml.lifecycle.history import TrainingRunRecord, TrainingRunStatus
from app.ml.lifecycle.pipeline import RetrainPipeline
from app.ml.lifecycle.versioning import ArtifactStore


def _make_export(rows: int = 120) -> Callable[[Path], Any]:
    async def _export(output_path: Path) -> None:
        lines = ["fecha,precio"] + [f"2026-01-0{i % 9 + 1},1.5" for i in range(rows)]
        output_path.write_text("\n".join(lines), encoding="utf-8")

    return _export


def _make_train(
    mae: float, r2: float, *, rmse: float = 0.02
) -> Callable[[Path, Path], dict[str, Any]]:
    def _train(csv_path: Path, model_path: Path) -> dict[str, Any]:
        artifact: dict[str, Any] = {
            "model": "fake-forest",
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "r2_oob": r2 - 0.01,
            "trained_at": "2026-05-24T03:00:00+00:00",
            "sklearn_version": "1.5.0",
            "features_names": ["distancia", "mes"],
            "hyperparameters": {"n_estimators": 300},
            "n_train_rows": 96,
            "n_test_rows": 24,
        }
        joblib.dump(artifact, model_path)
        return artifact

    return _train


class _Recorder:
    def __init__(self) -> None:
        self.records: list[TrainingRunRecord] = []

    async def __call__(self, record: TrainingRunRecord) -> None:
        self.records.append(record)


def _pipeline(
    store: ArtifactStore,
    recorder: _Recorder,
    *,
    train: Callable[[Path, Path], dict[str, Any]],
    reload_fn: Callable[[], bool] | None = None,
    cache_clear: Callable[[], None] | None = None,
    thresholds: AcceptanceThresholds | None = None,
) -> RetrainPipeline:
    return RetrainPipeline(
        store=store,
        thresholds=thresholds or AcceptanceThresholds(),
        export_fn=_make_export(),
        train_fn=train,
        reload_fn=reload_fn or (lambda: True),
        cache_clear=cache_clear or (lambda: None),
        record_fn=recorder,
        app_version="test",
        clock=_make_clock(),
    )


def _make_clock() -> Callable[[], datetime]:
    state = {"t": datetime(2026, 5, 24, 3, 0, 0, tzinfo=UTC)}

    def _clock() -> datetime:
        state["t"] += timedelta(seconds=1)
        return state["t"]

    return _clock


# ── happy path ─────────────────────────────────────────────────────────────


async def test_first_model_is_activated(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    rec = _Recorder()
    cache_calls = {"n": 0}

    def _clear() -> None:
        cache_calls["n"] += 1

    pipeline = _pipeline(store, rec, train=_make_train(0.04, 0.90), cache_clear=_clear)
    outcome = await pipeline.run()

    assert outcome.status is TrainingRunStatus.ACTIVATED
    assert outcome.activated is True
    assert outcome.version is not None
    assert store.active_version() == outcome.version
    assert store.active_model_path.exists()
    assert cache_calls["n"] == 1  # cache invalidated once on activation
    assert rec.records[-1].status is TrainingRunStatus.ACTIVATED
    assert rec.records[-1].mae == 0.04
    assert rec.records[-1].dataset_rows == 120


async def test_better_second_model_replaces_active(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    rec = _Recorder()
    await _pipeline(store, rec, train=_make_train(0.05, 0.88)).run()
    v1 = store.active_version()

    await _pipeline(store, rec, train=_make_train(0.03, 0.93)).run()
    v2 = store.active_version()

    assert v2 is not None and v2 != v1
    assert len(store.list_versions()) == 2


# ── rejection ────────────────────────────────────────────────────────────────


async def test_degraded_model_is_rejected_and_active_kept(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    rec = _Recorder()
    await _pipeline(store, rec, train=_make_train(0.04, 0.92)).run()
    v1 = store.active_version()

    # +50% MAE and big R2 drop → rejected by default thresholds.
    out = await _pipeline(store, rec, train=_make_train(0.06, 0.80)).run()

    assert out.status is TrainingRunStatus.REJECTED
    assert store.active_version() == v1  # active model unchanged
    assert len(store.list_versions()) == 2  # candidate still archived
    assert rec.records[-1].status is TrainingRunStatus.REJECTED
    assert rec.records[-1].reason is not None


# ── failures ─────────────────────────────────────────────────────────────────


async def test_export_failure_is_recorded_as_failed(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    rec = _Recorder()

    async def _boom(output_path: Path) -> None:
        raise RuntimeError("no rows in price_history")

    pipeline = RetrainPipeline(
        store=store,
        export_fn=_boom,
        train_fn=_make_train(0.04, 0.9),
        reload_fn=lambda: True,
        cache_clear=lambda: None,
        record_fn=rec,
        app_version="test",
    )
    out = await pipeline.run()

    assert out.status is TrainingRunStatus.FAILED
    assert "no rows" in (out.reason or "")
    assert store.active_version() is None  # nothing activated
    assert rec.records[-1].status is TrainingRunStatus.FAILED
    assert rec.records[-1].version is None


async def test_training_failure_is_recorded_as_failed(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    rec = _Recorder()

    def _bad_train(csv_path: Path, model_path: Path) -> dict[str, Any]:
        raise ValueError("CSV has 3 rows; minimum required is 100")

    pipeline = _pipeline(store, rec, train=_bad_train)
    out = await pipeline.run()

    assert out.status is TrainingRunStatus.FAILED
    assert rec.records[-1].status is TrainingRunStatus.FAILED


async def test_reload_failure_rolls_back_to_previous(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    rec = _Recorder()
    # First model activates cleanly.
    await _pipeline(store, rec, train=_make_train(0.05, 0.90), reload_fn=lambda: True).run()
    v1 = store.active_version()

    # Second model trains/accepts but reload fails → must roll back to v1.
    out = await _pipeline(store, rec, train=_make_train(0.04, 0.93), reload_fn=lambda: False).run()

    assert out.status is TrainingRunStatus.FAILED
    assert "rolled back" in (out.reason or "")
    assert store.active_version() == v1  # disk rolled back to the working model


async def test_history_failure_does_not_change_outcome(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    async def _bad_record(record: TrainingRunRecord) -> None:
        raise RuntimeError("db down")

    pipeline = RetrainPipeline(
        store=store,
        export_fn=_make_export(),
        train_fn=_make_train(0.04, 0.9),
        reload_fn=lambda: True,
        cache_clear=lambda: None,
        record_fn=_bad_record,
        app_version="test",
    )
    out = await pipeline.run()
    assert out.status is TrainingRunStatus.ACTIVATED  # history failure is non-fatal
    assert store.active_version() == out.version
