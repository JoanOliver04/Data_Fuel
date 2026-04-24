"""Tests for domain entities (FuelType, Coordinates, Station, Price)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from app.domain.entities import Coordinates, FuelType, Price, Station


def test_fuel_type_values() -> None:
    assert FuelType.GASOLINA_95.value == "gasolina_95"
    assert FuelType.GASOIL.value == "gasoil"
    assert FuelType("gasoil_premium") is FuelType.GASOIL_PREMIUM


def test_fuel_type_is_str_enum() -> None:
    """StrEnum members should be usable as plain strings."""
    assert f"prefix_{FuelType.GASOLINA_98}" == "prefix_gasolina_98"


def test_coordinates_are_frozen() -> None:
    coords = Coordinates(latitude=40.4, longitude=-3.7)
    with pytest.raises(FrozenInstanceError):
        coords.latitude = 0.0  # type: ignore[misc]


def test_station_defaults_to_empty_prices() -> None:
    station = Station(
        id=1,
        brand="Repsol",
        address="Calle Mayor 1",
        locality="Madrid",
        municipality="Madrid",
        province="Madrid",
        postal_code="28001",
        coordinates=Coordinates(40.4, -3.7),
        schedule="L-D: 24H",
    )
    assert station.prices == {}


def test_station_accepts_explicit_prices() -> None:
    prices: dict[FuelType, float | None] = {
        FuelType.GASOLINA_95: 1.595,
        FuelType.GASOIL: 1.499,
        FuelType.GASOLINA_98: None,
    }
    station = Station(
        id=42,
        brand="Cepsa",
        address="A",
        locality="B",
        municipality="C",
        province="D",
        postal_code="00000",
        coordinates=Coordinates(0.0, 0.0),
        schedule="",
        prices=prices,
    )
    assert station.prices[FuelType.GASOLINA_95] == 1.595
    assert station.prices[FuelType.GASOLINA_98] is None


def test_price_is_immutable() -> None:
    price = Price(
        station_id=1,
        fuel_type=FuelType.GASOIL,
        value=1.499,
        recorded_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
    )
    with pytest.raises(FrozenInstanceError):
        price.value = 0.0  # type: ignore[misc]
