"""Verify slowapi returns 429 once the per-endpoint quota is exhausted."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.infrastructure.database import session as db_session
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (  # noqa: F401
    PriceHistoryORM,
    StationORM,
)
from app.main import create_app


async def test_recommendations_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("SYNC_ON_STARTUP", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("GEOCODING_RATE_LIMIT", "2/minute")
    get_settings.cache_clear()

    # The in-memory slowapi store is process-global; clear leftover counts from prior tests.
    limiter.reset()
    # Conftest disables the shared limiter for other tests; re-enable it here.
    limiter.enabled = True

    engine = db_session.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        app = create_app()
        transport = ASGITransport(app=app)

        url = "/api/v1/recommendations?lat=39.47&lon=-0.376&liters=40&fuel_type=gasoil"
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            first = await client.get(url)
            second = await client.get(url)
            third = await client.get(url)

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
    finally:
        limiter.enabled = False
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
