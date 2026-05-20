"""Data transfer object for the routing provider abstraction.

A ``RouteLeg`` is one origin→destination result, provider-agnostic. Durations
are in seconds (TomTom's native unit and the most precise common
denominator); the recommendation layer converts to minutes when it maps these
into the existing response shape in a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RouteLeg:
    """One leg from the user origin to a single destination.

    Attributes:
        distance_km: Driving distance when available, otherwise the haversine
            fallback distance (see ``failed``).
        duration_seconds: Driving time in seconds, or ``None`` when the provider
            does not return it (e.g. haversine) or the leg fell back.
        traffic_delay_seconds: Seconds of delay versus free-flow. ``None`` for
            providers without traffic data (haversine, ORS).
        provider: The provider that was *asked* for this leg
            ("haversine" | "ors" | "tomtom") — stays the requested provider
            even when ``failed`` is True, so the caller knows what degraded.
        failed: True when the requested provider could not produce this leg and
            ``distance_km`` is the haversine fallback.
    """

    distance_km: float
    duration_seconds: int | None
    traffic_delay_seconds: int | None
    provider: str
    failed: bool = False
