"""Pure price-normalisation logic for the heatmap layer.

Decoupled from SQLAlchemy and FastAPI so the math can be unit-tested with
plain dataclass inputs and so the API endpoint stays a thin orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class HeatmapInput:
    """Minimal per-station data needed to build a heatmap point."""

    station_id: int
    latitude: float
    longitude: float
    price: Decimal
    brand: str
    name: str


@dataclass(frozen=True, slots=True)
class HeatmapPoint:
    """A station's heatmap entry with min-max-normalised price ∈ [0, 1]."""

    station_id: int
    latitude: float
    longitude: float
    price: Decimal
    price_normalized: float
    brand: str
    name: str


def normalize_prices(rows: list[HeatmapInput]) -> list[HeatmapPoint]:
    """Min-max normalise prices within ``rows`` so 0.0 = cheapest, 1.0 = most expensive.

    Edge cases:
    - empty input → empty output
    - one row, or all rows priced equal → every point gets ``price_normalized = 0.0``
      (no spread to communicate; rendering as the "cheap" colour is intentional).
    """
    if not rows:
        return []

    prices = [float(r.price) for r in rows]
    p_min = min(prices)
    p_max = max(prices)
    span = p_max - p_min

    if span <= 0.0:
        return [
            HeatmapPoint(
                station_id=r.station_id,
                latitude=r.latitude,
                longitude=r.longitude,
                price=r.price,
                price_normalized=0.0,
                brand=r.brand,
                name=r.name,
            )
            for r in rows
        ]

    return [
        HeatmapPoint(
            station_id=r.station_id,
            latitude=r.latitude,
            longitude=r.longitude,
            price=r.price,
            price_normalized=(float(r.price) - p_min) / span,
            brand=r.brand,
            name=r.name,
        )
        for r in rows
    ]
