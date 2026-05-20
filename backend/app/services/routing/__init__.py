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
    haversine_leg,
)

__all__ = [
    "HaversineProvider",
    "OrsMatrixProvider",
    "RouteLeg",
    "RoutingProvider",
    "get_routing_provider",
    "haversine_leg",
]
