"""Unit tests for deterministic analytics insights."""

from app.analytics.insights import (
    brand_insight,
    comarca_insight,
    overview_insight,
    trend_insight,
)
from app.analytics.schemas import BrandStat, ComarcaStat, TrendPoint


def _pt(bucket: str, avg: float) -> TrendPoint:
    return TrendPoint(bucket=bucket, avg_price=avg, min_price=avg, max_price=avg, sample_count=1)


def test_overview_insight_picks_cheapest_fuel() -> None:
    out = overview_insight({"gasoil": 1.45, "gasolina_95": 1.59}, "La Ribera Alta", "La Safor")
    assert "Gasóleo A" in out.text
    assert out.source == "deterministic"


def test_trend_insight_detects_drop_and_rise() -> None:
    down = trend_insight([_pt("d1", 1.60), _pt("d2", 1.55)], "gasolina_95", "7d")
    assert "bajado" in down.text
    up = trend_insight([_pt("d1", 1.50), _pt("d2", 1.56)], "gasolina_95", "7d")
    assert "subido" in up.text
    flat = trend_insight([_pt("d1", 1.500), _pt("d2", 1.5005)], "gasolina_95", "7d")
    assert "estable" in flat.text


def test_trend_insight_handles_insufficient_data() -> None:
    assert "suficientes" in trend_insight([], "gasoil", "7d").text


def test_comarca_insight_names_cheapest() -> None:
    items = [
        ComarcaStat(comarca="A", avg_price=1.60, min_price=1.5, max_price=1.7,
                    station_count=3, sample_count=10),
        ComarcaStat(comarca="B", avg_price=1.45, min_price=1.4, max_price=1.5,
                    station_count=2, sample_count=8, delta_pct=-1.2, direction="DOWN"),
    ]
    out = comarca_insight(items, "gasoil")
    assert "B" in out.text  # cheapest
    assert "bajada" in out.text  # biggest mover


def test_brand_insight_uses_top_ranked() -> None:
    items = [
        BrandStat(brand="CEPSA", rank=1, avg_price=1.48, station_count=5, sample_count=20),
        BrandStat(brand="REPSOL", rank=2, avg_price=1.55, station_count=8, sample_count=30),
    ]
    assert "CEPSA" in brand_insight(items, "gasolina_95").text
