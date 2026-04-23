"""Integration tests for SQLAlchemy ORM models against in-memory SQLite."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import FuelType
from app.infrastructure.database.models import PriceHistoryORM, StationORM


def _build_station(station_id: int = 1) -> StationORM:
    return StationORM(
        id=station_id,
        brand="REPSOL",
        address="Calle Mayor 1",
        locality="Madrid",
        municipality="Madrid",
        province="MADRID",
        postal_code="28001",
        latitude=40.4,
        longitude=-3.7,
        schedule="L-D: 24H",
    )


async def test_insert_and_read_station(db: AsyncSession) -> None:
    db.add(_build_station())
    await db.commit()

    stations = (await db.execute(select(StationORM))).scalars().all()
    assert len(stations) == 1
    assert stations[0].brand == "REPSOL"
    assert stations[0].latitude == 40.4
    assert stations[0].created_at is not None
    assert stations[0].updated_at is not None


async def test_insert_price_history_with_fk(db: AsyncSession) -> None:
    db.add(_build_station())
    await db.flush()
    db.add(
        PriceHistoryORM(
            station_id=1,
            fuel_type=FuelType.GASOLINE_95_E5,
            price=Decimal("1.595"),
            recorded_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
        ),
    )
    await db.commit()

    rows = (await db.execute(select(PriceHistoryORM))).scalars().all()
    assert len(rows) == 1
    assert rows[0].station_id == 1
    assert rows[0].fuel_type == FuelType.GASOLINE_95_E5
    assert rows[0].price == Decimal("1.595")


async def test_station_relationship_loads_prices(db: AsyncSession) -> None:
    station = _build_station()
    db.add(station)
    await db.flush()
    db.add_all(
        [
            PriceHistoryORM(
                station_id=1,
                fuel_type=FuelType.GASOLINE_95_E5,
                price=Decimal("1.595"),
            ),
            PriceHistoryORM(
                station_id=1,
                fuel_type=FuelType.DIESEL_A,
                price=Decimal("1.499"),
            ),
        ],
    )
    await db.commit()

    fetched = (
        await db.execute(
            select(StationORM).where(StationORM.id == 1),
        )
    ).scalar_one()
    prices = list(await fetched.awaitable_attrs.price_history)

    assert {p.fuel_type for p in prices} == {FuelType.GASOLINE_95_E5, FuelType.DIESEL_A}


async def test_cascade_delete_removes_price_history(db: AsyncSession) -> None:
    station = _build_station()
    db.add(station)
    await db.flush()
    db.add(
        PriceHistoryORM(
            station_id=1,
            fuel_type=FuelType.DIESEL_A,
            price=Decimal("1.499"),
        ),
    )
    await db.commit()

    await db.delete(station)
    await db.commit()

    rows = (await db.execute(select(PriceHistoryORM))).scalars().all()
    assert rows == []
