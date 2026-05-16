"""Download historical MITECO fuel price data into the local SQLite database.

Usage (run from backend/ directory):
    # Last 90 calendar days (today excluded — Ministry data not yet published)
    python scripts/descargar_historico.py --last-n-days 90

    # Explicit date range (ISO 8601, both inclusive)
    python scripts/descargar_historico.py --start-date 2024-01-01 --end-date 2024-03-31

Idempotent: dates that already have rows in price_history are skipped.
Rate-limited to ~1.6 req/s to respect the Ministry's server.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import ssl
import sys
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import httpx
import truststore
from sqlalchemy import CursorResult, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Allow `app.*` imports when executed as a top-level script from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM
from app.infrastructure.database.session import get_session_factory
from app.infrastructure.external.miteco.schemas import MitecoApiResponse, MitecoStation
from app.repositories.price_repository import PriceRepository

# ── Configuration ──────────────────────────────────────────────────────────────

_BASE_URL = (
    "https://sedeaplicaciones.minetur.gob.es"
    "/ServiciosRESTCarburantes/PreciosCarburantes"
)
# MITECO historical path — date parameter must be DD-MM-YYYY (Spanish format).
_HIST_PATH = "/EstacionesTerrestresHist/{fecha}"

_REQUEST_DELAY = 0.6   # seconds between requests ≈ 1.6 req/s
_TIMEOUT = 30.0
_STATION_CHUNK = 60    # matches StationRepository._CHUNK (999-param SQLite limit)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── SSL (mirrors MitecoClient — Spanish CA + legacy cipher quirks) ─────────────

def _ssl_ctx() -> ssl.SSLContext:
    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.set_ciphers("DEFAULT@SECLEVEL=0")
    return ctx


# ── Date utilities ─────────────────────────────────────────────────────────────

def _date_range(start: date, end: date) -> list[date]:
    """Return an inclusive list [start, end]."""
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _miteco_fmt(d: date) -> str:
    """Convert to DD-MM-YYYY — the format the MITECO history endpoint expects."""
    return d.strftime("%d-%m-%Y")


def _day_window(d: date) -> tuple[datetime, datetime]:
    """UTC midnight boundaries for idempotency check: [00:00, 00:00 next day)."""
    midnight = datetime(d.year, d.month, d.day, tzinfo=UTC)
    return midnight, midnight + timedelta(days=1)


# ── Idempotency check ──────────────────────────────────────────────────────────

async def _already_loaded(
    factory: async_sessionmaker[AsyncSession], d: date
) -> bool:
    """Return True if price_history already has rows for this calendar date (UTC)."""
    lo, hi = _day_window(d)
    async with factory() as session:
        result = await session.execute(
            select(func.count()).where(
                PriceHistoryORM.recorded_at >= lo,
                PriceHistoryORM.recorded_at < hi,
            )
        )
        return result.scalar_one() > 0


# ── HTTP fetch ─────────────────────────────────────────────────────────────────

async def _fetch_day(
    client: httpx.AsyncClient, d: date
) -> MitecoApiResponse | None:
    url = f"{_BASE_URL}{_HIST_PATH.format(fecha=_miteco_fmt(d))}"
    log.info("  GET %s", url)
    t0 = time.perf_counter()
    try:
        r = await client.get(url)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        log.error("  HTTP error after %.1f ms: %s", (time.perf_counter() - t0) * 1000, exc)
        return None

    elapsed_ms = (time.perf_counter() - t0) * 1000
    size_kb = len(r.content) / 1024
    log.info("  → %d  (%.1f ms, %.1f KB)", r.status_code, elapsed_ms, size_kb)

    try:
        return MitecoApiResponse.model_validate(json.loads(r.content))
    except (json.JSONDecodeError, ValueError) as exc:
        log.error("  Parse failed: %s", exc)
        return None


# ── Persistence helpers ────────────────────────────────────────────────────────

def _dec(v: float | None) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _station_row(ms: MitecoStation, now: datetime) -> dict[str, Any]:
    return {
        "id": ms.id,
        "brand": ms.brand,
        "address": ms.address,
        "locality": ms.locality,
        "municipality": ms.municipality,
        "province": ms.province,
        "postal_code": ms.postal_code,
        "latitude": ms.latitude,
        "longitude": ms.longitude,
        "schedule": ms.schedule,
        "price_gasoline_95_e5": _dec(ms.price_gasoline_95_e5),
        "price_gasoline_95_e10": _dec(ms.price_gasoline_95_e10),
        "price_gasoline_98_e5": _dec(ms.price_gasoline_98_e5),
        "price_diesel_a": _dec(ms.price_diesel_a),
        "price_diesel_premium": _dec(ms.price_diesel_premium),
        "updated_at": now,
    }


def _price_rows(ms: MitecoStation, recorded_at: datetime) -> list[dict[str, Any]]:
    rows = []
    for fuel_type, price in ms.prices_by_fuel().items():
        if price is not None:
            rows.append(
                {
                    "station_id": ms.id,
                    "fuel_type": fuel_type,
                    "price": _dec(price),
                    "recorded_at": recorded_at,
                }
            )
    return rows


async def _persist_day(
    factory: async_sessionmaker[AsyncSession],
    response: MitecoApiResponse,
    d: date,
) -> tuple[int, int]:
    """Upsert new stations (ignore existing) and insert price rows.

    Uses noon UTC of the fetched date as the canonical recorded_at so the
    idempotency window check ([00:00, 00:00+1d)) reliably covers every row.

    Returns (new_stations_inserted, price_rows_inserted).
    """
    recorded_at = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC)

    station_rows: list[dict[str, Any]] = []
    price_rows: list[dict[str, Any]] = []
    skipped = 0

    for ms in response.stations:
        if ms.latitude is None or ms.longitude is None:
            skipped += 1
            continue
        station_rows.append(_station_row(ms, recorded_at))
        price_rows.extend(_price_rows(ms, recorded_at))

    if skipped:
        log.warning("  Skipped %d stations without coordinates", skipped)

    async with factory() as session:
        # INSERT OR IGNORE — existing stations keep their current live prices.
        new_stations = 0
        for i in range(0, len(station_rows), _STATION_CHUNK):
            result = cast(
                CursorResult[Any],
                await session.execute(
                    sqlite_insert(StationORM)
                    .values(station_rows[i : i + _STATION_CHUNK])
                    .on_conflict_do_nothing(index_elements=["id"])
                ),
            )
            new_stations += result.rowcount

        prices_inserted = await PriceRepository(session).insert_many(price_rows)
        await session.commit()

    return new_stations, prices_inserted


# ── Main download loop ─────────────────────────────────────────────────────────

async def _run(dates: list[date]) -> None:
    factory = get_session_factory()

    async with httpx.AsyncClient(
        timeout=_TIMEOUT,
        headers={"Accept": "application/json"},
        verify=_ssl_ctx(),
    ) as client:
        for idx, d in enumerate(dates, start=1):
            log.info("[%d/%d] %s", idx, len(dates), d.isoformat())

            if await _already_loaded(factory, d):
                log.info("  Already in DB — skipping")
                continue

            response = await _fetch_day(client, d)
            if response is None:
                log.warning("  No data returned — skipping date")
                await asyncio.sleep(_REQUEST_DELAY)
                continue

            new_stations, prices = await _persist_day(factory, response, d)
            log.info("  Saved: %d new stations, %d price rows", new_stations, prices)

            # Throttle: max ~1.6 req/s, respectful of the Ministry's server.
            await asyncio.sleep(_REQUEST_DELAY)

    log.info("Done. Processed %d dates.", len(dates))


# ── CLI ────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Download MITECO historical fuel prices into the local DB."
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--last-n-days",
        type=int,
        metavar="N",
        help="Download the last N calendar days (today is excluded — not yet published).",
    )
    group.add_argument(
        "--start-date",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="Explicit range start (requires --end-date).",
    )
    p.add_argument(
        "--end-date",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="Explicit range end, inclusive (required when --start-date is given).",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    today = date.today()

    if args.last_n_days is not None:
        end = today - timedelta(days=1)  # yesterday — today not yet published
        start = end - timedelta(days=args.last_n_days - 1)
    else:
        if args.end_date is None:
            sys.exit("--end-date is required when --start-date is given.")
        start, end = args.start_date, args.end_date
        if start > end:
            sys.exit("--start-date must not be after --end-date.")
        if end >= today:
            sys.exit("--end-date must be in the past (today's data not yet published).")

    dates = _date_range(start, end)
    log.info(
        "Downloading %d days: %s → %s",
        len(dates),
        start.isoformat(),
        end.isoformat(),
    )
    asyncio.run(_run(dates))


if __name__ == "__main__":
    main()
