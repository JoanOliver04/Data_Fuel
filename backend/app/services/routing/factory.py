"""Routing provider factory — selects an implementation from settings.

Maps the existing ``DISTANCE_MODE`` values to providers, preserving today's
behaviour exactly:
    EUCLIDEAN          → HaversineProvider
    DRIVING (with key) → OrsMatrixProvider
    DRIVING (no key)   → HaversineProvider   (matches DistanceService fallback)

New modes (DRIVING_ORS / DRIVING_TOMTOM) and the TomTom provider are wired in a
later phase; this factory is not yet used by the recommendations endpoint.
"""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.domain.services.distance_service import DistanceMode
from app.infrastructure.external.ors import ORSClient
from app.services.routing.protocol import RoutingProvider
from app.services.routing.providers.haversine_provider import HaversineProvider
from app.services.routing.providers.ors_matrix_provider import OrsMatrixProvider

log = logging.getLogger(__name__)


def get_routing_provider(settings: Settings) -> RoutingProvider:
    """Return the routing provider for the configured ``DISTANCE_MODE``."""
    mode = DistanceMode(settings.distance_mode)
    if mode is DistanceMode.DRIVING:
        if not settings.ors_api_key:
            log.warning("DRIVING mode without ORS_API_KEY — using haversine provider")
            return HaversineProvider()
        return OrsMatrixProvider(ORSClient())
    return HaversineProvider()
