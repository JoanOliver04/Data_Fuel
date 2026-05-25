"""Alembic migrations apply cleanly and reach head (production startup flow).

The app boots with ``Base.metadata.create_all`` then ``alembic upgrade head``
(idempotent migrations). This test reproduces that on a throwaway SQLite file
and asserts the version table lands on the latest revision — catching a broken
or non-idempotent migration before it hits a real Postgres deploy.

Synchronous on purpose: ``command.upgrade`` drives Alembic's own
``asyncio.run`` internally, which cannot run inside a pytest event loop.
"""

import asyncio
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.infrastructure.database.base import Base

_HEAD = "0004_analytics_indexes"


async def _create_all(url: str) -> None:
    import app.alerts.models
    import app.infrastructure.database.models  # noqa: F401

    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def test_migrations_reach_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "mig.db"
    url = f"sqlite+aiosqlite:///{db.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    asyncio.run(_create_all(url))  # production flow: schema first, then upgrade
    command.upgrade(Config("alembic.ini"), "head")

    con = sqlite3.connect(db)
    try:
        version = con.execute("SELECT version_num FROM alembic_version").fetchone()
    finally:
        con.close()
    assert version is not None and version[0] == _HEAD
