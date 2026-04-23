"""FastAPI lifespan: DB init, optional startup sync, and scheduler management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.scheduler import create_scheduler
from app.infrastructure.database import Base, get_engine, get_session_factory
from app.infrastructure.database.models import PriceHistoryORM, StationORM  # noqa: F401
from app.services.sync_service import SyncService

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database tables verified / created")

    session_factory = get_session_factory()
    sync_svc = SyncService(session_factory)

    if settings.sync_on_startup:
        log.info("Running initial MITECO sync on startup")
        await sync_svc.run()

    scheduler = None
    if settings.scheduler_enabled:
        scheduler = create_scheduler(sync_svc, settings.sync_interval_seconds)
        scheduler.start()

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        log.info("Scheduler stopped")
