"""Shared pytest fixtures.

Each test gets fresh Settings/engine instances by clearing the lru_caches
defined in `app.core.config` and `app.infrastructure.database.session`.
"""

from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import Settings, get_settings
from app.infrastructure.database import session as db_session
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (  # noqa: F401  (registers ORM models)
    PriceHistoryORM,
    StationORM,
)
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_caches() -> Generator[None, None, None]:
    """Clear all lru_caches between tests for full isolation."""
    get_settings.cache_clear()
    db_session.get_engine.cache_clear()
    db_session.get_session_factory.cache_clear()
    yield
    get_settings.cache_clear()
    db_session.get_engine.cache_clear()
    db_session.get_session_factory.cache_clear()


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Settings configured for tests: in-memory DB, no startup sync, no scheduler."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173,http://example.test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SYNC_ON_STARTUP", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    return get_settings()


@pytest.fixture
async def engine(test_settings: Settings) -> AsyncGenerator[AsyncEngine, None]:
    """Provide a fresh in-memory SQLite async engine with all tables created."""
    eng = db_session.get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await eng.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession bound to the test engine."""
    factory = db_session.get_session_factory()
    async with factory() as session:
        yield session


@pytest.fixture
async def api_client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """ASGI in-process client for FastAPI integration tests.

    ASGITransport doesn't invoke the ASGI lifespan scope, so we manually seed
    app.state with the services that endpoints depend on.
    """
    from app.domain.services.prediction_service import PredictionService

    app = create_app()
    app.state.prediction_service = PredictionService()
    # Rate limiter would flake cross-test under a shared in-memory store; disable for tests.
    app.state.limiter.enabled = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
