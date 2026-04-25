"""Unit tests for vehicle profile domain logic.

Covers:
- The dynamic consumption-mode selector (boundary values).
- K calculation for each consumption mode at a real fuel price.
- Per-mode K resolution via ``km_cost_for_distance``.
"""

import pytest

from app.domain.entities.vehicle_profile import (
    HIGHWAY_MIN_KM,
    URBAN_MAX_KM,
    ConsumptionMode,
    select_consumption_mode,
)
from app.domain.services.vehicle_profile_service import (
    ConsumptionProfile,
    compute_km_cost,
    km_cost_for_distance,
)

# ── compute_km_cost: basic formula and edge cases ──────────────────────────


def test_typical_consumption():
    # 6.5 L/100km × 1.52 €/L = 0.0988 €/km
    assert compute_km_cost(6.5, 1.52) == pytest.approx(0.0988, rel=1e-5)


def test_higher_consumption():
    # 12 L/100km × 1.85 €/L = 0.222 €/km
    assert compute_km_cost(12.0, 1.85) == pytest.approx(0.222, rel=1e-5)


def test_low_consumption():
    # 4.0 L/100km × 1.50 €/L = 0.06 €/km
    assert compute_km_cost(4.0, 1.50) == pytest.approx(0.06, rel=1e-5)


def test_electric_vehicle_zero_consumption():
    assert compute_km_cost(0.0, 1.80) == 0.0


def test_electric_vehicle_zero_price():
    assert compute_km_cost(0.0, 0.0) == 0.0


def test_very_high_consumption():
    assert compute_km_cost(15.0, 2.0) == pytest.approx(0.30, rel=1e-5)


def test_very_high_fuel_price():
    assert compute_km_cost(7.0, 5.0) == pytest.approx(0.35, rel=1e-5)


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


# ── select_consumption_mode: boundary values 0/4.9/5/19.9/20/50 ────────────


@pytest.mark.parametrize(
    ("distance_km", "expected_mode"),
    [
        (0.0, ConsumptionMode.URBAN),
        (4.9, ConsumptionMode.URBAN),
        (URBAN_MAX_KM, ConsumptionMode.MIXED),  # exactly 5.0 → mixed (>= boundary)
        (5.0, ConsumptionMode.MIXED),
        (19.9, ConsumptionMode.MIXED),
        (HIGHWAY_MIN_KM, ConsumptionMode.HIGHWAY),  # exactly 20.0 → highway
        (20.0, ConsumptionMode.HIGHWAY),
        (50.0, ConsumptionMode.HIGHWAY),
    ],
)
def test_select_consumption_mode_boundaries(distance_km: float, expected_mode: ConsumptionMode):
    assert select_consumption_mode(distance_km) is expected_mode


# ── km_cost_for_distance: K per mode at a real fuel price ──────────────────


@pytest.fixture
def profile() -> ConsumptionProfile:
    return ConsumptionProfile(urban=8.0, mixed=6.5, highway=5.5)


def test_km_cost_urban_band(profile: ConsumptionProfile):
    # < 5 km → urban consumption (8.0) at 1.60 €/L = 0.128 €/km
    k, mode = km_cost_for_distance(profile, distance_km=2.0, fuel_price_eur_per_l=1.60)
    assert mode is ConsumptionMode.URBAN
    assert k == pytest.approx(0.128, rel=1e-5)


def test_km_cost_mixed_band(profile: ConsumptionProfile):
    # 5–20 km → mixed (6.5) at 1.60 €/L = 0.104 €/km
    k, mode = km_cost_for_distance(profile, distance_km=10.0, fuel_price_eur_per_l=1.60)
    assert mode is ConsumptionMode.MIXED
    assert k == pytest.approx(0.104, rel=1e-5)


def test_km_cost_highway_band(profile: ConsumptionProfile):
    # ≥ 20 km → highway (5.5) at 1.60 €/L = 0.088 €/km
    k, mode = km_cost_for_distance(profile, distance_km=35.0, fuel_price_eur_per_l=1.60)
    assert mode is ConsumptionMode.HIGHWAY
    assert k == pytest.approx(0.088, rel=1e-5)


def test_km_cost_at_urban_boundary(profile: ConsumptionProfile):
    # exactly 5.0 km → mixed
    _, mode = km_cost_for_distance(profile, distance_km=5.0, fuel_price_eur_per_l=1.60)
    assert mode is ConsumptionMode.MIXED


def test_km_cost_at_highway_boundary(profile: ConsumptionProfile):
    # exactly 20.0 km → highway
    _, mode = km_cost_for_distance(profile, distance_km=20.0, fuel_price_eur_per_l=1.60)
    assert mode is ConsumptionMode.HIGHWAY


def test_consumption_profile_lookup(profile: ConsumptionProfile):
    assert profile.consumption_for(ConsumptionMode.URBAN) == 8.0
    assert profile.consumption_for(ConsumptionMode.MIXED) == 6.5
    assert profile.consumption_for(ConsumptionMode.HIGHWAY) == 5.5
