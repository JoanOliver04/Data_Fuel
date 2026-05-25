"""Deterministic, executive-grade insight strings derived from aggregates.

These are computed purely from the numbers — no LLM, no hallucination risk.
The optional LLM-enrichment seam lives in ``app.analytics.enrich`` and wraps
these; if it is unavailable the deterministic text is returned unchanged.
"""

from __future__ import annotations

from app.analytics.schemas import BrandStat, ComarcaStat, Insight, TimeRange, TrendPoint

_FUEL_LABEL = {
    "gasolina_95": "Gasolina 95",
    "gasolina_95_e10": "Gasolina 95 E10",
    "gasolina_98": "Gasolina 98",
    "gasoil": "Gasóleo A",
    "gasoil_premium": "Gasóleo Premium",
}

_RANGE_LABEL: dict[TimeRange, str] = {
    "24h": "en las últimas 24h",
    "7d": "esta semana",
    "30d": "este mes",
    "90d": "en 90 días",
    "1y": "en el último año",
}


def fuel_label(fuel: str) -> str:
    return _FUEL_LABEL.get(fuel, fuel)


def overview_insight(
    fuel_averages: dict[str, float],
    cheapest_comarca: str | None,
    most_expensive_comarca: str | None,
) -> Insight:
    if not fuel_averages:
        return Insight(text="Aún no hay datos de precios suficientes para el resumen.")
    cheapest_fuel = min(fuel_averages, key=lambda k: fuel_averages[k])
    parts = [
        f"{fuel_label(cheapest_fuel)} es el combustible más barato de media "
        f"({fuel_averages[cheapest_fuel]:.3f} €/L)."
    ]
    if cheapest_comarca and most_expensive_comarca and cheapest_comarca != most_expensive_comarca:
        parts.append(
            f"{cheapest_comarca} concentra los precios más bajos y "
            f"{most_expensive_comarca} los más altos."
        )
    return Insight(text=" ".join(parts))


def trend_insight(points: list[TrendPoint], fuel: str, rng: TimeRange) -> Insight:
    if len(points) < 2:
        return Insight(text=f"Sin datos suficientes para la tendencia de {fuel_label(fuel)}.")
    first, last = points[0].avg_price, points[-1].avg_price
    if first <= 0:
        return Insight(text=f"Tendencia de {fuel_label(fuel)} no disponible.")
    delta = (last - first) / first * 100
    if delta <= -0.3:
        word = f"ha bajado {abs(delta):.1f}%"
    elif delta >= 0.3:
        word = f"ha subido {delta:.1f}%"
    else:
        word = "se ha mantenido estable"
    return Insight(text=f"{fuel_label(fuel)} {word} {_RANGE_LABEL[rng]}.")


def comarca_insight(items: list[ComarcaStat], fuel: str) -> Insight:
    if not items:
        return Insight(text=f"Sin datos por comarca para {fuel_label(fuel)}.")
    cheapest = min(items, key=lambda c: c.avg_price)
    parts = [f"{cheapest.comarca} es la comarca más barata ({cheapest.avg_price:.3f} €/L)."]
    movers = [c for c in items if c.delta_pct is not None]
    if movers:
        mover = min(movers, key=lambda c: c.delta_pct or 0.0)
        if mover.delta_pct is not None and mover.delta_pct <= -0.3:
            parts.append(f"{mover.comarca} registra la mayor bajada ({mover.delta_pct:.1f}%).")
    return Insight(text=" ".join(parts))


def brand_insight(items: list[BrandStat], fuel: str) -> Insight:
    if not items:
        return Insight(text=f"Sin datos por marca para {fuel_label(fuel)}.")
    cheapest = items[0]  # items arrive ranked by avg price ascending
    return Insight(
        text=(
            f"{cheapest.brand} ofrece el precio medio más competitivo en "
            f"{fuel_label(fuel)} ({cheapest.avg_price:.3f} €/L)."
        )
    )
