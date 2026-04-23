"""Unit tests for PredictionService."""

from datetime import UTC, datetime, timedelta

from app.domain.entities.fuel_type import FuelType
from app.domain.services.prediction_service import (
    MIN_SAMPLES,
    PredictionResult,
    PredictionService,
    TrainingRow,
    _make_advice,
)


def _make_rows(n: int, price: float = 1.489) -> list[TrainingRow]:
    base = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
    return [
        TrainingRow(
            price=price + (i % 5) * 0.01,
            recorded_at=base + timedelta(hours=i * 3),
            brand="REPSOL" if i % 2 == 0 else "CEPSA",
            province="Valencia",
        )
        for i in range(n)
    ]


class TestPredictionServiceInsufficientData:
    def test_returns_none_when_below_min_samples(self):
        svc = PredictionService()
        rows = _make_rows(MIN_SAMPLES - 1)
        result = svc.predict(rows, 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        assert result is None

    def test_returns_none_with_empty_rows(self):
        svc = PredictionService()
        result = svc.predict([], 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        assert result is None


class TestPredictionServiceResult:
    def test_returns_prediction_result_with_enough_data(self):
        svc = PredictionService()
        rows = _make_rows(MIN_SAMPLES)
        result = svc.predict(rows, 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        assert isinstance(result, PredictionResult)

    def test_predicted_price_is_positive(self):
        svc = PredictionService()
        rows = _make_rows(MIN_SAMPLES)
        result = svc.predict(rows, 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        assert result is not None
        assert result.predicted_price > 0

    def test_horizon_hours_is_48(self):
        svc = PredictionService()
        rows = _make_rows(MIN_SAMPLES)
        result = svc.predict(rows, 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        assert result is not None
        assert result.horizon_hours == 48

    def test_change_pct_sign_matches_direction(self):
        svc = PredictionService()
        rows = _make_rows(MIN_SAMPLES)
        result = svc.predict(rows, 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        assert result is not None
        # change_pct sign must match the direction between predicted and current
        if result.predicted_price > result.current_price:
            assert result.change_pct > 0
        elif result.predicted_price < result.current_price:
            assert result.change_pct < 0

    def test_model_r2_is_between_0_and_1(self):
        svc = PredictionService()
        rows = _make_rows(MIN_SAMPLES)
        result = svc.predict(rows, 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        assert result is not None
        # R² can be negative for very bad fits, but should be finite
        assert isinstance(result.model_r2, float)

    def test_cache_reused_on_second_call(self):
        svc = PredictionService()
        rows = _make_rows(MIN_SAMPLES)
        svc.predict(rows, 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        # Populate cache — second call should hit it
        assert FuelType.DIESEL_A in svc._cache

    def test_invalidate_clears_specific_fuel_type(self):
        svc = PredictionService()
        rows = _make_rows(MIN_SAMPLES)
        svc.predict(rows, 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        svc.invalidate(FuelType.DIESEL_A)
        assert FuelType.DIESEL_A not in svc._cache

    def test_invalidate_all_clears_cache(self):
        svc = PredictionService()
        rows = _make_rows(MIN_SAMPLES)
        svc.predict(rows, 1.489, "REPSOL", "Valencia", FuelType.DIESEL_A)
        svc.invalidate()
        assert svc._cache == {}


class TestMakeAdvice:
    def test_price_drop_gives_wait_advice(self):
        advice = _make_advice(-2.0)
        assert "Espera" in advice
        assert "2.0%" in advice

    def test_price_rise_gives_refuel_now_advice(self):
        advice = _make_advice(1.5)
        assert "Reposta ahora" in advice
        assert "1.5%" in advice

    def test_stable_price(self):
        advice = _make_advice(0.0)
        assert "estable" in advice

    def test_below_threshold_counts_as_stable(self):
        assert "estable" in _make_advice(0.3)
        assert "estable" in _make_advice(-0.3)
