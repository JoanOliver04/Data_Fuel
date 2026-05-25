"""Alert ORM models. Importing this registers them on the shared ``Base``."""

from app.alerts.models.alert import AlertORM
from app.alerts.models.notification import NotificationORM

__all__ = ["AlertORM", "NotificationORM"]
