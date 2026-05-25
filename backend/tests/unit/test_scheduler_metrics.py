"""Unit tests for scheduler observability (listener counts + job duration)."""

from types import SimpleNamespace

import pytest
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED

from app.core.metrics import REGISTRY
from app.core.scheduler import _on_job_event, _timed_job


def _runs(job: str, outcome: str) -> float:
    return (
        REGISTRY.get_sample_value(
            "datafuel_scheduler_job_runs_total", {"job": job, "outcome": outcome}
        )
        or 0.0
    )


def _dur_count(job: str) -> float:
    return (
        REGISTRY.get_sample_value(
            "datafuel_scheduler_job_duration_seconds_count", {"job": job}
        )
        or 0.0
    )


def test_listener_counts_executed_error_missed() -> None:
    for code, outcome in (
        (EVENT_JOB_EXECUTED, "executed"),
        (EVENT_JOB_ERROR, "error"),
        (EVENT_JOB_MISSED, "missed"),
    ):
        before = _runs("t_sched", outcome)
        _on_job_event(SimpleNamespace(code=code, job_id="t_sched", exception=ValueError("x")))
        assert _runs("t_sched", outcome) == before + 1.0


async def test_timed_job_observes_duration_on_success() -> None:
    async def job() -> int:
        return 42

    before = _dur_count("t_dur_ok")
    assert await _timed_job("t_dur_ok", job)() == 42
    assert _dur_count("t_dur_ok") == before + 1.0


async def test_timed_job_observes_duration_on_exception() -> None:
    async def boom() -> None:
        raise RuntimeError("boom")

    before = _dur_count("t_dur_err")
    with pytest.raises(RuntimeError):
        await _timed_job("t_dur_err", boom)()
    assert _dur_count("t_dur_err") == before + 1.0
