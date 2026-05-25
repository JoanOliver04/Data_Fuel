"""Copy all Data Fuel data from a SQLite database into PostgreSQL.

Idempotent and rollback-safe: rows are inserted with ``ON CONFLICT (id) DO
NOTHING`` inside per-table transactions, so re-running never duplicates and a
failure mid-table rolls that table back. Tables are copied in FK order, then the
PostgreSQL identity sequences are advanced past the imported ids.

Usage (local or against a cloud DB):

    python scripts/migrate_sqlite_to_postgres.py \\
        --source "sqlite+aiosqlite:///./datafuel.db" \\
        --target "postgresql+asyncpg://user:pass@host:5432/datafuel"

The target schema is created if missing (``--no-create-schema`` to skip when
Alembic already ran). Bare ``postgres://`` / ``postgresql://`` targets (Railway/
Render/Heroku) are upgraded to the asyncpg driver automatically.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

import app.alerts.models
import app.infrastructure.database.models  # noqa: F401  (register core tables)
from app.infrastructure.database.base import Base

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("migrate")

_CHUNK = 500


def _to_asyncpg(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


async def _copy_table(src: AsyncEngine, dst: AsyncEngine, table: Table) -> None:
    async with src.connect() as sconn:
        rows = [dict(r._mapping) for r in (await sconn.execute(select(table))).all()]
    if not rows:
        log.info("%-16s source=0 (skipped)", table.name)
        return

    inserted = 0
    async with dst.begin() as dconn:
        for i in range(0, len(rows), _CHUNK):
            stmt = pg_insert(table).values(rows[i : i + _CHUNK]).on_conflict_do_nothing()
            result = await dconn.execute(stmt)
            inserted += result.rowcount or 0

    async with dst.connect() as dconn:
        target_count = (
            await dconn.execute(select(func.count()).select_from(table))
        ).scalar_one()
    log.info(
        "%-16s source=%d inserted=%d target=%d", table.name, len(rows), inserted, target_count
    )
    if int(target_count) < len(rows):
        log.warning("%s: target has fewer rows than source — investigate", table.name)


async def _reset_sequences(dst: AsyncEngine) -> None:
    """Advance each id sequence past the imported max so future inserts don't collide."""
    async with dst.begin() as dconn:
        for table in Base.metadata.sorted_tables:
            if "id" not in table.c:
                continue
            await dconn.exec_driver_sql(
                f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                f"(SELECT COALESCE(MAX(id), 1) FROM {table.name}))"
            )
    log.info("identity sequences reset")


async def _migrate(source_url: str, target_url: str, *, create_schema: bool) -> None:
    src = create_async_engine(source_url)
    dst = create_async_engine(target_url)
    try:
        if create_schema:
            async with dst.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            log.info("target schema ensured")
        for table in Base.metadata.sorted_tables:  # FK-safe (parents first)
            await _copy_table(src, dst, table)
        await _reset_sequences(dst)
    finally:
        await src.dispose()
        await dst.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Data Fuel SQLite → PostgreSQL")
    parser.add_argument("--source", default="sqlite+aiosqlite:///./datafuel.db")
    parser.add_argument("--target", required=True, help="postgresql+asyncpg://user:pass@host/db")
    parser.add_argument(
        "--no-create-schema", action="store_true", help="skip create_all (Alembic already ran)"
    )
    args = parser.parse_args()

    target = _to_asyncpg(args.target)
    if not target.startswith("postgresql+asyncpg:"):
        parser.error("--target must be a PostgreSQL URL")
    asyncio.run(_migrate(args.source, target, create_schema=not args.no_create_schema))
    log.info("migration complete")


if __name__ == "__main__":
    main()
