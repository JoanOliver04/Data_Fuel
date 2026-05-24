"""APScheduler configuration for periodic MITECO syncs and ML retraining."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import Settings
from app.ml.lifecycle.pipeline import RetrainPipeline
from app.services.sync_service import SyncService

log = logging.getLogger(__name__)

PipelineFactory = Callable[[], RetrainPipeline]


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


async def run_retrain_job(
    timeout_seconds: int,
    pipeline_factory: PipelineFactory | None = None,
) -> None:
    """Run one retraining attempt under a wall-clock timeout.

    The pipeline already swallows its own errors and returns a FAILED outcome,
    so this wrapper only guards against a hung run and logs the result. On
    timeout the await is abandoned; the CPU work running in a worker thread
    cannot be force-killed and will finish in the background, but no further
    pipeline steps execute.
    """
    factory = pipeline_factory or RetrainPipeline
    try:
        outcome = await asyncio.wait_for(factory().run(), timeout=timeout_seconds)
        log.info(
            "Scheduled retrain finished: status=%s version=%s duration=%.1fs",
            outcome.status.value,
            outcome.version,
            outcome.duration_seconds,
        )
    except TimeoutError:
        log.error("Scheduled retrain exceeded %ds timeout — aborted", timeout_seconds)
    except Exception:
        log.exception("Scheduled retrain raised unexpectedly")


def add_retrain_job(
    scheduler: AsyncIOScheduler,
    settings: Settings,
    pipeline_factory: PipelineFactory | None = None,
) -> None:
    """Register the weekly retraining cron job (UTC) on an existing scheduler."""
    trigger = CronTrigger.from_crontab(settings.retrain_cron, timezone="UTC")
    scheduler.add_job(
        run_retrain_job,
        trigger=trigger,
        id="ml_retrain",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
        kwargs={
            "timeout_seconds": settings.retrain_timeout_seconds,
            "pipeline_factory": pipeline_factory,
        },
    )
    log.info("Scheduler configured: ML retrain cron=%r (UTC)", settings.retrain_cron)
