"""Unit tests for vehicle profile domain service (dynamic K calculation)."""

import pytest

from app.domain.services.vehicle_profile_service import compute_km_cost


# ── Basic formula ──────────────────────────────────────────────────────────


def test_typical_consumption():
    # 6.5 L/100km × 1.52 €/L = 0.0988 €/km
    result = compute_km_cost(6.5, 1.52)
    assert result == pytest.approx(0.0988, rel=1e-5)


def test_higher_consumption():
    # 12 L/100km × 1.85 €/L = 0.222 €/km
    result = compute_km_cost(12.0, 1.85)
    assert result == pytest.approx(0.222, rel=1e-5)


def test_low_consumption():
    # 4.0 L/100km × 1.50 €/L = 0.06 €/km
    result = compute_km_cost(4.0, 1.50)
    assert result == pytest.approx(0.06, rel=1e-5)


# ── Edge cases ─────────────────────────────────────────────────────────────


def test_electric_vehicle_zero_consumption():
    # Electric vehicle: consumption = 0 → K = 0 regardless of fuel price.
    assert compute_km_cost(0.0, 1.80) == 0.0


def test_electric_vehicle_zero_price():
    assert compute_km_cost(0.0, 0.0) == 0.0


def test_very_high_consumption():
    # 15 L/100km (max slider) × 2.0 €/L = 0.30 €/km
    result = compute_km_cost(15.0, 2.0)
    assert result == pytest.approx(0.30, rel=1e-5)


def test_very_high_fuel_price():
    # 7 L/100km × 5.0 €/L (extreme) = 0.35 €/km
    result = compute_km_cost(7.0, 5.0)
    assert result == pytest.approx(0.35, rel=1e-5)


def test_formula_proportional_to_consumption():
    k1 = compute_km_cost(5.0, 1.50)
    k2 = compute_km_cost(10.0, 1.50)
    assert k2 == pytest.approx(k1 * 2, rel=1e-9)


def test_formula_proportional_to_price():
    k1 = compute_km_cost(7.0, 1.00)
    k2 = compute_km_cost(7.0, 2.00)
    assert k2 == pytest.approx(k1 * 2, rel=1e-9)


def test_result_is_float():
    assert isinstance(compute_km_cost(6.0, 1.60), float)
