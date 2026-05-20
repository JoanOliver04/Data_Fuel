"""Haversine routing provider: great-circle distance, no duration/traffic.

Doubles as the ultimate fallback for the driving providers, so the leg builder
is exposed as ``haversine_leg`` for them to reuse with their own ``provider``
label and ``failed`` flag.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.services.cost_calculator import haversine_km
from app.services.routing.dto import RouteLeg

PROVIDER_NAME = "haversine"


def haversine_leg(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    provider: str,
    failed: bool = False,
) -> RouteLeg:
    """Build a haversine ``RouteLeg`` (no duration/traffic) for one destination.

    ``provider``/``failed`` are caller-supplied so a driving provider can return
    this as its own degraded leg (e.g. ``provider="ors", failed=True``).
    """
    distance = haversine_km(origin[0], origin[1], destination[0], destination[1])
    return RouteLeg(
        distance_km=round(distance, 3),
        duration_seconds=None,
        traffic_delay_seconds=None,
        provider=provider,
        failed=failed,
    )


class HaversineProvider:
    """Straight-line distance for every destination. Never fails, no I/O."""

    async def matrix(
        self,
        origin: tuple[float, float],
        destinations: Sequence[tuple[float, float]],
    ) -> list[RouteLeg]:
        return [
            haversine_leg(origin, dest, provider=PROVIDER_NAME, failed=False)
            for dest in destinations
        ]
