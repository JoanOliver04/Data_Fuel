"""Strict per-type validation of alert creation payloads."""

import pytest
from pydantic import ValidationError

from app.alerts.schemas import AlertCreate


def _make(alert_type: str, **extra: object) -> AlertCreate:
    base: dict[str, object] = {
        "user_identifier": "u1",
        "alert_type": alert_type,
        "fuel_type": "gasolina_95",
    }
    base.update(extra)
    return AlertCreate(**base)  # type: ignore[arg-type]


def test_price_below_requires_threshold_price() -> None:
    with pytest.raises(ValidationError):
        _make("PRICE_BELOW_THRESHOLD")
    assert _make("PRICE_BELOW_THRESHOLD", threshold_price="1.45").threshold_price is not None


def test_cheapest_brand_requires_brand_and_geo() -> None:
    with pytest.raises(ValidationError):
        _make("CHEAPEST_BRAND", brand="REPSOL")  # missing lat/lon
    ok = _make("CHEAPEST_BRAND", brand="REPSOL", latitude=39.1, longitude=-0.4)
    assert ok.brand == "REPSOL"


def test_favorite_requires_station_id() -> None:
    with pytest.raises(ValidationError):
        _make("FAVORITE_STATION_CHANGE")
    assert _make("FAVORITE_STATION_CHANGE", station_id=7).station_id == 7


def test_wait_signal_requires_pct_and_geo() -> None:
    with pytest.raises(ValidationError):
        _make("WAIT_VS_REFUEL_SIGNAL", threshold_pct=3.0)  # missing geo
    assert _make(
        "WAIT_VS_REFUEL_SIGNAL", threshold_pct=3.0, latitude=39.1, longitude=-0.4
    ).threshold_pct == 3.0


def test_invalid_fuel_type_rejected() -> None:
    with pytest.raises(ValidationError):
        _make("WEEKLY_SUMMARY", fuel_type="kerosene")


def test_weekly_summary_needs_no_extra_fields() -> None:
    assert _make("WEEKLY_SUMMARY").alert_type == "WEEKLY_SUMMARY"
