"""Port for any driving-distance/duration provider.

Coordinates are ``(latitude, longitude)`` tuples, matching the existing
``ORSClient`` / ``DistanceService`` convention (the project has no Coordinate
value object). Implementations live in ``app.services.routing.providers``:
``HaversineProvider``, ``OrsMatrixProvider`` and (later) ``TomTomMatrixProvider``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.services.routing.dto import RouteLeg


@runtime_checkable
class RoutingProvider(Protocol):
    """A single-origin / N-destination distance + duration matrix provider."""

    async def matrix(
        self,
        origin: tuple[float, float],
        destinations: Sequence[tuple[float, float]],
    ) -> list[RouteLeg]:
        """Return one ``RouteLeg`` per destination, in input order.

        MUST NOT raise on partial or total provider failure: failed legs return
        a ``RouteLeg`` with ``failed=True`` and the haversine fallback distance.
        An empty ``destinations`` returns an empty list without any I/O.
        """
        ...
