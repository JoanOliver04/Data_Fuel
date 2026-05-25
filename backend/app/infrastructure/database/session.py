"""Async SQLAlchemy engine and session factory.

Engine and session factory are created lazily and cached so that tests can
clear the cache and substitute a different DATABASE_URL.
"""

import logging
import time
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

from app.core.config import Settings, get_settings
from app.core.metrics import db_query_duration_seconds, db_slow_queries_total

log = logging.getLogger("app.db")


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


def _instrument_queries(engine: AsyncEngine, slow_ms: float) -> None:
    """Observe query latency; count + warn on slow queries. Dialect-agnostic."""

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _before(conn: Any, _cur: Any, _stmt: str, _p: Any, _ctx: Any, _many: bool) -> None:
        conn.info.setdefault("_q_start", []).append(time.perf_counter())

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _after(conn: Any, _cur: Any, statement: str, _p: Any, _ctx: Any, _many: bool) -> None:
        stack: list[float] = conn.info.get("_q_start", [])
        if not stack:
            return
        elapsed = time.perf_counter() - stack.pop()
        db_query_duration_seconds.observe(elapsed)
        if elapsed * 1000.0 >= slow_ms:
            db_slow_queries_total.inc()
            log.warning("slow query %.1fms: %s", elapsed * 1000.0, statement.split("\n", 1)[0][:200])


def _engine_kwargs(settings: Settings) -> dict[str, Any]:
    """Production-grade pool config for PostgreSQL; SQLite keeps its defaults
    (StaticPool for in-memory, single file for dev)."""
    kwargs: dict[str, Any] = {"echo": settings.debug, "future": True}
    if not settings.is_postgres:
        return kwargs
    connect_args: dict[str, Any] = {"timeout": settings.db_connect_timeout_seconds}
    if settings.db_statement_timeout_ms > 0:
        # asyncpg applies these Postgres GUCs per connection.
        connect_args["server_settings"] = {
            "statement_timeout": str(settings.db_statement_timeout_ms)
        }
    kwargs.update(
        pool_pre_ping=True,  # drop stale connections before use (cloud DBs cycle them)
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_timeout=settings.db_pool_timeout_seconds,
        connect_args=connect_args,
    )
    return kwargs


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return the cached async SQLAlchemy engine."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, **_engine_kwargs(settings))
    if not settings.is_postgres:
        _enable_sqlite_foreign_keys(engine)
    _instrument_queries(engine, settings.db_slow_query_ms)
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
