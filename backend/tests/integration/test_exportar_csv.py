"""Integration tests for scripts/exportar_datos_csv.py."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database import session as db_session
from app.infrastructure.database.models.price_history import PriceHistoryORM
from app.infrastructure.database.models.station import StationORM

# Add scripts/ to the module search path for a direct import of the exporter.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from exportar_datos_csv import COLUMN_ORDER, _run  # noqa: E402, I001


# ── Test data ─────────────────────────────────────────────────────────────────

def _make_stations() -> list[StationORM]:
    return [
        StationORM(
            id=1,
            brand="Repsol",
            address="C/ Test 1",
            locality="Valencia",
            municipality="Valencia",
            province="Valencia",
            postal_code="46001",
            latitude=39.4697,
            longitude=-0.3774,
            schedule="L-D: 06:00-22:00",
        ),
        StationORM(
            id=2,
            brand="Cepsa",
            address="C/ Test 2",
            locality="Alzira",
            municipality="Alzira",
            province="Valencia",
            postal_code="46600",
            latitude=39.1496,
            longitude=-0.4373,
            schedule="L-D: 06:00-22:00",
        ),
        StationORM(
            id=3,
            brand="BP",
            address="C/ Test 3",
            locality="Madrid",
            municipality="Madrid",
            province="Madrid",
            postal_code="28001",
            latitude=40.4168,
            longitude=-3.7038,
            schedule="L-D: 24h",
        ),
    ]


def _make_prices(n_days: int = 30) -> list[PriceHistoryORM]:
    base = datetime(2026, 1, 1, 12, 0)
    prices = []
    for day in range(n_days):
        dt = base + timedelta(days=day)
        for station_id in [1, 2, 3]:
            for fuel in [FuelType.GASOLINA_95, FuelType.GASOIL]:
                prices.append(
                    PriceHistoryORM(
                        station_id=station_id,
                        fuel_type=fuel,
                        price=round(1.400 + day * 0.001, 3),
                        recorded_at=dt,
                    )
                )
    return prices


# ── Fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture
async def populated(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Seed the in-memory DB and return the session factory."""
    factory = db_session.get_session_factory()
    async with factory() as session:
        session.add_all(_make_stations())
        await session.flush()
        session.add_all(_make_prices())
        await session.commit()
    return factory


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_column_order_exact(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert list(df.columns) == COLUMN_ORDER


async def test_precio_prox_semana_present_and_notnull(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert "precio_prox_semana" in df.columns
    assert df["precio_prox_semana"].notna().all()


async def test_last_7_days_dropped(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    # 30 days (Jan 1-30): rows from Jan 24-30 have no 7-day future price -> dropped.
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out, parse_dates=["fecha"])
    assert df["fecha"].max() <= pd.Timestamp("2026-01-23")


async def test_distancia_positive_and_under_500km(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert (df["distancia"] >= 0).all()
    assert (df["distancia"] < 500).all()
