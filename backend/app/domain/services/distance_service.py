"""Distance service: straight-line (haversine) or driving (OpenRouteService).

Decouples the cost calculator from the distance source. When DRIVING mode
fails at runtime, falls back to EUCLIDEAN silently so the endpoint keeps
working while the outage is logged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

from app.domain.services.cost_calculator import haversine_km
from app.infrastructure.external.ors import ORSClient, ORSClientError

logger = logging.getLogger(__name__)


class DistanceMode(StrEnum):
    EUCLIDEAN = "EUCLIDEAN"
    DRIVING = "DRIVING"


@dataclass(frozen=True, slots=True)
class DistanceResult:
    """Distance (and optional driving time) between user and one station."""

    distance_km: float
    driving_distance_km: float | None
    driving_duration_min: float | None


class DistanceService:
    """Compute distances from a user origin to a list of station coordinates."""

    def __init__(
        self,
        mode: DistanceMode,
        ors_client: ORSClient | None = None,
    ) -> None:
        self._mode = mode
        self._ors_client = ors_client

    async def compute(
        self,
        origin: tuple[float, float],
        destinations: list[tuple[float, float]],
    ) -> list[DistanceResult]:
        if self._mode is DistanceMode.DRIVING:
            driving = await self._try_driving(origin, destinations)
            if driving is not None:
                return driving
            logger.warning("ORS unavailable; falling back to Euclidean distances")
        return [
            DistanceResult(
                distance_km=haversine_km(origin[0], origin[1], lat, lon),
                driving_distance_km=None,
                driving_duration_min=None,
            )
            for lat, lon in destinations
        ]

    async def _try_driving(
        self,
        origin: tuple[float, float],
        destinations: list[tuple[float, float]],
    ) -> list[DistanceResult] | None:
        if self._ors_client is None:
            logger.warning("DRIVING mode selected but no ORS client provided")
            return None
        try:
            async with self._ors_client as ors:
                matrix = await ors.driving_matrix(origin, destinations)
        except ORSClientError as exc:
            logger.warning("ORS call failed: %s", exc)
            return None

        return [
            DistanceResult(
                distance_km=m.distance_km,
                driving_distance_km=m.distance_km,
                driving_duration_min=m.duration_min,
            )
            for m in matrix
        ]
