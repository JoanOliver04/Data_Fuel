"""Async alert-evaluation engine.

One ``run_once`` is a batch tick (driven by the scheduler). It loads enabled
alerts, builds a shared :class:`AlertContext`, and evaluates each behind its own
``try/except`` so a single failure never aborts the batch or crashes the
scheduler. Anti-spam is layered: a per-alert cooldown skips evaluation entirely,
then the dispatcher deduplicates by trigger state. The CPU-bound ML prediction
runs off the event loop (in the context), so the loop is never blocked.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.ai.providers import get_llm_provider
from app.ai.providers.fallback import FallbackProvider
from app.alerts.enrich import enrich_message
from app.alerts.evaluators import AlertContext, get_evaluator
from app.alerts.notifications import InAppChannel, NotificationDispatcher
from app.alerts.repositories import AlertRepository, NotificationRepository
from app.core.metrics import alert_batch_duration_seconds, alert_evaluations_total
from app.domain.services.prediction_service import PredictionService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.ai.providers.base import LLMProvider
    from app.alerts.models.alert import AlertORM
    from app.core.config import Settings

log = logging.getLogger("app.alerts.engine")


@dataclass(slots=True)
class EvalStats:
    """Outcome counts for one batch tick (for structured logging)."""

    evaluated: int = 0
    triggered: int = 0
    suppressed: int = 0
    errors: int = 0


class AlertEvaluationEngine:
    """Evaluates enabled alerts in batches and dispatches notifications."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], settings: Settings) -> None:
        self._session_factory = session_factory
        self._settings = settings

    def _provider(self) -> LLMProvider:
        if self._settings.alerts_llm_explanations:
            return get_llm_provider(self._settings)
        return FallbackProvider()

    async def run_once(self) -> EvalStats:
        """Evaluate one batch of enabled alerts. Never raises."""
        start = time.perf_counter()
        stats = EvalStats()
        try:
            async with self._session_factory() as session:
                await self._run_batch(session, stats)
        except Exception:  # pragma: no cover - last-resort guard, must not crash scheduler
            log.exception("Alert batch aborted unexpectedly")
        finally:
            alert_batch_duration_seconds.observe(time.perf_counter() - start)
        log.info(
            "Alert batch complete",
            extra={
                "evaluated": stats.evaluated,
                "triggered": stats.triggered,
                "suppressed": stats.suppressed,
                "errors": stats.errors,
            },
        )
        return stats

    async def _run_batch(self, session: AsyncSession, stats: EvalStats) -> None:
        alert_repo = AlertRepository(session)
        notifications = NotificationRepository(session)
        alerts = await alert_repo.list_enabled(limit=self._settings.alerts_eval_batch_size)
        if not alerts:
            return
        ctx = AlertContext(session, PredictionService(), km_cost=self._settings.default_km_cost)
        provider = self._provider()
        dispatcher = NotificationDispatcher(
            notifications,
            InAppChannel(),
            dedup_window_minutes=self._settings.alerts_dedup_window_minutes,
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        for alert in alerts:
            stats.evaluated += 1
            try:
                await self._eval_one(alert, ctx, dispatcher, alert_repo, provider, now, stats)
            except Exception:
                stats.errors += 1
                alert_evaluations_total.labels(alert_type=alert.alert_type, result="error").inc()
                log.exception("Alert %s evaluation failed", alert.id)

    async def _eval_one(
        self,
        alert: AlertORM,
        ctx: AlertContext,
        dispatcher: NotificationDispatcher,
        alert_repo: AlertRepository,
        provider: LLMProvider,
        now: datetime,
        stats: EvalStats,
    ) -> None:
        if self._in_cooldown(alert, now):
            alert_evaluations_total.labels(
                alert_type=alert.alert_type, result="cooldown_suppressed"
            ).inc()
            stats.suppressed += 1
            return

        evaluator = get_evaluator(alert.alert_type)
        if evaluator is None:
            alert_evaluations_total.labels(alert_type=alert.alert_type, result="error").inc()
            stats.errors += 1
            log.warning("No evaluator registered for alert_type=%s", alert.alert_type)
            return

        trigger = await evaluator.evaluate(alert, ctx)
        if trigger is None:
            alert_evaluations_total.labels(alert_type=alert.alert_type, result="no_trigger").inc()
            return

        message, source = trigger.message, trigger.source
        if self._settings.alerts_llm_explanations:
            message, source = await enrich_message(trigger.message, provider)

        dispatched = await dispatcher.dispatch(
            alert=alert, trigger=trigger, message=message, source=source, now=now
        )
        if dispatched:
            await alert_repo.mark_triggered(alert, now)
            alert_evaluations_total.labels(alert_type=alert.alert_type, result="triggered").inc()
            stats.triggered += 1
        else:
            stats.suppressed += 1  # dedup outcome already counted by the dispatcher

    @staticmethod
    def _in_cooldown(alert: AlertORM, now: datetime) -> bool:
        if alert.cooldown_minutes <= 0 or alert.last_triggered_at is None:
            return False
        last = alert.last_triggered_at
        if last.tzinfo is not None:
            last = last.replace(tzinfo=None)
        return now < last + timedelta(minutes=alert.cooldown_minutes)


async def run_alert_evaluation(settings: Settings) -> None:
    """Scheduler entry point: build the engine on the live session factory and tick."""
    from app.infrastructure.database.session import get_session_factory

    await AlertEvaluationEngine(get_session_factory(), settings).run_once()
