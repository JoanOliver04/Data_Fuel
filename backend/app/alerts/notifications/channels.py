"""Notification channels.

A channel delivers an already-persisted notification. The in-app channel is a
no-op delivery (the stored row *is* the in-app notification); the Protocol lets
email / push / Telegram channels slot in later without touching the dispatcher.
Channels never raise — failures return ``False`` so delivery stays retry-safe.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.alerts.models.notification import NotificationORM

log = logging.getLogger("app.alerts.notifications")


@runtime_checkable
class NotificationChannel(Protocol):
    name: str

    async def send(self, notification: NotificationORM) -> bool:
        """Deliver the notification. Returns success; never raises."""
        ...


class InAppChannel:
    """In-app delivery: persistence is delivery, so this always succeeds."""

    name = "in_app"

    async def send(self, notification: NotificationORM) -> bool:
        return True
