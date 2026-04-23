"""APScheduler configuration for periodic MITECO syncs."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.sync_service import SyncService

log = logging.getLogger(__name__)


def create_scheduler(sync_svc: SyncService, interval_seconds: int) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        sync_svc.run,
        trigger="interval",
        seconds=interval_seconds,
        id="miteco_sync",
        replace_existing=True,
        misfire_grace_time=300,
    )
    log.info("Scheduler configured: MITECO sync every %ds", interval_seconds)
    return scheduler
