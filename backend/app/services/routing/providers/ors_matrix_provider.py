"""ORS routing provider: adapts the existing ORSClient to RoutingProvider.

This is a thin adapter over the unchanged ``ORSClient`` — it does not move or
alter the ORS Matrix logic, it wraps it. Behaviour mirrors the current
``DistanceService`` DRIVING path: on a whole-call ORS failure every leg
degrades to haversine; additionally, any individual unreachable leg (ORS
returns an infinite distance) degrades just that leg. The adapter never raises.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence

from app.infrastructure.external.ors import ORSClient, ORSClientError
from app.services.routing.dto import RouteLeg
from app.services.routing.providers.haversine_provider import haversine_leg

log = logging.getLogger(__name__)

PROVIDER_NAME = "ors"


class OrsMatrixProvider:
    """RoutingProvider backed by the OpenRouteService Matrix API."""

    def __init__(self, ors_client: ORSClient) -> None:
        self._ors_client = ors_client

    async def matrix(
        self,
        origin: tuple[float, float],
        destinations: Sequence[tuple[float, float]],
    ) -> list[RouteLeg]:
        if not destinations:
            return []

        dest_list = list(destinations)
        try:
            async with self._ors_client as ors:
                results = await ors.driving_matrix(origin, dest_list)
        except ORSClientError as exc:
            log.warning("ORS matrix failed (%s); degrading all legs to haversine", exc)
            return [
                haversine_leg(origin, dest, provider=PROVIDER_NAME, failed=True)
                for dest in dest_list
            ]

        legs: list[RouteLeg] = []
        for dest, result in zip(dest_list, results, strict=True):
            # ORSClient maps unreachable destinations to inf for both metrics.
            if math.isinf(result.distance_km):
                legs.append(haversine_leg(origin, dest, provider=PROVIDER_NAME, failed=True))
                continue
            duration_seconds = (
                None if math.isinf(result.duration_min) else round(result.duration_min * 60)
            )
            legs.append(
                RouteLeg(
                    distance_km=round(result.distance_km, 3),
                    duration_seconds=duration_seconds,
                    traffic_delay_seconds=None,
                    provider=PROVIDER_NAME,
                    failed=False,
                )
            )
        return legs
