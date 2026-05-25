"""Deterministic tests for the eight alert evaluators (no DB, stubbed context)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.alerts.evaluators import get_evaluator
from app.alerts.models.alert import AlertORM
from app.domain.entities.fuel_type import FuelType
from app.domain.services.cost_calculator import StationCost
from app.domain.services.prediction_service import PredictionResult
from app.infrastructure.database.models.station import StationORM


def _sc(price: float, *, brand: str = "REPSOL", station_id: int = 1, total: float = 80.0,
        travel: float = 1.0) -> StationCost:
    p = Decimal(str(price))
    return StationCost(
        station_id=station_id, brand=brand, address="x", locality="Alzira",
        municipality="Alzira", province="Valencia", latitude=39.1, longitude=-0.4,
        schedule="", fuel_type=FuelType.GASOLINA_95, price_per_liter=p, liters=50.0,
        distance_km=2.0, km_cost=0.13, fuel_cost=Decimal(str(round(price * 50, 2))),
        travel_cost=Decimal(str(travel)), total_cost=Decimal(str(total)),
    )


def _pred(change_pct: float) -> PredictionResult:
    return PredictionResult(
        current_price=1.6, predicted_price=round(1.6 * (1 + change_pct / 100), 3),
        change_pct=change_pct, advice="x", horizon_hours=48, model_r2=0.8,
    )


def _alert(alert_type: str, **kw: Any) -> AlertORM:
    base: dict[str, Any] = {
        "id": 1, "user_identifier": "u", "alert_type": alert_type,
        "fuel_type": "gasolina_95", "radius_km": 10.0, "liters": 50.0, "cooldown_minutes": 0,
        "latitude": 39.1, "longitude": -0.4,
    }
    base.update(kw)
    return AlertORM(**base)


class StubContext:
    """Canned data source matching the AlertContext surface evaluators use."""

    def __init__(self, *, ranked: list[StationCost] | None = None,
                 station: StationORM | None = None, price_now: float | None = None,
                 days_ago: float | None = None,
                 cheapest: tuple[float, StationORM] | None = None,
                 pred: PredictionResult | None = None) -> None:
        self._ranked = ranked or []
        self._station = station
        self._price_now = price_now
        self._days_ago = days_ago
        self._cheapest = cheapest
        self._pred = pred

    async def ranked(self, *_a: Any, **_k: Any) -> list[StationCost]:
        return self._ranked

    async def station(self, *_a: Any, **_k: Any) -> StationORM | None:
        return self._station

    def station_price_now(self, *_a: Any, **_k: Any) -> float | None:
        return self._price_now

    async def station_price_days_ago(self, *_a: Any, **_k: Any) -> float | None:
        return self._days_ago

    async def cheapest_anywhere(self, *_a: Any, **_k: Any) -> tuple[float, StationORM] | None:
        return self._cheapest

    async def predict(self, *_a: Any, **_k: Any) -> PredictionResult | None:
        return self._pred


async def _eval(alert: AlertORM, ctx: StubContext) -> Any:
    evaluator = get_evaluator(alert.alert_type)
    assert evaluator is not None
    return await evaluator.evaluate(alert, ctx)  # type: ignore[arg-type]


async def test_price_below_threshold() -> None:
    alert = _alert("PRICE_BELOW_THRESHOLD", threshold_price=Decimal("1.50"))
    assert await _eval(alert, StubContext(ranked=[_sc(1.43)])) is not None
    assert await _eval(alert, StubContext(ranked=[_sc(1.60)])) is None


async def test_cheapest_brand() -> None:
    alert = _alert("CHEAPEST_BRAND", brand="REPSOL")
    hit = await _eval(alert, StubContext(ranked=[_sc(1.5, brand="REPSOL")]))
    assert hit is not None and "REPSOL" in hit.title
    assert await _eval(alert, StubContext(ranked=[_sc(1.5, brand="CEPSA")])) is None


async def test_prediction_trend() -> None:
    alert = _alert("PREDICTION_TREND")
    up = await _eval(alert, StubContext(pred=_pred(1.0)))
    assert up is not None and "subir" in up.title
    assert await _eval(alert, StubContext(pred=_pred(0.1))) is None  # below default threshold


async def test_wait_vs_refuel() -> None:
    alert = _alert("WAIT_VS_REFUEL_SIGNAL", threshold_pct=2.0)
    assert await _eval(alert, StubContext(pred=_pred(-3.0))) is not None
    assert await _eval(alert, StubContext(pred=_pred(1.0))) is None  # rise → don't wait


async def test_favorite_station_change() -> None:
    station = StationORM(id=2, brand="CEPSA", locality="Algemesí")
    alert = _alert("FAVORITE_STATION_CHANGE", station_id=2)
    drop = await _eval(alert, StubContext(station=station, price_now=1.50, days_ago=1.54))
    assert drop is not None and "bajado" in drop.title
    assert await _eval(alert, StubContext(station=station, price_now=1.50, days_ago=1.50)) is None


async def test_price_change() -> None:
    alert = _alert("PRICE_CHANGE", threshold_pct=2.0)
    moved = await _eval(alert, StubContext(ranked=[_sc(1.60)], days_ago=1.50))
    assert moved is not None and "subido" in moved.title
    assert await _eval(alert, StubContext(ranked=[_sc(1.60)], days_ago=1.59)) is None


async def test_total_cost_drop() -> None:
    alert = _alert("TOTAL_COST_DROP", threshold_pct=2.0)
    dropped = await _eval(alert, StubContext(ranked=[_sc(1.58, total=80.0, travel=1.0)], days_ago=1.70))
    assert dropped is not None and "bajado" in dropped.message
    assert await _eval(alert, StubContext(ranked=[_sc(1.58, total=80.0, travel=1.0)], days_ago=1.58)) is None


async def test_weekly_summary_always_reports() -> None:
    alert = _alert("WEEKLY_SUMMARY")
    out = await _eval(alert, StubContext(ranked=[_sc(1.50)], days_ago=1.55))
    assert out is not None and out.dedup_key.startswith("week:")
