"""Async repository for notification history + dedup lookups."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models.notification import NotificationORM


class NotificationRepository:
    """Data access for :class:`NotificationORM`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        alert_id: int | None,
        user_identifier: str,
        alert_type: str,
        channel: str,
        title: str,
        message: str,
        source: str,
        dedup_key: str,
        data_json: str | None,
    ) -> NotificationORM:
        notification = NotificationORM(
            alert_id=alert_id,
            user_identifier=user_identifier,
            alert_type=alert_type,
            channel=channel,
            title=title,
            message=message,
            source=source,
            dedup_key=dedup_key,
            data_json=data_json,
        )
        self._session.add(notification)
        await self._session.commit()
        await self._session.refresh(notification)
        return notification

    async def dedup_exists(self, dedup_key: str, *, since: datetime) -> bool:
        """True if a notification with this dedup key exists at/after ``since``."""
        stmt = (
            select(func.count())
            .select_from(NotificationORM)
            .where(
                NotificationORM.dedup_key == dedup_key,
                NotificationORM.created_at >= since,
            )
        )
        return int((await self._session.execute(stmt)).scalar_one()) > 0

    async def list_by_user(self, user_identifier: str, *, limit: int = 50) -> list[NotificationORM]:
        stmt = (
            select(NotificationORM)
            .where(NotificationORM.user_identifier == user_identifier)
            .order_by(NotificationORM.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
