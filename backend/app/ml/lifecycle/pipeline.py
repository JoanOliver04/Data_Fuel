"""End-to-end retraining orchestrator.

Pipeline stages::

    export dataset → train (in a worker thread) → version + write sidecars
    → evaluate vs active model → activate (atomic) → hot-reload → invalidate
    caches → record history

Design notes:
- ``run()`` is a coroutine. Only the CPU-bound training step is offloaded to a
  thread (``asyncio.to_thread``) so the event loop stays responsive; the GIL is
  released inside scikit-learn's native code, so concurrent requests keep being
  served. The rest is cheap async DB / filesystem work on the running loop.
- The active model is **never** replaced by an invalid or degraded candidate:
  rejection short-circuits before activation, and a reload failure after
  activation rolls the active pointer back to the previous version.
- Every attempt — activated, rejected, or failed — is recorded in the
  training-run history. History persistence is best-effort: a DB write failure
  is logged but does not change the pipeline outcome.
- All collaborators are injectable, so tests run without a database, MITECO, or
  a real Random Forest fit.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.cache import recommendations_cache
from app.core.config import Settings, get_settings
from app.core.metrics import (
    ml_model_activation_failures_total,
    ml_retrain_dataset_rows,
    ml_retrain_duration_seconds,
    ml_retrain_total,
)
from app.infrastructure.database.session import get_session_factory
from app.ml.inference.model_loader import reload_modelo
from app.ml.lifecycle.evaluation import AcceptanceThresholds, evaluate_candidate
from app.ml.lifecycle.exceptions import ArtifactError
from app.ml.lifecycle.history import TrainingRunRecord, TrainingRunStatus
from app.ml.lifecycle.versioning import (
    ArtifactStore,
    build_metadata,
    build_metrics,
    new_version_id,
)
from app.ml.training.entrenar import ejecutar_entrenamiento
from app.repositories.training_run_repository import TrainingRunRepository
from app.services.dataset_export_service import count_data_rows, export_dataset

log = logging.getLogger(__name__)

ExportFn = Callable[[Path], Awaitable[None]]
TrainFn = Callable[[Path, Path], dict[str, Any]]
ReloadFn = Callable[[], bool]
RecordFn = Callable[[TrainingRunRecord], Awaitable[None]]


def thresholds_from_settings(settings: Settings) -> AcceptanceThresholds:
    """Build the acceptance gate's tolerances from runtime settings."""
    return AcceptanceThresholds(
        max_mae=settings.retrain_max_mae,
        min_r2=settings.retrain_min_r2,
        max_mae_regression_pct=settings.retrain_max_mae_regression_pct,
        max_r2_absolute_drop=settings.retrain_max_r2_absolute_drop,
    )


@dataclass(frozen=True, slots=True)
class RetrainOutcome:
    """Result of one retraining attempt."""

    status: TrainingRunStatus
    version: str | None
    reason: str | None
    metrics: dict[str, float | None] | None
    duration_seconds: float

    @property
    def activated(self) -> bool:
        return self.status is TrainingRunStatus.ACTIVATED


