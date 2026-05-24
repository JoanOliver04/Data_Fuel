"""Unit tests for the ML retrain scheduler wiring."""

from __future__ import annotations

import asyncio

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import Settings
from app.core.scheduler import add_retrain_job, run_retrain_job
from app.ml.lifecycle.history import TrainingRunStatus
from app.ml.lifecycle.pipeline import RetrainOutcome


def _settings(**env: str) -> Settings:
    return Settings(**env)  # type: ignore[arg-type]


# ── job registration ───────────────────────────────────────────────────────────


def test_add_retrain_job_registers_cron_job() -> None:
    scheduler = AsyncIOScheduler()
    add_retrain_job(scheduler, _settings(retrain_cron="0 3 * * 0"))
    job = scheduler.get_job("ml_retrain")
    assert job is not None
    assert job.max_instances == 1


def test_add_retrain_job_accepts_custom_cron() -> None:
    scheduler = AsyncIOScheduler()
    add_retrain_job(scheduler, _settings(retrain_cron="30 4 * * 1"))
    assert scheduler.get_job("ml_retrain") is not None


def test_invalid_cron_rejected_by_settings() -> None:
    with pytest.raises(ValueError, match="5-field cron"):
        _settings(retrain_cron="not a cron")


# ── job execution ───────────────────────────────────────────────────────────


class _FakePipeline:
    def __init__(self, *, sleep: float = 0.0) -> None:
        self._sleep = sleep
        self.ran = False

    async def run(self) -> RetrainOutcome:
        self.ran = True
        if self._sleep:
            await asyncio.sleep(self._sleep)
        return RetrainOutcome(
            status=TrainingRunStatus.ACTIVATED,
            version="2026-05-24T03-00-00",
            reason=None,
            metrics=None,
            duration_seconds=1.0,
        )


async def test_run_retrain_job_invokes_pipeline() -> None:
    pipeline = _FakePipeline()
    await run_retrain_job(timeout_seconds=60, pipeline_factory=lambda: pipeline)
    assert pipeline.ran is True


async def test_run_retrain_job_times_out_without_raising() -> None:
    pipeline = _FakePipeline(sleep=5.0)
    # Should not raise despite the pipeline exceeding the timeout.
    await run_retrain_job(timeout_seconds=1, pipeline_factory=lambda: pipeline)


async def test_run_retrain_job_swallows_pipeline_errors() -> None:
    class _Boom:
        async def run(self) -> RetrainOutcome:
            raise RuntimeError("unexpected")

    # Must not propagate — a scheduled job failure should never crash the loop.
    await run_retrain_job(timeout_seconds=60, pipeline_factory=lambda: _Boom())  # type: ignore[arg-type,return-value]
