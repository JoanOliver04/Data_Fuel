"""Traffic-aware multi-objective optimization layer.

This package turns Data Fuel from a cheapest-price finder into a route-aware
decision engine. It scores each candidate station on a single, additive,
euro-denominated objective that blends four cost components:

    OptimizationScore = w_fuel·fuel_cost
                      + w_distance·travel_cost
                      + w_time·time_cost
                      + w_traffic·traffic_penalty

The weights come from a user-selectable :class:`OptimizationProfile`
(CHEAPEST / BALANCED / FASTEST / COMMUTER). Every component is already expressed
in € so the scalarized objective is itself a € figure that a non-technical user
can read directly.

The layer is purely additive: it consumes the existing :class:`StationCost`
ranking output and re-ranks it. It never replaces the cost calculator, the
routing providers (TomTom / ORS / haversine) or the Random Forest advice.
"""

from __future__ import annotations

from app.services.optimization.optimization_profiles import (
    DEFAULT_PROFILE,
    PROFILE_WEIGHTS,
    OptimizationProfile,
    ProfileWeights,
    weights_for,
)
from app.services.optimization.optimization_score import (
    CostComponents,
    OptimizationResult,
    evaluate,
    optimization_score,
    time_cost,
    traffic_penalty,
)
from app.services.optimization.optimization_service import (
    OptimizationSummary,
    OptimizedStation,
    ProfileWinner,
    optimize,
    summarize,
)

__all__ = [
    "DEFAULT_PROFILE",
    "PROFILE_WEIGHTS",
    "CostComponents",
    "OptimizationProfile",
    "OptimizationResult",
    "OptimizationSummary",
    "OptimizedStation",
    "ProfileWeights",
    "ProfileWinner",
    "evaluate",
    "optimization_score",
    "optimize",
    "summarize",
    "time_cost",
    "traffic_penalty",
    "weights_for",
]
