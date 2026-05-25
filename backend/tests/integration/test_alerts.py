"""Integration tests for the alert API + evaluation engine (seeded, deterministic)."""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.repositories import AlertRepository, NotificationRepository
from app.alerts.schemas import AlertCreate
from app.alerts.services import AlertEvaluationEngine
from app.core.config import get_settings
from app.infrastructure.database.models.station import StationORM
from app.infrastructure.database.session import get_session_factory


def _station() -> StationORM:
    return StationORM(
        id=1, brand="REPSOL", address="Calle X", locality="Alzira", municipality="Alzira",
        province="Valencia", postal_code="46600", latitude=39.15, longitude=-0.43,
        schedule="L-D: 24H", price_gasoline_95_e5=Decimal("1.400"), price_gasoline_95_e10=None,
        price_gasoline_98_e5=None, price_diesel_a=Decimal("1.489"), price_diesel_premium=None,
    )


async def test_alert_crud_and_validation(api_client: AsyncClient) -> None:
    payload = {
        "user_identifier": "u1", "alert_type": "PRICE_BELOW_THRESHOLD",
        "fuel_type": "gasolina_95", "threshold_price": "1.45",
        "latitude": 39.15, "longitude": -0.43, "radius_km": 20,
    }
    created = await api_client.post("/api/v1/alerts", json=payload)
    assert created.status_code == 201
    alert_id = created.json()["id"]

    listed = await api_client.get("/api/v1/alerts", params={"user_identifier": "u1"})
    assert listed.status_code == 200 and any(a["id"] == alert_id for a in listed.json())

    patched = await api_client.patch(
        f"/api/v1/alerts/{alert_id}", params={"user_identifier": "u1"},
        json={"is_enabled": False},
    )
    assert patched.status_code == 200 and patched.json()["is_enabled"] is False

    # Cross-user access is hidden.
    assert (
        await api_client.patch(
            f"/api/v1/alerts/{alert_id}", params={"user_identifier": "intruder"},
            json={"is_enabled": True},
        )
    ).status_code == 404

    deleted = await api_client.delete(
        f"/api/v1/alerts/{alert_id}", params={"user_identifier": "u1"}
    )
    assert deleted.status_code == 204


async def test_create_rejects_missing_required_field(api_client: AsyncClient) -> None:
    # PRICE_BELOW_THRESHOLD without threshold_price → 422.
    resp = await api_client.post(
        "/api/v1/alerts",
        json={"user_identifier": "u2", "alert_type": "PRICE_BELOW_THRESHOLD",
              "fuel_type": "gasolina_95"},
    )
    assert resp.status_code == 422


@pytest.fixture
async def seeded_station(db: AsyncSession) -> None:
    db.add(_station())
    await db.commit()


async def test_engine_triggers_then_dedups(
    db: AsyncSession, api_client: AsyncClient, seeded_station: None
) -> None:
    await AlertRepository(db).create(
        AlertCreate(
            user_identifier="ueng", alert_type="PRICE_BELOW_THRESHOLD",
            fuel_type="gasolina_95", threshold_price=Decimal("1.45"),
            latitude=39.15, longitude=-0.43, radius_km=20, cooldown_minutes=0,
        ),
        default_cooldown=0,
    )

    engine = AlertEvaluationEngine(get_session_factory(), get_settings())
    first = await engine.run_once()
    assert first.triggered == 1

    # Second tick: identical trigger state → deduplicated, no new notification.
    await engine.run_once()

    notifications = await NotificationRepository(db).list_by_user("ueng")
    assert len(notifications) == 1
    assert notifications[0].alert_type == "PRICE_BELOW_THRESHOLD"
    assert "1.45" in notifications[0].message
