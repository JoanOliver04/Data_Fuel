"""APScheduler configuration for periodic MITECO syncs and ML retraining."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import Settings
from app.core.metrics import scheduler_job_duration_seconds, scheduler_job_runs_total
from app.ml.lifecycle.pipeline import RetrainPipeline
from app.services.sync_service import SyncService

log = logging.getLogger(__name__)

PipelineFactory = Callable[[], RetrainPipeline]

_T = TypeVar("_T")


def _timed_job(
    job_id: str, func: Callable[..., Awaitable[_T]]
) -> Callable[..., Awaitable[_T]]:
    """Wrap an async job so its wall-clock duration is always observed."""

    async def wrapper(*args: Any, **kwargs: Any) -> _T:
        start = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            scheduler_job_duration_seconds.labels(job=job_id).observe(
                time.perf_counter() - start
            )

    return wrapper


def _on_job_event(event: Any) -> None:
    """APScheduler listener: count job outcomes and log failures structurally."""
    if event.code == EVENT_JOB_ERROR:
        outcome = "error"
    elif event.code == EVENT_JOB_MISSED:
        outcome = "missed"
    else:
        outcome = "executed"
    scheduler_job_runs_total.labels(job=event.job_id, outcome=outcome).inc()
    if outcome == "error":
        log.error(
            "Scheduler job %s failed: %s",
            event.job_id,
            type(getattr(event, "exception", None)).__name__,
            extra={"job_id": event.job_id, "outcome": outcome},
        )
    elif outcome == "missed":
        log.warning("Scheduler job %s missed its run", event.job_id, extra={"job_id": event.job_id})


def attach_scheduler_metrics(scheduler: AsyncIOScheduler) -> None:
    """Register the job-outcome listener. Call once before ``scheduler.start()``."""
    scheduler.add_listener(
        _on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
    )


def create_scheduler(sync_svc: SyncService, interval_seconds: int) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _timed_job("miteco_sync", sync_svc.run),
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
        _timed_job("ml_retrain", run_retrain_job),
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
