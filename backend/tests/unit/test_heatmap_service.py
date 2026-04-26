"""Unit tests for the heatmap price-normalisation logic."""

from decimal import Decimal

import pytest

from app.domain.services.heatmap import HeatmapInput, normalize_prices


def _row(sid: int, price: str, lat: float = 0.0, lon: float = 0.0) -> HeatmapInput:
    return HeatmapInput(
        station_id=sid,
        latitude=lat,
        longitude=lon,
        price=Decimal(price),
        brand="TEST",
        name="Locality",
    )


def test_empty_input_returns_empty_list():
    assert normalize_prices([]) == []


def test_single_station_normalized_to_zero():
    """No spread to communicate → cheap colour by convention."""
    [point] = normalize_prices([_row(1, "1.500")])
    assert point.price_normalized == 0.0
    assert point.price == Decimal("1.500")


def test_all_stations_same_price_all_zero():
    """When max == min the normalisation formula would divide by zero;
    every point must collapse to 0.0 (no false gradient)."""
    points = normalize_prices(
        [_row(1, "1.500"), _row(2, "1.500"), _row(3, "1.500")]
    )
    assert [p.price_normalized for p in points] == [0.0, 0.0, 0.0]


def test_two_stations_endpoints_at_zero_and_one():
    cheap, expensive = normalize_prices([_row(1, "1.400"), _row(2, "1.700")])
    assert cheap.price_normalized == 0.0
    assert expensive.price_normalized == 1.0


def test_three_stations_midpoint_lands_at_half():
    points = normalize_prices(
        [_row(1, "1.400"), _row(2, "1.550"), _row(3, "1.700")]
    )
    norms = [p.price_normalized for p in points]
    assert norms[0] == 0.0
    assert norms[1] == pytest.approx(0.5, abs=1e-9)
    assert norms[2] == 1.0


def test_normalization_preserves_metadata():
    """Lat/lon/brand/name must round-trip unchanged through the transform."""
    [p] = normalize_prices(
        [
            HeatmapInput(
                station_id=42,
                latitude=39.47,
                longitude=-0.376,
                price=Decimal("1.600"),
                brand="REPSOL",
                name="Valencia",
            )
        ]
    )
    assert p.station_id == 42
    assert p.latitude == 39.47
    assert p.longitude == -0.376
    assert p.brand == "REPSOL"
    assert p.name == "Valencia"
    assert p.price == Decimal("1.600")


def test_output_normalization_in_unit_interval():
    """Property: every produced normalisation must lie in [0, 1]."""
    points = normalize_prices(
        [_row(i, f"1.{400 + i:03d}") for i in range(10)]
    )
    assert all(0.0 <= p.price_normalized <= 1.0 for p in points)
