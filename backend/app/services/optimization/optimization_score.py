"""The multi-objective scoring engine.

Pure, dependency-free arithmetic over four euro-denominated cost components:

* **fuel_cost**      litres * price            (€) — from the cost calculator.
* **travel_cost**    distance_km * km_cost     (€) — from the cost calculator.
* **time_cost**      eta_minutes * time_value  (€) — "time has value" (Phase 2).
* **traffic_penalty** delay_min * penalty_rate (€) — congestion aversion.

The scalar objective is a weighted sum (a standard weighted-sum scalarization
of a multi-objective problem):

    score = w_fuel·fuel_cost + w_distance·travel_cost
          + w_time·time_cost + w_traffic·traffic_penalty

Lower is better. Because every term is already in €, an *equal* weighting
reduces the score to a plain total cost; profiles simply re-weight the user's
preferences. ETA / traffic data is optional (haversine and ORS expose no
driving time): when absent, ``time_cost`` and ``traffic_penalty`` are 0 and the
score degrades gracefully to fuel + travel cost.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.optimization.optimization_profiles import (
    OptimizationProfile,
    ProfileWeights,
    weights_for,
)

_SECONDS_PER_MINUTE = 60.0
_MINUTES_PER_HOUR = 60.0


@dataclass(frozen=True, slots=True)
class CostComponents:
    """The four euro-denominated terms that make up the objective."""

    fuel_cost: float
    travel_cost: float
    time_cost: float
    traffic_penalty: float
    # The ETA (driving minutes) the time cost was derived from. ``None`` when no
    # routing duration was available (straight-line / failed leg).
    eta_minutes: float | None


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """A single station's components, scalar score and the profile used."""

    components: CostComponents
    score: float
    profile: OptimizationProfile


def time_cost(eta_minutes: float | None, time_cost_per_hour: float) -> float:
    """Monetise travel time: ``eta_minutes * (time_cost_per_hour / 60)``.

    Returns 0.0 when the ETA is unknown so straight-line distance modes keep a
    well-defined (fuel + travel only) score.
    """
    if eta_minutes is None or eta_minutes <= 0.0:
        return 0.0
    return eta_minutes * (time_cost_per_hour / _MINUTES_PER_HOUR)


def traffic_penalty(traffic_delay_seconds: int | None, traffic_penalty_factor: float) -> float:
    """Monetise congestion: ``(delay_seconds / 60) * penalty_factor``.

    Returns 0.0 when the provider exposes no traffic data (haversine, ORS) or
    the route is free-flowing.
    """
    if traffic_delay_seconds is None or traffic_delay_seconds <= 0:
        return 0.0
    return (traffic_delay_seconds / _SECONDS_PER_MINUTE) * traffic_penalty_factor


def optimization_score(components: CostComponents, weights: ProfileWeights) -> float:
    """Weighted-sum scalarization of the four components (lower is better)."""
    return (
        weights.fuel * components.fuel_cost
        + weights.distance * components.travel_cost
        + weights.time * components.time_cost
        + weights.traffic * components.traffic_penalty
    )


def evaluate(
    *,
    fuel_cost: float,
    travel_cost: float,
    eta_minutes: float | None,
    traffic_delay_seconds: int | None,
    profile: OptimizationProfile,
    time_cost_per_hour: float,
    traffic_penalty_factor: float,
    weights_override: ProfileWeights | None = None,
) -> OptimizationResult:
    """Compute the full objective for one station under ``profile``."""
    components = CostComponents(
        fuel_cost=fuel_cost,
        travel_cost=travel_cost,
        time_cost=round(time_cost(eta_minutes, time_cost_per_hour), 4),
        traffic_penalty=round(traffic_penalty(traffic_delay_seconds, traffic_penalty_factor), 4),
        eta_minutes=eta_minutes,
    )
    weights = weights_for(profile, weights_override)
    return OptimizationResult(
        components=components,
        score=round(optimization_score(components, weights), 4),
        profile=profile,
    )
