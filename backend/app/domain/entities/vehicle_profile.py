"""Vehicle profile domain entity, driving-style and consumption-mode enums.

The consumption mode determines which of the three stored consumption values
is applied when computing the per-km cost (K) toward a given station. The
mode is selected automatically from the driving distance.
"""

from __future__ import annotations

from enum import StrEnum

# Distance thresholds (km) that bucket trips into urban / mixed / highway.
URBAN_MAX_KM: float = 5.0
HIGHWAY_MIN_KM: float = 20.0


class DrivingStyle(StrEnum):
    URBAN = "urban"
    MIXED = "mixed"
    HIGHWAY = "highway"


class ConsumptionMode(StrEnum):
    URBAN = "urban"
    MIXED = "mixed"
    HIGHWAY = "highway"


def select_consumption_mode(distance_km: float) -> ConsumptionMode:
    """Return the consumption mode that applies for a given driving distance.

    < 5 km           → URBAN
    5 km ≤ d < 20 km → MIXED
    ≥ 20 km          → HIGHWAY
    """
    if distance_km < URBAN_MAX_KM:
        return ConsumptionMode.URBAN
    if distance_km < HIGHWAY_MIN_KM:
        return ConsumptionMode.MIXED
    return ConsumptionMode.HIGHWAY
