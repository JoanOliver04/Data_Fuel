"""FastAPI lifespan: DB init, optional startup sync, and scheduler management."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.alerts.models import AlertORM, NotificationORM  # noqa: F401
from app.core.config import get_settings
from app.core.scheduler import (
    add_alert_job,
    add_retrain_job,
    attach_scheduler_metrics,
    create_scheduler,
)
from app.domain.services.prediction_service import PredictionService
from app.infrastructure.database import Base, get_engine, get_session_factory
from app.infrastructure.database.models import (  # noqa: F401
    PriceHistoryORM,
    StationORM,
    TrainingRunORM,
    VehicleProfileORM,
)
from app.ml.inference.model_loader import get_modelo, load_modelo
from app.ml.xai import shap_explainer
from app.services.sync_service import SyncService

log = logging.getLogger(__name__)

# alembic.ini lives at backend/alembic.ini; this file is at backend/app/core/lifespan.py.
_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


async def _run_alembic_upgrade() -> None:
    """Apply pending migrations to the live DB. Idempotent.

    Runs in a worker thread because alembic's env.py spins up its own
    ``asyncio.run()`` loop to drive the async engine, which would conflict
    with the lifespan's already-running event loop.
    """
    cfg = Config(str(_ALEMBIC_INI))
    await asyncio.to_thread(command.upgrade, cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database tables verified / created")

    # Apply pending Alembic migrations. ``create_all`` only creates missing
    # tables; it does not migrate existing ones (e.g. add new columns), so a
    # legacy DB schema would silently break inserts. Running ``upgrade head``
    # here closes that gap. Failures are logged but non-fatal — the app keeps
    # whatever schema ``create_all`` already produced.
    try:
        await _run_alembic_upgrade()
        log.info("Alembic migrations up to date")
    except Exception:
        log.exception("Alembic upgrade failed — running on create_all schema only")

    session_factory = get_session_factory()
    sync_svc = SyncService(session_factory)

    app.state.prediction_service = PredictionService()
    load_modelo()

    # Pre-build the SHAP TreeExplainer so the first /xai request pays no build
    # cost. Best-effort and non-fatal: a missing model or missing `shap`
    # dependency simply leaves the explainer cold (lazy build / graceful 503).
    _artifact = get_modelo()
    if _artifact is not None and shap_explainer.is_available():
        try:
            if shap_explainer.warm(_artifact["model"]):
                log.info("SHAP explainer warmed at startup")
        except Exception:
            log.exception("SHAP explainer warm-up failed — will build lazily on first request")

    if settings.sync_on_startup:
        log.info("Running initial MITECO sync on startup")
        try:
            await sync_svc.run()
        except Exception:
            log.exception("Initial MITECO sync failed — app continues without fresh data")

    scheduler = None
    if settings.scheduler_enabled:
        scheduler = create_scheduler(sync_svc, settings.sync_interval_seconds)
    if settings.retrain_enabled:
        if scheduler is None:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler

            scheduler = AsyncIOScheduler()
        add_retrain_job(scheduler, settings)
    if settings.alerts_enabled:
        if scheduler is None:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler

            scheduler = AsyncIOScheduler()
        add_alert_job(scheduler, settings)
    if scheduler is not None:
        attach_scheduler_metrics(scheduler)
        scheduler.start()

    # Expose the scheduler for the readiness/details health probes.
    app.state.scheduler = scheduler

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        log.info("Scheduler stopped")
