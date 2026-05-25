"""Dialect-portability helpers must emit the right SQL per database."""

import pytest
from sqlalchemy.dialects import postgresql, sqlite

from app.core.config import get_settings
from app.infrastructure.database.dialects import active_dialect, build_upsert, time_bucket
from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM


def _use(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()


def test_active_dialect_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, "sqlite+aiosqlite:///:memory:")
    assert active_dialect() == "sqlite"
    _use(monkeypatch, "postgresql+asyncpg://u:p@h/db")
    assert active_dialect() == "postgresql"


def test_time_bucket_sqlite_uses_strftime(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, "sqlite+aiosqlite:///:memory:")
    assert "strftime" in str(time_bucket(PriceHistoryORM.recorded_at, "hour"))


def test_time_bucket_postgres_uses_to_char(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, "postgresql+asyncpg://u:p@h/db")
    assert "to_char" in str(time_bucket(PriceHistoryORM.recorded_at, "day"))


def test_build_upsert_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, "postgresql+asyncpg://u:p@h/db")
    stmt = build_upsert(
        StationORM, [{"id": 1, "brand": "X"}], index_elements=["id"], update_keys=["brand"]
    )
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT" in compiled and "DO UPDATE" in compiled


def test_build_upsert_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, "sqlite+aiosqlite:///:memory:")
    stmt = build_upsert(
        StationORM, [{"id": 1, "brand": "X"}], index_elements=["id"], update_keys=["brand"]
    )
    assert "ON CONFLICT" in str(stmt.compile(dialect=sqlite.dialect()))
