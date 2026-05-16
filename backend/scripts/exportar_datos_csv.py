"""Export price_history + stations from SQLite to datos.csv for ML training.

Usage (run from backend/):
    python scripts/exportar_datos_csv.py

Output columns (strict order):
    fecha, precio, municipio, distancia, tipo_combustible, comarca,
    dia_de_la_semana, precio_prox_semana

precio_prox_semana is the price of the same station+fuel 7 days later.
Rows without a match (last 7 days of history) are dropped.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from geopy.distance import geodesic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Allow `app.*` imports when executed as a top-level script from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM
from app.infrastructure.database.session import get_session_factory
from app.ml.data.fuel_type_mapping import FUEL_TYPE_TO_ID, resolve_fuel_type

# ── Configuration ─────────────────────────────────────────────────────────────

_ALZIRA: tuple[float, float] = (39.1496, -0.4373)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_COMARCAS_PATH = _BACKEND_DIR / "app" / "ml" / "data" / "comarcas_valencia.json"
_OUTPUT_PATH = _BACKEND_DIR / "data" / "datos.csv"

COLUMN_ORDER: list[str] = [
    "fecha",
    "precio",
    "municipio",
    "distancia",
    "tipo_combustible",
    "comarca",
    "dia_de_la_semana",
    "precio_prox_semana",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_comarcas() -> dict[str, str]:
    with _COMARCAS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _geodesic_km(lat: float, lon: float) -> float:
    return round(geodesic(_ALZIRA, (lat, lon)).km, 4)


def _coerce_datetime(value: Any) -> datetime:
    """Return a datetime, parsing ISO strings that aiosqlite may return as str."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


# ── Core async logic ──────────────────────────────────────────────────────────


async def _fetch_all(factory: async_sessionmaker[AsyncSession]) -> list[Any]:
    async with factory() as session:
        stmt = (
            select(
                PriceHistoryORM.station_id,
                PriceHistoryORM.recorded_at,
                PriceHistoryORM.price,
                PriceHistoryORM.fuel_type,
                StationORM.municipality,
                StationORM.latitude,
                StationORM.longitude,
            )
            .join(StationORM, PriceHistoryORM.station_id == StationORM.id)
            .order_by(PriceHistoryORM.recorded_at)
        )
        result = await session.execute(stmt)
        return result.all()


async def _run(
    output_path: Path,
    factory: async_sessionmaker[AsyncSession] | None = None,
) -> Path:
    if factory is None:
        factory = get_session_factory()

    comarcas = _load_comarcas()
    raw = await _fetch_all(factory)
    log.info("Fetched %d rows from price_history JOIN stations", len(raw))

    if not raw:
        raise RuntimeError("No rows in price_history — populate the DB first.")

    # Cache geodesic distances per (lat, lon) to avoid redundant calculations.
    dist_cache: dict[tuple[float, float], float] = {}
    records: list[dict[str, Any]] = []
    skipped = 0

    for row in raw:
        fuel_type = resolve_fuel_type(str(row.fuel_type))
        if fuel_type is None:
            skipped += 1
            continue

        coord = (float(row.latitude), float(row.longitude))
        if coord not in dist_cache:
            dist_cache[coord] = _geodesic_km(*coord)

        recorded_at = _coerce_datetime(row.recorded_at)
        municipio = str(row.municipality)

        records.append({
            "_station_id": int(row.station_id),
            "fecha": recorded_at.date(),
            "precio": float(row.price),
            "municipio": municipio,
            "distancia": dist_cache[coord],
            "tipo_combustible": FUEL_TYPE_TO_ID[fuel_type],
            "comarca": comarcas.get(municipio, "Sin Comarca"),
            "dia_de_la_semana": recorded_at.weekday(),
        })

    if skipped:
        log.warning("Skipped %d rows with unrecognised fuel_type values", skipped)

    df = pd.DataFrame(records)
    df["fecha"] = pd.to_datetime(df["fecha"])
    log.info("Rows fetched: %d", len(df))

    # Self-join: for each row find the price of the same station+fuel 7 days later.
    # Aggregate to one representative price per (station, fuel, date) before merging
    # to avoid a cartesian product when multiple recordings exist on the same day.
    df_next = (
        df.groupby(["_station_id", "tipo_combustible", "fecha"], as_index=False)["precio"]
        .mean()
        .rename(columns={"precio": "precio_prox_semana"})
    )
    df_next["fecha"] = df_next["fecha"] - pd.Timedelta(days=7)

    df = df.merge(df_next, on=["_station_id", "tipo_combustible", "fecha"], how="left")
    df = df.drop(columns=["_station_id"]).dropna(subset=["precio_prox_semana"])
    log.info("Rows after dropping last-7-days (no future price): %d", len(df))

    df = df[COLUMN_ORDER]
    log.info("DataFrame shape: %d rows x %d columns", len(df), len(df.columns))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    log.info("Exported → %s", output_path)
    return output_path


# ── Public entry point (used by tests and __main__) ───────────────────────────


def exportar_datos_csv(
    output_path: Path = _OUTPUT_PATH,
    factory: async_sessionmaker[AsyncSession] | None = None,
) -> Path:
    """Export price history to CSV. Pass a custom factory in tests."""
    return asyncio.run(_run(output_path, factory))


if __name__ == "__main__":
    exportar_datos_csv()
