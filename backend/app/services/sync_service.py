"""Syncs MITECO fuel price data into the local database."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.cache import recommendations_cache
from app.infrastructure.external.miteco.client import MitecoClient, MitecoClientError
from app.infrastructure.external.miteco.schemas import MitecoStation
from app.repositories.price_repository import PriceRepository
from app.repositories.station_repository import StationRepository

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SyncResult:
    stations_synced: int
    stations_skipped: int
    prices_recorded: int


class SyncService:
    """Fetches all stations from the MITECO API and persists them to the database."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def run(self) -> SyncResult:
        log.info("Starting MITECO sync")
        try:
            async with MitecoClient() as client:
                response = await client.get_all_stations()
        except MitecoClientError:
            log.exception("MITECO API request failed — sync aborted")
            raise

        now = datetime.now(UTC)
        station_rows: list[dict[str, Any]] = []
        price_rows: list[dict[str, Any]] = []
        skipped = 0

        for ms in response.stations:
            if ms.latitude is None or ms.longitude is None:
                skipped += 1
                continue
            station_rows.append(_station_dict(ms, now))
            price_rows.extend(_price_dicts(ms, now))

        async with self._session_factory() as session:
            await StationRepository(session).upsert_many(station_rows)
            await PriceRepository(session).insert_many(price_rows)
            await session.commit()

        # Cached recommendations embed prices and rankings that are now stale.
        await recommendations_cache.clear()

        result = SyncResult(
            stations_synced=len(station_rows),
            stations_skipped=skipped,
            prices_recorded=len(price_rows),
        )
        log.info(
            "MITECO sync complete: %d synced, %d skipped, %d prices",
            result.stations_synced,
            result.stations_skipped,
            result.prices_recorded,
        )
        return result


def _station_dict(ms: MitecoStation, now: datetime) -> dict[str, Any]:
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


def _price_dicts(ms: MitecoStation, now: datetime) -> list[dict[str, Any]]:
    rows = []
    for fuel_type, value in ms.prices_by_fuel().items():
        if value is not None:
            rows.append(
                {
                    "station_id": ms.id,
                    "fuel_type": fuel_type,
                    "price": _dec(value),
                    "recorded_at": now,
                }
            )
    return rows


def _dec(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))
