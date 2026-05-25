"""Alert + notification API.

CRUD for user-defined alerts plus a read-only notification feed. There is no
auth layer in this project, so requests are scoped by an explicit
``user_identifier`` (path/query/body); cross-user access returns 404. All routes
are rate-limited and strictly validated. These endpoints never run evaluation —
the scheduler does — so they are cheap and cannot be abused to trigger work.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models.notification import NotificationORM
from app.alerts.repositories import AlertRepository, NotificationRepository
from app.alerts.schemas import (
    AlertCreate,
    AlertOut,
    AlertUpdate,
    NotificationChannel,
    NotificationOut,
    TriggerSource,
)
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.infrastructure.database.session import get_async_session

log = logging.getLogger("app.alerts.endpoints")

router = APIRouter(tags=["alerts"])

_RATE = lambda: get_settings().alerts_rate_limit  # noqa: E731 (slowapi wants a callable)


def _to_notification_out(row: NotificationORM) -> NotificationOut:
    data: dict[str, object] = {}
    if row.data_json:
        try:
            parsed = json.loads(row.data_json)
            if isinstance(parsed, dict):
                data = parsed
        except ValueError:
            data = {}
    return NotificationOut(
        id=row.id,
        alert_id=row.alert_id,
        user_identifier=row.user_identifier,
        alert_type=row.alert_type,
        channel=cast(NotificationChannel, row.channel),
        title=row.title,
        message=row.message,
        source=cast(TriggerSource, row.source),
        data=data,
        created_at=row.created_at,
    )


@router.post("/alerts", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(_RATE)
async def create_alert(
    request: Request,
    body: AlertCreate,
    session: AsyncSession = Depends(get_async_session),
) -> AlertOut:
    settings = get_settings()
    repo = AlertRepository(session)
    if await repo.count_for_user(body.user_identifier) >= settings.alerts_max_per_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alert limit reached ({settings.alerts_max_per_user} per user)",
        )
    alert = await repo.create(body, default_cooldown=settings.alerts_default_cooldown_minutes)
    return AlertOut.model_validate(alert)


@router.get("/alerts", response_model=list[AlertOut])
@limiter.limit(_RATE)
async def list_alerts(
    request: Request,
    user_identifier: Annotated[str, Query(min_length=1, max_length=120)],
    session: AsyncSession = Depends(get_async_session),
) -> list[AlertOut]:
    alerts = await AlertRepository(session).list_by_user(user_identifier)
    return [AlertOut.model_validate(a) for a in alerts]


@router.patch("/alerts/{alert_id}", response_model=AlertOut)
@limiter.limit(_RATE)
async def update_alert(
    request: Request,
    alert_id: int,
    body: AlertUpdate,
    user_identifier: Annotated[str, Query(min_length=1, max_length=120)],
    session: AsyncSession = Depends(get_async_session),
) -> AlertOut:
    repo = AlertRepository(session)
    existing = await repo.get(alert_id)
    if existing is None or existing.user_identifier != user_identifier:
        raise HTTPException(status_code=404, detail="Alert not found")
    updated = await repo.update(alert_id, body)
    assert updated is not None  # existence checked above
    return AlertOut.model_validate(updated)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(_RATE)
async def delete_alert(
    request: Request,
    alert_id: int,
    user_identifier: Annotated[str, Query(min_length=1, max_length=120)],
    session: AsyncSession = Depends(get_async_session),
) -> None:
    repo = AlertRepository(session)
    existing = await repo.get(alert_id)
    if existing is None or existing.user_identifier != user_identifier:
        raise HTTPException(status_code=404, detail="Alert not found")
    await repo.delete(alert_id)


@router.get("/notifications", response_model=list[NotificationOut])
@limiter.limit(_RATE)
async def list_notifications(
    request: Request,
    user_identifier: Annotated[str, Query(min_length=1, max_length=120)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    session: AsyncSession = Depends(get_async_session),
) -> list[NotificationOut]:
    rows = await NotificationRepository(session).list_by_user(user_identifier, limit=limit)
    return [_to_notification_out(r) for r in rows]
