"""Process-local daily quota guard for the TomTom routing provider.

TomTom's free tier is finite, so the adapter (not the client) tracks how many
matrix requests have gone out today and short-circuits to the haversine
fallback once the configured daily limit is reached. The counter resets at UTC
midnight and a single WARNING is logged per breach (not per call).

State is process-local: a single shared default instance lives here so the
count survives across the short-lived provider instances the factory creates
per request. Concurrency is safe under asyncio because acquire is fully
synchronous (no await), so no two coroutines interleave a check-and-increment.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

log = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class QuotaSnapshot:
    """Observable view of the guard's current state (for /health later)."""

    date: date
    used: int
    limit: int
    exhausted: bool


class DailyQuotaGuard:
    """Counts requests per UTC day and reports when the daily limit is spent."""

    def __init__(self, now: Callable[[], datetime] = _utcnow) -> None:
        self._now = now
        self._date = now().date()
        self._used = 0
        self._breach_logged = False

    def _roll_if_new_day(self) -> None:
        today = self._now().date()
        if today != self._date:
            self._date = today
            self._used = 0
            self._breach_logged = False

    def try_acquire(self, limit: int) -> bool:
        """Reserve one request against ``limit``. False means quota is spent.

        Logs a single WARNING the first time the limit is hit on a given day.
        """
        self._roll_if_new_day()
        if self._used >= limit:
            if not self._breach_logged:
                log.warning(
                    "TomTom daily quota reached (%d/%d for %s); routing falls back to haversine",
                    self._used,
                    limit,
                    self._date.isoformat(),
                )
                self._breach_logged = True
            return False
        self._used += 1
        return True

    def snapshot(self, limit: int) -> QuotaSnapshot:
        self._roll_if_new_day()
        return QuotaSnapshot(
            date=self._date,
            used=self._used,
            limit=limit,
            exhausted=self._used >= limit,
        )

    def reset(self) -> None:
        """Wipe state — for test isolation."""
        self._date = self._now().date()
        self._used = 0
        self._breach_logged = False


# Shared default guard so the count is process-wide across provider instances.
default_quota_guard = DailyQuotaGuard()
