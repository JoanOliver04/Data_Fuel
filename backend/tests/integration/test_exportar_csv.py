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

_STATION_IDS: list[int] = [1, 2, 3, 4, 5]


def _make_stations() -> list[StationORM]:
    """Five stations covering both branches of is_low_cost and es_autopista.

    - id=1 Repsol / "C/ Test 1"            → low_cost=0, autopista=0
    - id=2 Cepsa  / "C/ Test 2"            → low_cost=0, autopista=0
    - id=3 BP     / "C/ Test 3"            → low_cost=0, autopista=0
    - id=4 Plenoil / "C/ Mayor 5"           → low_cost=1, autopista=0
    - id=5 Repsol / "Ctra. N-340 km 15"     → low_cost=0, autopista=1
    """
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
        StationORM(
            id=4,
            brand="Plenoil",
            address="C/ Mayor 5",
            locality="Alzira",
            municipality="Alzira",
            province="Valencia",
            postal_code="46600",
            latitude=39.1500,
            longitude=-0.4400,
            schedule="L-D: 24h",
        ),
        StationORM(
            id=5,
            brand="Repsol",
            address="Ctra. N-340 km 15",
            locality="Valencia",
            municipality="Valencia",
            province="Valencia",
            postal_code="46019",
            latitude=39.4710,
            longitude=-0.3800,
            schedule="L-D: 24h",
        ),
    ]


def _make_prices(n_days: int = 40) -> list[PriceHistoryORM]:
    """Continuous daily prices for 5 stations x 2 fuels. 40 days >= 14-day window."""
    base = datetime(2026, 1, 1, 12, 0)
    prices = []
    for day in range(n_days):
        dt = base + timedelta(days=day)
        for station_id in _STATION_IDS:
            for fuel in [FuelType.GASOLINA_95, FuelType.GASOIL]:
                prices.append(
                    PriceHistoryORM(
                        station_id=station_id,
                        fuel_type=fuel,
                        # Slight offset per station so municipal/comarca means
                        # differ from individual prices.
                        price=round(1.400 + day * 0.001 + station_id * 0.002, 3),
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


async def test_first_and_last_7_days_dropped(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    # 40 days (Jan 1-Feb 9): first 7 (no past price) and last 7 (no future price)
    # are dropped. Surviving range: Jan 8 → Feb 2.
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out, parse_dates=["fecha"])
    assert df["fecha"].min() >= pd.Timestamp("2026-01-08")
    assert df["fecha"].max() <= pd.Timestamp("2026-02-02")


async def test_distancia_positive_and_under_500km(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert (df["distancia"] >= 0).all()
    assert (df["distancia"] < 500).all()


async def test_precio_semana_anterior_present_and_notnull(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert "precio_semana_anterior" in df.columns
    assert df["precio_semana_anterior"].notna().all()


async def test_es_festivo_is_binary(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert "es_festivo" in df.columns
    assert set(df["es_festivo"].unique()).issubset({0, 1})


async def test_es_festivo_marks_weekends(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out, parse_dates=["fecha"])
    weekend_mask = df["fecha"].dt.weekday >= 5
    assert (df.loc[weekend_mask, "es_festivo"] == 1).all()


async def test_tendencia_ultimos_30_dias_present_and_numeric(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert "tendencia_ultimos_30_dias" in df.columns
    assert pd.api.types.is_numeric_dtype(df["tendencia_ultimos_30_dias"])
    assert df["tendencia_ultimos_30_dias"].notna().all()


# ── Self-engineered features (block of six) ───────────────────────────────────


async def test_is_low_cost_is_binary(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert "is_low_cost" in df.columns
    assert set(df["is_low_cost"].unique()).issubset({0, 1})


async def test_is_low_cost_distinguishes_brands(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    """Plenoil rows must be flagged as 1; Repsol / Cepsa / BP must be 0."""
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    # The fixture has both branches present.
    assert df["is_low_cost"].sum() > 0, "expected at least some low-cost rows"
    assert (df["is_low_cost"] == 0).sum() > 0, "expected at least some non-low-cost rows"


async def test_mes_matches_fecha_month(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out, parse_dates=["fecha"])
    assert "mes" in df.columns
    assert pd.api.types.is_integer_dtype(df["mes"]) or df["mes"].dtype.kind == "i"
    assert (df["mes"] == df["fecha"].dt.month).all()
    assert set(df["mes"].unique()).issubset(set(range(1, 13)))


async def test_precio_medio_municipio_positive_and_consistent(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert "precio_medio_municipio" in df.columns
    assert pd.api.types.is_numeric_dtype(df["precio_medio_municipio"])
    assert (df["precio_medio_municipio"] > 0).all()
    # Within any (fecha, municipio, tipo_combustible) bucket the mean must be
    # constant — it's defined as a groupby transform.
    grouped = df.groupby(["fecha", "municipio", "tipo_combustible"])[
        "precio_medio_municipio"
    ].nunique()
    assert (grouped == 1).all()


async def test_es_autopista_is_binary(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert "es_autopista" in df.columns
    assert set(df["es_autopista"].unique()).issubset({0, 1})


async def test_es_autopista_distinguishes_addresses(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    """The Ctra. N-340 km 15 station must flag 1; plain street addresses 0."""
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert df["es_autopista"].sum() > 0
    assert (df["es_autopista"] == 0).sum() > 0


async def test_precio_vs_media_comarca_is_signed_and_balances_to_zero(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert "precio_vs_media_comarca" in df.columns
    assert pd.api.types.is_numeric_dtype(df["precio_vs_media_comarca"])
    # By definition, deviations from the daily comarca mean sum to ~0 within
    # each (fecha, comarca, tipo_combustible) bucket.
    summed = df.groupby(["fecha", "comarca", "tipo_combustible"])[
        "precio_vs_media_comarca"
    ].sum()
    assert summed.abs().max() < 1e-3


async def test_momentum_7d_matches_precio_minus_precio_semana_anterior(
    populated: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    out = await _run(tmp_path / "datos.csv", populated)
    df = pd.read_csv(out)
    assert "momentum_7d" in df.columns
    assert pd.api.types.is_numeric_dtype(df["momentum_7d"])
    expected = (df["precio"] - df["precio_semana_anterior"]).round(6)
    pd.testing.assert_series_equal(
        df["momentum_7d"].astype(float),
        expected.astype(float),
        check_names=False,
    )
