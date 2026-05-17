"""Export price_history + stations from SQLite to datos.csv for ML training.

Usage (run from backend/):
    python scripts/exportar_datos_csv.py

Output columns (strict order):
    fecha, precio, municipio, distancia, tipo_combustible, comarca,
    dia_de_la_semana, es_festivo, precio_semana_anterior,
    tendencia_ultimos_30_dias, precio_prox_semana

- precio_prox_semana: price of the same station+fuel 7 days later.
- precio_semana_anterior: price of the same station+fuel 7 days earlier.
- tendencia_ultimos_30_dias: precio - rolling 30-day mean (same station+fuel).
- es_festivo: 1 if weekend (sat/sun) or Spanish fixed national holiday, else 0.

Rows without precio_prox_semana (last 7 days) or precio_semana_anterior
(first 7 days) are dropped.
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
    "es_festivo",
    "precio_semana_anterior",
    "tendencia_ultimos_30_dias",
    "precio_prox_semana",
]

# Fixed-date Spanish national holidays (movable ones like Easter excluded
# to keep the mapping deterministic).
_HOLIDAYS_ES_FIXED: frozenset[tuple[int, int]] = frozenset({
    (1, 1),    # Año Nuevo
    (1, 6),    # Reyes
    (5, 1),    # Día del Trabajo
    (8, 15),   # Asunción
    (10, 12),  # Fiesta Nacional
    (11, 1),   # Todos los Santos
    (12, 6),   # Constitución
    (12, 8),   # Inmaculada
    (12, 25),  # Navidad
})

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


def _es_festivo(d: datetime) -> int:
    """1 if weekend or Spanish fixed national holiday, else 0."""
    if d.weekday() >= 5:
        return 1
    if (d.month, d.day) in _HOLIDAYS_ES_FIXED:
        return 1
    return 0


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
            "es_festivo": _es_festivo(recorded_at),
        })

    if skipped:
        log.warning("Skipped %d rows with unrecognised fuel_type values", skipped)

    df = pd.DataFrame(records)
    df["fecha"] = pd.to_datetime(df["fecha"])
    log.info("Rows fetched: %d", len(df))

    # Aggregate one representative price per (station, fuel, date) for all
    # temporal derivations to avoid cartesian products when multiple recordings
    # exist on the same day.
    agg = (
        df.groupby(["_station_id", "tipo_combustible", "fecha"], as_index=False)["precio"]
        .mean()
        .sort_values(["_station_id", "tipo_combustible", "fecha"])
        .reset_index(drop=True)
    )

    # precio_prox_semana: same station+fuel exactly 7 days later.
    df_next = agg.rename(columns={"precio": "precio_prox_semana"}).copy()
    df_next["fecha"] = df_next["fecha"] - pd.Timedelta(days=7)

    # precio_semana_anterior: same station+fuel exactly 7 days earlier.
    df_prev = agg.rename(columns={"precio": "precio_semana_anterior"}).copy()
    df_prev["fecha"] = df_prev["fecha"] + pd.Timedelta(days=7)

    # tendencia_ultimos_30_dias: precio minus rolling 30-day mean per series.
    # min_periods=1 keeps early rows (trend defined from day 1).
    agg["_rolling_30"] = (
        agg.groupby(["_station_id", "tipo_combustible"])["precio"]
        .transform(lambda s: s.rolling(window=30, min_periods=1).mean())
    )
    agg["tendencia_ultimos_30_dias"] = (agg["precio"] - agg["_rolling_30"]).round(6)
    df_trend = agg[
        ["_station_id", "tipo_combustible", "fecha", "tendencia_ultimos_30_dias"]
    ]

    df = df.merge(df_next, on=["_station_id", "tipo_combustible", "fecha"], how="left")
    df = df.merge(df_prev, on=["_station_id", "tipo_combustible", "fecha"], how="left")
    df = df.merge(df_trend, on=["_station_id", "tipo_combustible", "fecha"], how="left")
    df = df.drop(columns=["_station_id"]).dropna(
        subset=["precio_prox_semana", "precio_semana_anterior"]
    )
    log.info(
        "Rows after dropping first/last 7-day windows (no past/future price): %d",
        len(df),
    )

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