class RetrainPipeline:
    """Coordinates the full retraining lifecycle for the recommendation model."""

    def __init__(
        self,
        *,
        store: ArtifactStore | None = None,
        thresholds: AcceptanceThresholds | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        export_fn: ExportFn | None = None,
        train_fn: TrainFn | None = None,
        reload_fn: ReloadFn | None = None,
        cache_clear: Callable[[], None] | None = None,
        record_fn: RecordFn | None = None,
        app_version: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        settings = get_settings()
        self._store = store or ArtifactStore()
        self._thresholds = thresholds or thresholds_from_settings(settings)
        self._session_factory = session_factory  # resolved lazily so it binds the live loop
        self._export_fn = export_fn or self._default_export
        self._train_fn = train_fn or ejecutar_entrenamiento
        self._reload_fn = reload_fn or reload_modelo
        self._cache_clear = cache_clear or recommendations_cache.reset
        self._record_fn = record_fn or self._default_record
        self._app_version = app_version if app_version is not None else settings.app_version
        self._clock = clock or (lambda: datetime.now(UTC))

    async def run(self) -> RetrainOutcome:
        """Run one retraining attempt and return its outcome."""
        started = self._clock()
        version = self._store.unique_version(new_version_id(started))
        dataset_rows: int | None = None
        recorded_version: str | None = None
        log.info("Retrain started: candidate_version=%s", version)

        try:
            with tempfile.TemporaryDirectory(prefix="datafuel_retrain_") as tmp:
                csv_path = Path(tmp) / "datos.csv"
                await self._export_fn(csv_path)
                dataset_rows = count_data_rows(csv_path)
                ml_retrain_dataset_rows.set(dataset_rows)
                log.info("Dataset exported: rows=%d", dataset_rows)

                self._store.prepare_version_dir(version)
                model_path = self._store.version_model_path(version)
                artifact = await asyncio.to_thread(self._train_fn, csv_path, model_path)

            candidate = build_metrics(artifact)
            metadata = build_metadata(
                artifact, version, dataset_rows=dataset_rows, app_version=self._app_version
            )
            self._store.write_sidecars(version, metadata, candidate)
            recorded_version = version
            log.info("Model trained and versioned: version=%s metrics=%s", version, candidate)

            baseline = self._store.read_active_metrics()
            decision = evaluate_candidate(candidate, baseline, self._thresholds)

            if not decision.accepted:
                await self._emit(
                    TrainingRunStatus.REJECTED,
                    started,
                    recorded_version,
                    dataset_rows,
                    candidate,
                    decision.reason,
                )
                log.warning(
                    "Retrain outcome: REJECTED version=%s reason=%s", version, decision.reason
                )
                return self._outcome(
                    TrainingRunStatus.REJECTED,
                    recorded_version,
                    decision.reason,
                    candidate,
                    started,
                )

            previous_version = self._store.active_version()
            self._store.activate(version)
            log.info("Activated model: version=%s previous=%s", version, previous_version)

            if not self._reload_fn():
                ml_model_activation_failures_total.inc()
                if previous_version is not None:
                    self._store.activate(previous_version)
                    self._reload_fn()
                raise ArtifactError(
                    f"model reload failed after activating {version}; "
                    f"rolled back to {previous_version}"
                )

            self._cache_clear()
            await self._emit(
                TrainingRunStatus.ACTIVATED,
                started,
                recorded_version,
                dataset_rows,
                candidate,
                None,
            )
            log.info("Retrain outcome: ACTIVATED version=%s", version)
            return self._outcome(
                TrainingRunStatus.ACTIVATED, recorded_version, None, candidate, started
            )

        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            log.exception("Retrain failed: candidate_version=%s", version)
            await self._emit(
                TrainingRunStatus.FAILED, started, recorded_version, dataset_rows, None, reason
            )
            return self._outcome(TrainingRunStatus.FAILED, recorded_version, reason, None, started)

    # ── Collaborator defaults ────────────────────────────────────────────────
    async def _default_export(self, output_path: Path) -> None:
        factory = self._session_factory or get_session_factory()
        await export_dataset(output_path, factory)

    async def _default_record(self, record: TrainingRunRecord) -> None:
        factory = self._session_factory or get_session_factory()
        async with factory() as session:
            await TrainingRunRepository(session).record(record)
            await session.commit()

    # ── Internals ────────────────────────────────────────────────────────────
    def _outcome(
        self,
        status: TrainingRunStatus,
        version: str | None,
        reason: str | None,
        metrics: dict[str, float | None] | None,
        started: datetime,
    ) -> RetrainOutcome:
        duration = (self._clock() - started).total_seconds()
        ml_retrain_total.labels(status=status.value).inc()
        ml_retrain_duration_seconds.observe(duration)
        return RetrainOutcome(
            status=status,
            version=version,
            reason=reason,
            metrics=metrics,
            duration_seconds=duration,
        )

    async def _emit(
        self,
        status: TrainingRunStatus,
        started: datetime,
        version: str | None,
        dataset_rows: int | None,
        metrics: dict[str, float | None] | None,
        reason: str | None,
    ) -> None:
        finished = self._clock()
        record = TrainingRunRecord(
            status=status,
            started_at=started,
            finished_at=finished,
            duration_seconds=(finished - started).total_seconds(),
            version=version,
            dataset_rows=dataset_rows,
            mae=metrics.get("mae") if metrics else None,
            rmse=metrics.get("rmse") if metrics else None,
            r2=metrics.get("r2") if metrics else None,
            r2_oob=metrics.get("r2_oob") if metrics else None,
            reason=reason,
        )
        try:
            await self._record_fn(record)
        except Exception:
            log.exception("Failed to persist training-run history (status=%s)", status)
