"""Routing provider factory — selects an implementation from settings.

Maps ``DISTANCE_MODE`` to a provider, preserving today's behaviour:
    EUCLIDEAN | HAVERSINE          → HaversineProvider
    DRIVING | DRIVING_ORS (key)    → OrsMatrixProvider
    DRIVING | DRIVING_ORS (no key) → HaversineProvider   (matches old fallback)
    DRIVING_TOMTOM (with key)      → TomTomMatrixProvider
    DRIVING_TOMTOM (no key)        → HaversineProvider

``DRIVING`` is the legacy alias of ``DRIVING_ORS``; ``HAVERSINE`` of
``EUCLIDEAN``. A missing key degrades to haversine rather than failing, so a
misconfigured driving mode never breaks the endpoint.
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
    if mode in (DistanceMode.DRIVING, DistanceMode.DRIVING_ORS):
        if not settings.ors_api_key:
            log.warning("%s mode without ORS_API_KEY — using haversine provider", mode.value)
            return HaversineProvider()
        return OrsMatrixProvider(ORSClient())
    if mode is DistanceMode.DRIVING_TOMTOM:
        if not settings.tomtom_api_key:
            log.warning("DRIVING_TOMTOM mode without TOMTOM_API_KEY — using haversine provider")
            return HaversineProvider()
        return TomTomMatrixProvider(TomTomClient(), settings.tomtom_daily_quota_limit)
    return HaversineProvider()
