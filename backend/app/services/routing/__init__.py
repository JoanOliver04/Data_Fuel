"""Pluggable routing provider abstraction (distance + duration matrix).

Additive layer: the recommendations endpoint still uses DistanceService until a
later phase wires this in. See ``protocol.RoutingProvider`` for the port.
"""

from app.services.routing.dto import RouteLeg
from app.services.routing.factory import get_routing_provider
from app.services.routing.protocol import RoutingProvider
from app.services.routing.providers import (
    HaversineProvider,
    OrsMatrixProvider,
    TomTomMatrixProvider,
    haversine_leg,
)
from app.services.routing.quota import DailyQuotaGuard, QuotaSnapshot, default_quota_guard

__all__ = [
    "DailyQuotaGuard",
    "HaversineProvider",
    "OrsMatrixProvider",
    "QuotaSnapshot",
    "RouteLeg",
    "RoutingProvider",
    "TomTomMatrixProvider",
    "default_quota_guard",
    "get_routing_provider",
    "haversine_leg",
]
