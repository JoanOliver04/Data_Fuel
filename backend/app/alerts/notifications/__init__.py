"""Modular notification layer: channels + deduplicating dispatcher."""

from app.alerts.notifications.channels import InAppChannel, NotificationChannel
from app.alerts.notifications.dispatcher import NotificationDispatcher

__all__ = ["InAppChannel", "NotificationChannel", "NotificationDispatcher"]
