"""Async repository for alert persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models.alert import AlertORM
from app.alerts.schemas import AlertCreate, AlertUpdate


class AlertRepository:
    """Data access for :class:`AlertORM`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: AlertCreate, *, default_cooldown: int) -> AlertORM:
        alert = AlertORM(
            user_identifier=data.user_identifier,
            alert_type=data.alert_type,
            fuel_type=data.fuel_type,
            station_id=data.station_id,
            brand=data.brand,
            threshold_price=data.threshold_price,
            threshold_pct=data.threshold_pct,
            latitude=data.latitude,
            longitude=data.longitude,
            radius_km=data.radius_km,
            liters=data.liters,
            cooldown_minutes=(
                data.cooldown_minutes if data.cooldown_minutes is not None else default_cooldown
            ),
        )
        self._session.add(alert)
        await self._session.commit()
        await self._session.refresh(alert)
        return alert

    async def get(self, alert_id: int) -> AlertORM | None:
        return await self._session.get(AlertORM, alert_id)

    async def count_for_user(self, user_identifier: str) -> int:
        stmt = select(func.count()).select_from(AlertORM).where(
            AlertORM.user_identifier == user_identifier
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_by_user(self, user_identifier: str) -> list[AlertORM]:
        stmt = (
            select(AlertORM)
            .where(AlertORM.user_identifier == user_identifier)
            .order_by(AlertORM.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_enabled(self, *, limit: int, offset: int = 0) -> list[AlertORM]:
        """Enabled alerts for batch evaluation, ordered by id for stable paging."""
        stmt = (
            select(AlertORM)
            .where(AlertORM.is_enabled.is_(True))
            .order_by(AlertORM.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def update(self, alert_id: int, data: AlertUpdate) -> AlertORM | None:
        alert = await self.get(alert_id)
        if alert is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(alert, field, value)
        await self._session.commit()
        await self._session.refresh(alert)
        return alert

    async def delete(self, alert_id: int) -> bool:
        alert = await self.get(alert_id)
        if alert is None:
            return False
        await self._session.delete(alert)
        await self._session.commit()
        return True

    async def mark_triggered(self, alert: AlertORM, when: datetime) -> None:
        alert.last_triggered_at = when
        await self._session.commit()
