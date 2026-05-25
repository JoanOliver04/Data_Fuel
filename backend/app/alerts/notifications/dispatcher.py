"""Notification dispatch: deduplication, persistence and channel delivery.

Cooldown (time since the alert last fired) is enforced upstream by the engine;
the dispatcher enforces *content* deduplication — a notification with the same
namespaced dedup key inside the dedup window is suppressed. Together they make
spam structurally impossible: an alert can only re-notify when both the cooldown
has elapsed and the trigger state actually changed.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from app.alerts.schemas import TriggerSource
from app.core.metrics import alert_evaluations_total, alert_notifications_total

if TYPE_CHECKING:
    from app.alerts.evaluators.base import Trigger
    from app.alerts.models.alert import AlertORM
    from app.alerts.notifications.channels import NotificationChannel
    from app.alerts.repositories.notification_repository import NotificationRepository

log = logging.getLogger("app.alerts.dispatcher")


class NotificationDispatcher:
    """Persists + delivers notifications, suppressing duplicates."""

    def __init__(
        self,
        notifications: NotificationRepository,
        channel: NotificationChannel,
        *,
        dedup_window_minutes: int,
    ) -> None:
        self._notifications = notifications
        self._channel = channel
        self._dedup_window = timedelta(minutes=dedup_window_minutes)

    async def dispatch(
        self,
        *,
        alert: AlertORM,
        trigger: Trigger,
        message: str,
        source: TriggerSource,
        now: datetime,
    ) -> bool:
        """Persist + deliver a triggered alert. Returns ``False`` if deduplicated."""
        dedup_key = f"{alert.id}:{trigger.dedup_key}"
        if await self._notifications.dedup_exists(dedup_key, since=now - self._dedup_window):
            alert_evaluations_total.labels(
                alert_type=alert.alert_type, result="dedup_suppressed"
            ).inc()
            return False

        notification = await self._notifications.create(
            alert_id=alert.id,
            user_identifier=alert.user_identifier,
            alert_type=alert.alert_type,
            channel=self._channel.name,
            title=trigger.title,
            message=message,
            source=source,
            dedup_key=dedup_key,
            data_json=json.dumps(trigger.data, ensure_ascii=False, default=str),
        )
        sent = await self._channel.send(notification)
        alert_notifications_total.labels(
            channel=self._channel.name, result="sent" if sent else "failed"
        ).inc()
        if not sent:
            log.warning("Notification delivery failed: channel=%s id=%s", self._channel.name, notification.id)
        return True
