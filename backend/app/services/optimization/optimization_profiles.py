"""User-selectable optimization profiles and their objective weights.

A profile expresses *preference*, not facts: how much the user cares about the
price at the pump versus the distance driven, the time lost and the traffic
endured. Each profile maps to a :class:`ProfileWeights` whose four components
sum to 1.0, so the resulting :func:`optimization_score` stays on the same euro
scale across profiles and remains directly comparable between stations.

Profiles (weights: fuel / distance / time / traffic)
----------------------------------------------------
* **CHEAPEST**  70 / 20 / 10 /  0 — classic "lowest total cost" behaviour.
* **BALANCED**  40 / 25 / 25 / 10 — sensible default for a one-off trip.
* **FASTEST**   15 / 15 / 50 / 20 — minimise time and congestion exposure.
* **COMMUTER**  20 / 20 / 40 / 20 — daily driver: time and traffic dominate.

Extension hook
--------------
:func:`weights_for` accepts an optional ``override`` so future features
(personalized time value, company fleets, EV charging profiles) can supply
bespoke weights without touching the enum or the scoring engine. None of those
are implemented here — only the seam exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

_WEIGHT_SUM_TOLERANCE = 1e-6


class OptimizationProfile(StrEnum):
    """Preference profile shared verbatim between backend and frontend."""

    CHEAPEST = "CHEAPEST"
    BALANCED = "BALANCED"
    FASTEST = "FASTEST"
    COMMUTER = "COMMUTER"


@dataclass(frozen=True, slots=True)
class ProfileWeights:
    """Relative weight of each objective component. Must sum to ~1.0.

    Validated at construction so a malformed profile fails loudly at import
    time rather than silently skewing every ranking.
    """

    fuel: float
    distance: float
    time: float
    traffic: float

    def __post_init__(self) -> None:
        total = self.fuel + self.distance + self.time + self.traffic
        if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
            raise ValueError(f"profile weights must sum to 1.0, got {total}")
        if min(self.fuel, self.distance, self.time, self.traffic) < 0.0:
            raise ValueError("profile weights must be non-negative")


# The single source of truth for profile → weights. Frozen ProfileWeights make
# the mapping effectively immutable.
PROFILE_WEIGHTS: dict[OptimizationProfile, ProfileWeights] = {
    OptimizationProfile.CHEAPEST: ProfileWeights(fuel=0.70, distance=0.20, time=0.10, traffic=0.0),
    OptimizationProfile.BALANCED: ProfileWeights(fuel=0.40, distance=0.25, time=0.25, traffic=0.10),
    OptimizationProfile.FASTEST: ProfileWeights(fuel=0.15, distance=0.15, time=0.50, traffic=0.20),
    OptimizationProfile.COMMUTER: ProfileWeights(fuel=0.20, distance=0.20, time=0.40, traffic=0.20),
}

# Backwards compatibility wins over the spec's "default = BALANCED": the raw
# recommendations endpoint defaults to *no* profile (legacy cost ranking). When
# a profile IS requested but unspecified at a lower layer, this is the default.
DEFAULT_PROFILE: OptimizationProfile = OptimizationProfile.BALANCED


def weights_for(
    profile: OptimizationProfile,
    override: ProfileWeights | None = None,
) -> ProfileWeights:
    """Resolve the weights for a profile.

    ``override`` is an extension hook for personalized / fleet / EV weighting:
    when supplied it wins, letting callers inject bespoke preferences without a
    new enum member. Unused by the current endpoints.
    """
    if override is not None:
        return override
    return PROFILE_WEIGHTS[profile]
