"""Shared pytest fixtures.

Each test gets fresh Settings/engine instances by clearing the lru_caches
defined in `app.core.config` and `app.infrastructure.database.session`.
"""

from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.cache import recommendations_cache
from app.core.config import Settings, get_settings
from app.infrastructure.database import session as db_session
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (  # noqa: F401  (registers ORM models)
    PriceHistoryORM,
    StationORM,
    TrainingRunORM,
    VehicleProfileORM,
)
from app.main import create_app
from app.ml.xai import feature_importance_service, shap_explainer


@pytest.fixture(autouse=True)
def _reset_caches() -> Generator[None, None, None]:
    """Clear all lru_caches and TTL caches between tests for full isolation."""
    get_settings.cache_clear()
    db_session.get_engine.cache_clear()
    db_session.get_session_factory.cache_clear()
    recommendations_cache.reset()
    feature_importance_service.reset_cache()
    shap_explainer.reset()
    yield
    get_settings.cache_clear()
    db_session.get_engine.cache_clear()
    db_session.get_session_factory.cache_clear()
    recommendations_cache.reset()
    feature_importance_service.reset_cache()
    shap_explainer.reset()


@pytest.fixture
def rf_artifact() -> dict[str, Any]:
    """A small but *real* Random Forest artifact the XAI layer can explain.

    Trains a 10-tree forest on synthetic data shaped like the 15-column feature
    schema, with the target driven by a couple of features so importances are
    non-degenerate. SHAP TreeExplainer works on this exactly as on production.
    """
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import LabelEncoder

    from app.ml.training.entrenar import FEATURE_COLUMNS

    rng = np.random.default_rng(0)
    n = 200
    x = rng.normal(size=(n, len(FEATURE_COLUMNS)))
    # Target leans on precio_semana_anterior (idx 4) and precio_medio_municipio (idx 8).
    y = 1.5 + 0.5 * x[:, 4] + 0.3 * x[:, 8] + rng.normal(scale=0.05, size=n)
    model = RandomForestRegressor(n_estimators=10, max_depth=5, random_state=0)
    model.fit(x, y)

    le_m = LabelEncoder().fit(["Valencia", "Alzira", "Gandia"])
    le_c = LabelEncoder().fit(["Horta de València", "Ribera Alta", "La Safor"])
    importances = {
        f: float(i) for f, i in zip(FEATURE_COLUMNS, model.feature_importances_, strict=True)
    }
    return {
        "model": model,
        "label_encoder_municipio": le_m,
        "label_encoder_comarca": le_c,
        "features_names": list(FEATURE_COLUMNS),
        "feature_importances": importances,
        "r2": 0.85,
        "mae": 0.04,
        "trained_at": "2026-01-01T00:00:00+00:00",
        "version": "test-rf-v1",
    }


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Settings configured for tests: in-memory DB, no startup sync, no scheduler."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173,http://example.test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SYNC_ON_STARTUP", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    # Hermetic default: straight-line distances and no API keys, so the suite
    # never makes real ORS/TomTom calls regardless of the developer's .env.
    # Tests that exercise driving modes set these explicitly and mock the
    # provider/transport.
    monkeypatch.setenv("DISTANCE_MODE", "EUCLIDEAN")
    monkeypatch.setenv("ORS_API_KEY", "")
    monkeypatch.setenv("TOMTOM_API_KEY", "")
    # Same reasoning for the LLM: with no key the provider factory degrades to
    # the deterministic fallback, so the suite never calls OpenRouter/OpenAI
    # regardless of the developer's .env. LLM tests mock the provider directly.
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "")
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
async def api_client(engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    """ASGI in-process client for FastAPI integration tests.

    ASGITransport doesn't invoke the ASGI lifespan scope, so we manually seed
    app.state with the services that endpoints depend on. Depending on
    ``engine`` guarantees the in-memory schema is created before endpoints
    that touch the DB are exercised.
    """
    from app.domain.services.prediction_service import PredictionService

    app = create_app()
    app.state.prediction_service = PredictionService()
    # Rate limiter would flake cross-test under a shared in-memory store; disable for tests.
    app.state.limiter.enabled = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
