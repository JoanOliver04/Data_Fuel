"""Unit tests for the cost calculator domain service."""

import math
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import (
    StationCost,
    haversine_km,
    rank_stations,
)
from app.infrastructure.database.models.station import StationORM


# ── haversine_km ──────────────────────────────────────────────────────────


def test_haversine_same_point():
    assert haversine_km(40.0, -3.0, 40.0, -3.0) == pytest.approx(0.0, abs=1e-9)


def test_haversine_known_distance():
    # Madrid (40.4168, -3.7038) → Barcelona (41.3851, 2.1734) ≈ 505 km straight line.
    dist = haversine_km(40.4168, -3.7038, 41.3851, 2.1734)
    assert 490 < dist < 520


def test_haversine_symmetry():
    d1 = haversine_km(39.47, -0.376, 40.41, -3.70)
    d2 = haversine_km(40.41, -3.70, 39.47, -0.376)
    assert d1 == pytest.approx(d2, rel=1e-9)


# ── helpers ───────────────────────────────────────────────────────────────


def _make_orm(
    station_id: int,
    lat: float,
    lon: float,
    price_gasoline_95_e5: Decimal | None = Decimal("1.595"),
    price_diesel_a: Decimal | None = Decimal("1.489"),
) -> StationORM:
    orm = MagicMock(spec=StationORM)
    orm.id = station_id
    orm.brand = "TEST"
    orm.address = "Calle Test"
    orm.locality = "City"
    orm.municipality = "City"
    orm.province = "Province"
    orm.latitude = lat
    orm.longitude = lon
    orm.schedule = "L-D: 24H"
    orm.price_gasoline_95_e5 = price_gasoline_95_e5
    orm.price_gasoline_95_e10 = None
    orm.price_gasoline_98_e5 = None
    orm.price_diesel_a = price_diesel_a
    orm.price_diesel_premium = None
    return orm


# ── rank_stations ─────────────────────────────────────────────────────────


USER_LAT, USER_LON = 39.47, -0.376  # Valencia


def test_rank_stations_sorts_by_total_cost():
    # Station A: cheap price, far away.
    # Station B: pricier, very close.
    # With enough liters the cheap+far wins; with few liters the close one wins.
    far = _make_orm(1, 39.80, -0.376, price_gasoline_95_e5=Decimal("1.500"))
    near = _make_orm(2, 39.471, -0.377, price_gasoline_95_e5=Decimal("1.700"))

    # 1 litre: travel cost dominates → near station wins.
    ranked = rank_stations([far, near], FuelType.GASOLINE_95_E5, USER_LAT, USER_LON, 1, 0.13)
    assert ranked[0].station_id == near.id

    # 300 litres: fuel cost dominates → cheap station wins.
    ranked = rank_stations([far, near], FuelType.GASOLINE_95_E5, USER_LAT, USER_LON, 300, 0.13)
    assert ranked[0].station_id == far.id


def test_rank_stations_excludes_missing_price():
    no_diesel = _make_orm(1, 39.47, -0.376, price_diesel_a=None)
    has_diesel = _make_orm(2, 39.48, -0.376, price_diesel_a=Decimal("1.489"))

    ranked = rank_stations([no_diesel, has_diesel], FuelType.DIESEL_A, USER_LAT, USER_LON, 40, 0.13)
    assert len(ranked) == 1
    assert ranked[0].station_id == has_diesel.id


def test_rank_stations_max_distance_filter():
    far = _make_orm(1, 42.0, -0.376)  # ~280 km north
    near = _make_orm(2, 39.48, -0.376)

    ranked = rank_stations(
        [far, near], FuelType.GASOLINE_95_E5, USER_LAT, USER_LON, 40, 0.13, max_distance_km=50
    )
    assert len(ranked) == 1
    assert ranked[0].station_id == near.id


def test_rank_stations_limit():
    stations = [_make_orm(i, 39.47 + i * 0.01, -0.376) for i in range(20)]
    ranked = rank_stations(
        stations, FuelType.GASOLINE_95_E5, USER_LAT, USER_LON, 40, 0.13, limit=5
    )
    assert len(ranked) == 5


def test_rank_stations_empty_db():
    assert rank_stations([], FuelType.DIESEL_A, USER_LAT, USER_LON, 40, 0.13) == []


def test_station_cost_formula():
    """Total = fuel_cost + travel_cost exactly."""
    station = _make_orm(1, 39.48, -0.376, price_gasoline_95_e5=Decimal("1.595"))
    ranked = rank_stations(
        [station], FuelType.GASOLINE_95_E5, USER_LAT, USER_LON, 40.0, 0.13
    )
    sc = ranked[0]
    assert sc.total_cost == sc.fuel_cost + sc.travel_cost
    assert sc.fuel_cost == (Decimal("40") * Decimal("1.595")).quantize(Decimal("0.001"))


def test_zero_km_cost_travel_is_zero():
    station = _make_orm(1, 42.0, 3.0)  # far away
    ranked = rank_stations(
        [station], FuelType.GASOLINE_95_E5, USER_LAT, USER_LON, 40, km_cost=0.0
    )
    assert ranked[0].travel_cost == Decimal("0.000")
    assert ranked[0].total_cost == ranked[0].fuel_cost
