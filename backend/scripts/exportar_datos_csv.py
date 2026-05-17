"""Export price_history + stations from SQLite to datos.csv for ML training.

Usage (run from backend/):
    python scripts/exportar_datos_csv.py

Output columns (strict order, 17 total):
    fecha, precio, municipio, distancia, tipo_combustible, comarca,
    dia_de_la_semana, es_festivo, precio_semana_anterior,
    tendencia_ultimos_30_dias, is_low_cost, mes, precio_medio_municipio,
    es_autopista, precio_vs_media_comarca, momentum_7d, precio_prox_semana

Derived features:
- es_festivo: 1 if weekend (sat/sun) or Spanish fixed national holiday, else 0.
- precio_semana_anterior: price of the same station+fuel 7 days earlier.
- tendencia_ultimos_30_dias: precio - rolling 30-day mean (same station+fuel).
- is_low_cost: 1 if station brand matches a known low-cost label, else 0.
- mes: month number (1-12) extracted from fecha.
- precio_medio_municipio: mean price that day for (municipio, fuel).
- es_autopista: 1 if brand/address contains a highway pattern, else 0.
- precio_vs_media_comarca: precio - mean price that day for (comarca, fuel).
- momentum_7d: precio - precio_semana_anterior (short-term velocity).
- precio_prox_semana: price of the same station+fuel 7 days later (target).

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
from app.ml.data.holidays import is_festivo as _shared_is_festivo

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
    "is_low_cost",
    "mes",
    "precio_medio_municipio",
    "es_autopista",
    "precio_vs_media_comarca",
    "momentum_7d",
    "precio_prox_semana",
]

# Known low-cost brand labels (substring match, case-insensitive).
_LOW_COST_BRANDS: frozenset[str] = frozenset({
    "PLENOIL",
    "PETROPRIX",
    "BALLENOIL",
    "GASAUTO",
    "FAMILY",
    "EASYGAS",
    "CHEAP",
})

# Spanish road / highway patterns (substring match on brand + address, upper).
_HIGHWAY_PATTERNS: tuple[str, ...] = (
    "A-",
    "AP-",
    "N-",
    "CV-",
    "CARRETERA",
    "CTRA",
    "KM",
)

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


def _is_low_cost(brand: str) -> int:
    """1 if station brand contains a known low-cost label, else 0."""
    upper = brand.upper()
    return 1 if any(lc in upper for lc in _LOW_COST_BRANDS) else 0


def _es_autopista(brand: str, address: str) -> int:
    """1 if brand or address contains a Spanish road/highway pattern, else 0."""
    upper = f"{brand} {address}".upper()
    return 1 if any(p in upper for p in _HIGHWAY_PATTERNS) else 0


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
                StationORM.brand,
                StationORM.address,
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
        brand = str(row.brand or "")
        address = str(row.address or "")

        records.append({
            "_station_id": int(row.station_id),
            "fecha": recorded_at.date(),
            "precio": float(row.price),
            "municipio": municipio,
            "distancia": dist_cache[coord],
            "tipo_combustible": FUEL_TYPE_TO_ID[fuel_type],
            "comarca": comarcas.get(municipio, "Sin Comarca"),
            "dia_de_la_semana": recorded_at.weekday(),
            "es_festivo": _shared_is_festivo(recorded_at),
            "is_low_cost": _is_low_cost(brand),
            "mes": recorded_at.month,
            "es_autopista": _es_autopista(brand, address),
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

    # momentum_7d: short-term price velocity. Safe to compute after the dropna
    # since precio_semana_anterior is guaranteed non-null at this point.
    df["momentum_7d"] = (df["precio"] - df["precio_semana_anterior"]).round(6)

    # precio_medio_municipio: daily local market average per (municipio, fuel).
    df["precio_medio_municipio"] = (
        df.groupby(["fecha", "municipio", "tipo_combustible"])["precio"]
        .transform("mean")
        .round(6)
    )

    # precio_vs_media_comarca: deviation of this row's price from the daily
    # comarca-level mean per fuel. Positive ⇒ this station is dearer than its
    # comarca that day; negative ⇒ cheaper.
    df["precio_vs_media_comarca"] = (
        df["precio"]
        - df.groupby(["fecha", "comarca", "tipo_combustible"])["precio"].transform("mean")
    ).round(6)

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
