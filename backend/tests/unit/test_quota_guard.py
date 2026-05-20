"""Tests for DailyQuotaGuard: counting, exhaustion, UTC midnight rollover.

The guard takes an injectable clock so the rollover can be tested
deterministically without sleeping or patching internals.
"""

import logging
from datetime import UTC, datetime

from app.services.routing.quota import DailyQuotaGuard


class _Clock:
    """Mutable callable returning a fixed datetime until reassigned."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


_DAY1 = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
_DAY2 = datetime(2026, 5, 21, 0, 1, tzinfo=UTC)


def test_acquires_until_limit_then_refuses() -> None:
    guard = DailyQuotaGuard(now=_Clock(_DAY1))

    assert guard.try_acquire(2) is True
    assert guard.try_acquire(2) is True
    assert guard.try_acquire(2) is False
    assert guard.try_acquire(2) is False


def test_snapshot_reports_usage_and_exhaustion() -> None:
    guard = DailyQuotaGuard(now=_Clock(_DAY1))
    guard.try_acquire(1)

    snap = guard.snapshot(1)
    assert snap.used == 1
    assert snap.limit == 1
    assert snap.exhausted is True
    assert snap.date == _DAY1.date()


def test_midnight_rollover_resets_counter() -> None:
    clock = _Clock(_DAY1)
    guard = DailyQuotaGuard(now=clock)

    assert guard.try_acquire(1) is True
    assert guard.try_acquire(1) is False  # day 1 spent

    clock.now = _DAY2  # cross UTC midnight
    assert guard.try_acquire(1) is True  # counter reset for the new day
    assert guard.snapshot(1).date == _DAY2.date()


def test_breach_warning_logged_once_per_day(caplog) -> None:
    guard = DailyQuotaGuard(now=_Clock(_DAY1))
    guard.try_acquire(1)  # uses the only slot

    with caplog.at_level(logging.WARNING, logger="app.services.routing.quota"):
        guard.try_acquire(1)
        guard.try_acquire(1)
        guard.try_acquire(1)

    breaches = [r for r in caplog.records if "daily quota reached" in r.message]
    assert len(breaches) == 1  # warned once, not per refused call


def test_reset_clears_state() -> None:
    guard = DailyQuotaGuard(now=_Clock(_DAY1))
    guard.try_acquire(5)
    guard.try_acquire(5)

    guard.reset()

    assert guard.snapshot(5).used == 0
