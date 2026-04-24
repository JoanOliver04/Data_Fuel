"""Unit tests for SmartRefuelService decision logic."""

from decimal import Decimal

import pytest

from app.domain.services.cost_calculator import StationCost
from app.domain.services.prediction_service import PredictionResult
from app.domain.entities.fuel_type import FuelType
from app.domain.services.smart_refuel_service import (
    SAVINGS_THRESHOLD_EUR,
    SmartRefuelService,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_station(
    price: float = 1.595,
    distance_km: float = 2.0,
    liters: float = 50.0,
    km_cost: float = 0.13,
) -> StationCost:
    price_d = Decimal(str(price))
    liters_d = Decimal(str(liters))
    km_cost_d = Decimal(str(km_cost))
    dist_d = Decimal(str(distance_km))
    fuel_cost = (liters_d * price_d).quantize(Decimal("0.001"))
    travel_cost = (dist_d * km_cost_d).quantize(Decimal("0.001"))
    return StationCost(
        station_id=1,
        brand="REPSOL",
        address="Calle Test 1",
        locality="Valencia",
        municipality="Valencia",
        province="Valencia",
        latitude=39.47,
        longitude=-0.376,
        schedule="L-D: 24H",
        fuel_type=FuelType.GASOLINA_95,
        price_per_liter=price_d,
        liters=liters,
        distance_km=distance_km,
        km_cost=km_cost,
        fuel_cost=fuel_cost,
        travel_cost=travel_cost,
        total_cost=fuel_cost + travel_cost,
    )


def _make_prediction(
    current_price: float = 1.595,
    predicted_price: float = 1.595,
    model_r2: float = 0.8,
) -> PredictionResult:
    change_pct = round((predicted_price - current_price) / current_price * 100, 2)
    return PredictionResult(
        current_price=current_price,
        predicted_price=predicted_price,
        change_pct=change_pct,
        advice="",
        horizon_hours=48,
        model_r2=model_r2,
    )


SVC = SmartRefuelService()

# ── No prediction ─────────────────────────────────────────────────────────────


def test_no_prediction_returns_refuel_now():
    station = _make_station()
    advice = SVC.advise(station, None, liters=50.0, km_cost=0.13)
    assert advice.action == "REFUEL_NOW"
    assert advice.savings_eur == 0.0
    assert advice.confidence == pytest.approx(0.4)


# ── Price rising → REFUEL_NOW ─────────────────────────────────────────────────


def test_refuel_now_when_price_rising():
    station = _make_station(price=1.50, liters=50.0)
    prediction = _make_prediction(current_price=1.50, predicted_price=1.56)
    advice = SVC.advise(station, prediction, liters=50.0, km_cost=0.13)
    assert advice.action == "REFUEL_NOW"
    assert advice.savings_eur < 0


# ── Price stable → REFUEL_NOW ─────────────────────────────────────────────────


def test_refuel_now_when_price_stable():
    station = _make_station(price=1.50, liters=50.0)
    prediction = _make_prediction(current_price=1.50, predicted_price=1.501)
    advice = SVC.advise(station, prediction, liters=50.0, km_cost=0.13)
    assert advice.action == "REFUEL_NOW"
    assert abs(advice.savings_eur) < SAVINGS_THRESHOLD_EUR


# ── Price drops enough → WAIT ─────────────────────────────────────────────────


def test_wait_when_savings_above_threshold():
    station = _make_station(price=1.60, liters=50.0)
    # Drop of 0.10 €/L × 50 L = 5€ savings → above 2€ threshold
    prediction = _make_prediction(current_price=1.60, predicted_price=1.50)
    advice = SVC.advise(station, prediction, liters=50.0, km_cost=0.13)
    assert advice.action == "WAIT"
    assert advice.savings_eur == pytest.approx(5.0, abs=0.01)


# ── Savings just below threshold → REFUEL_NOW ────────────────────────────────


def test_refuel_now_when_savings_just_below_threshold():
    station = _make_station(price=1.60, liters=50.0)
    # Drop of 0.03 €/L × 50 L = 1.5€ → below 2€ threshold
    prediction = _make_prediction(current_price=1.60, predicted_price=1.57)
    advice = SVC.advise(station, prediction, liters=50.0, km_cost=0.13)
    assert advice.action == "REFUEL_NOW"
    assert 0 < advice.savings_eur < SAVINGS_THRESHOLD_EUR


# ── Confidence clipped to [0.1, 0.95] ────────────────────────────────────────


def test_confidence_clipped_high():
    station = _make_station()
    prediction = _make_prediction(model_r2=1.0)
    advice = SVC.advise(station, prediction, liters=50.0, km_cost=0.13)
    assert advice.confidence <= 0.95


def test_confidence_clipped_low():
    station = _make_station()
    prediction = _make_prediction(model_r2=-5.0)
    advice = SVC.advise(station, prediction, liters=50.0, km_cost=0.13)
    assert advice.confidence >= 0.1


# ── Output fields present ─────────────────────────────────────────────────────


def test_output_fields_complete():
    station = _make_station(price=1.55, liters=40.0)
    prediction = _make_prediction(current_price=1.55, predicted_price=1.40, model_r2=0.75)
    advice = SVC.advise(station, prediction, liters=40.0, km_cost=0.13)

    assert advice.action in {"WAIT", "REFUEL_NOW"}
    assert isinstance(advice.reasoning, str) and len(advice.reasoning) > 0
    assert 0.0 <= advice.confidence <= 1.0
    assert advice.recommended_station is station
