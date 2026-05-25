"""Dialect-portable SQL helpers (SQLite ⇄ PostgreSQL).

Keeps dialect-specific SQL in one place so repositories and the analytics layer
stay database-agnostic. Both supported dialects expose the same
``insert(...).on_conflict_do_update`` upsert API and time-formatting functions;
this module picks the right one from the active ``DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Literal

from sqlalchemy import Insert, func
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import get_settings

Granularity = Literal["hour", "day"]


def active_dialect() -> Literal["postgresql", "sqlite"]:
    return "postgresql" if get_settings().is_postgres else "sqlite"


# strftime (SQLite) vs to_char (PostgreSQL) patterns that yield the SAME label
# string for a given bucket, so output is identical across dialects.
_PG_TIME_FMT: dict[Granularity, str] = {"hour": 'YYYY-MM-DD"T"HH24', "day": "YYYY-MM-DD"}
_SQLITE_TIME_FMT: dict[Granularity, str] = {"hour": "%Y-%m-%dT%H", "day": "%Y-%m-%d"}


def time_bucket(column: Any, granularity: Granularity) -> ColumnElement[str]:
    """Format a timestamp column into a groupable bucket label, per dialect.

    ``column`` is any timestamp SQL expression (mapped attribute or column).
    """
    if active_dialect() == "postgresql":
        return func.to_char(column, _PG_TIME_FMT[granularity])
    return func.strftime(_SQLITE_TIME_FMT[granularity], column)


def build_upsert(
    table: Any,
    values: Sequence[dict[str, Any]],
    *,
    index_elements: Sequence[str],
    update_keys: Iterable[str],
) -> Insert:
    """INSERT … ON CONFLICT (index_elements) DO UPDATE — portable across dialects.

    Both ``postgresql`` and ``sqlite`` dialect inserts share this API and the
    ``excluded`` pseudo-table, so the only difference is which ``insert`` to call.
    """
    keys = list(update_keys)
    indexes = list(index_elements)
    if active_dialect() == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        pg = pg_insert(table).values(list(values))
        return pg.on_conflict_do_update(
            index_elements=indexes, set_={k: getattr(pg.excluded, k) for k in keys}
        )
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    sl = sqlite_insert(table).values(list(values))
    return sl.on_conflict_do_update(
        index_elements=indexes, set_={k: getattr(sl.excluded, k) for k in keys}
    )
