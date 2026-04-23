"""Async SQLAlchemy engine and session factory.

Engine and session factory are created lazily and cached so that tests can
clear the cache and substitute a different DATABASE_URL.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import ConnectionPoolEntry

from app.core.config import get_settings


def _enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    """SQLite ignores FOREIGN KEY constraints unless this PRAGMA is set per-connection."""

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(
        dbapi_connection: DBAPIConnection,
        _connection_record: ConnectionPoolEntry,
    ) -> None:
        cursor: Any = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return the cached async SQLAlchemy engine."""
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        future=True,
    )
    if settings.database_url.startswith("sqlite"):
        _enable_sqlite_foreign_keys(engine)
    return engine


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the cached async session factory bound to the current engine."""
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async SQLAlchemy session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
