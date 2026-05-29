"""Unit tests for the optimization orchestration service."""

from __future__ import annotations

from decimal import Decimal

from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import StationCost
from app.services.optimization.optimization_profiles import OptimizationProfile
from app.services.optimization.optimization_service import optimize, summarize

_TIME = 15.0
_TRAFFIC = 0.25


def _station(
    station_id: int,
    *,
    fuel_cost: float,
    travel_cost: float,
    eta_min: float | None,
    delay_s: int | None,
    distance_km: float = 5.0,
) -> StationCost:
    return StationCost(
        station_id=station_id,
        brand="TEST",
        address="addr",
        locality="loc",
        municipality="mun",
        province="prov",
        latitude=39.1,
        longitude=-0.4,
        schedule="24H",
        fuel_type=FuelType.GASOLINA_95,
        price_per_liter=Decimal("1.50"),
        liters=40.0,
        distance_km=distance_km,
        km_cost=0.13,
        fuel_cost=Decimal(str(fuel_cost)),
        travel_cost=Decimal(str(travel_cost)),
        total_cost=Decimal(str(fuel_cost + travel_cost)),
        driving_distance_km=distance_km,
        driving_duration_min=eta_min,
        traffic_delay_seconds=delay_s,
    )


# Cheap-but-far A vs pricey-but-near B — the spec's headline scenario.
def _scenario() -> list[StationCost]:
    far_cheap = _station(1, fuel_cost=56.0, travel_cost=2.34, eta_min=32.0, delay_s=720, distance_km=18.0)
    near_pricey = _station(2, fuel_cost=62.0, travel_cost=0.39, eta_min=4.0, delay_s=0, distance_km=3.0)
    return [far_cheap, near_pricey]


def test_optimize_ranks_and_numbers() -> None:
    out = optimize(_scenario(), OptimizationProfile.CHEAPEST, time_cost_per_hour=_TIME, traffic_penalty_factor=_TRAFFIC)
    assert [o.rank for o in out] == [1, 2]
    assert out[0].result.score <= out[1].result.score


def test_cheapest_prefers_cheap_fuel_station() -> None:
    out = optimize(_scenario(), OptimizationProfile.CHEAPEST, time_cost_per_hour=_TIME, traffic_penalty_factor=_TRAFFIC)
    assert out[0].station.station_id == 1


def test_fastest_prefers_near_fast_station() -> None:
    # The smarter optimizer picks the closer station despite higher fuel price.
    out = optimize(_scenario(), OptimizationProfile.FASTEST, time_cost_per_hour=_TIME, traffic_penalty_factor=_TRAFFIC)
    assert out[0].station.station_id == 2


def test_optimize_limit() -> None:
    out = optimize(_scenario(), OptimizationProfile.BALANCED, time_cost_per_hour=_TIME, traffic_penalty_factor=_TRAFFIC, limit=1)
    assert len(out) == 1


def test_optimize_empty() -> None:
    assert optimize([], OptimizationProfile.BALANCED, time_cost_per_hour=_TIME, traffic_penalty_factor=_TRAFFIC) == []


def test_optimize_stable_on_tie() -> None:
    # Two identical stations → input order preserved (cost-ranked tie-break).
    a = _station(10, fuel_cost=50.0, travel_cost=1.0, eta_min=5.0, delay_s=0)
    b = _station(20, fuel_cost=50.0, travel_cost=1.0, eta_min=5.0, delay_s=0)
    out = optimize([a, b], OptimizationProfile.BALANCED, time_cost_per_hour=_TIME, traffic_penalty_factor=_TRAFFIC)
    assert [o.station.station_id for o in out] == [10, 20]


# ── summarize ────────────────────────────────────────────────────────────────


def test_summarize_metrics() -> None:
    s = summarize(_scenario(), profile=OptimizationProfile.BALANCED, time_cost_per_hour=_TIME, traffic_penalty_factor=_TRAFFIC)
    assert s.station_count == 2
    assert s.average_eta_minutes == 18.0  # (32 + 4) / 2
    assert s.average_traffic_delay_minutes == 6.0  # (12 + 0) / 2
    # Fuel savings vs priciest (62): (62-56 + 62-62)/2 = 3.0
    assert s.average_fuel_savings_eur == 3.0


def test_summarize_distribution_covers_four_profiles() -> None:
    s = summarize(_scenario(), profile=OptimizationProfile.BALANCED, time_cost_per_hour=_TIME, traffic_penalty_factor=_TRAFFIC)
    assert len(s.profile_winners) == 4
    assert sum(s.best_profile_distribution.values()) == 4


def test_summarize_empty_set() -> None:
    s = summarize([], profile=OptimizationProfile.BALANCED, time_cost_per_hour=_TIME, traffic_penalty_factor=_TRAFFIC)
    assert s.station_count == 0
    assert s.average_eta_minutes is None
    assert s.average_traffic_delay_minutes == 0.0
    assert s.average_fuel_savings_eur == 0.0
    assert s.profile_winners == []
