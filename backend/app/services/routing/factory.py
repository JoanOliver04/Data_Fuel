"""Routing provider factory — selects an implementation from settings.

Maps the existing ``DISTANCE_MODE`` values to providers, preserving today's
behaviour exactly:
    EUCLIDEAN                 → HaversineProvider
    DRIVING (with key)        → OrsMatrixProvider
    DRIVING (no key)          → HaversineProvider   (matches DistanceService fallback)
    DRIVING_TOMTOM (with key) → TomTomMatrixProvider
    DRIVING_TOMTOM (no key)   → HaversineProvider

This factory is not yet used by the recommendations endpoint; the endpoint
still runs through DistanceService until a later wiring phase.
"""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.domain.services.distance_service import DistanceMode
from app.infrastructure.external.ors import ORSClient
from app.infrastructure.external.tomtom import TomTomClient
from app.services.routing.protocol import RoutingProvider
from app.services.routing.providers.haversine_provider import HaversineProvider
from app.services.routing.providers.ors_matrix_provider import OrsMatrixProvider
from app.services.routing.providers.tomtom_matrix_provider import TomTomMatrixProvider

log = logging.getLogger(__name__)


def get_routing_provider(settings: Settings) -> RoutingProvider:
    """Return the routing provider for the configured ``DISTANCE_MODE``."""
    mode = DistanceMode(settings.distance_mode)
    if mode is DistanceMode.DRIVING:
        if not settings.ors_api_key:
            log.warning("DRIVING mode without ORS_API_KEY — using haversine provider")
            return HaversineProvider()
        return OrsMatrixProvider(ORSClient())
    if mode is DistanceMode.DRIVING_TOMTOM:
        if not settings.tomtom_api_key:
            log.warning("DRIVING_TOMTOM mode without TOMTOM_API_KEY — using haversine provider")
            return HaversineProvider()
        return TomTomMatrixProvider(TomTomClient(), settings.tomtom_daily_quota_limit)
    return HaversineProvider()
