"""Orchestration over the scoring engine: re-rank stations and summarise.

Consumes the existing :class:`StationCost` list produced by the cost calculator
(so the routing / pricing / fallback pipeline is reused verbatim) and:

* :func:`optimize` — score every station under a profile and re-rank ascending.
* :func:`summarize` — aggregate stats + per-profile winners for the analytics
  endpoint (ETA, traffic, fuel savings, best-profile distribution).

Nothing here performs I/O; callers pass an already-built ``StationCost`` list.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.services.cost_calculator import StationCost
from app.services.optimization.optimization_profiles import (
    PROFILE_WEIGHTS,
    OptimizationProfile,
)
from app.services.optimization.optimization_score import OptimizationResult, evaluate


@dataclass(frozen=True, slots=True)
class OptimizedStation:
    """A scored station plus its 1-based rank under the active profile."""

    station: StationCost
    result: OptimizationResult
    rank: int


@dataclass(frozen=True, slots=True)
class ProfileWinner:
    """The top station a given profile would pick, with its score."""

    profile: OptimizationProfile
    station_id: int
    optimization_score: float


@dataclass(frozen=True, slots=True)
class OptimizationSummary:
    """Aggregate optimization metrics over a candidate set (analytics)."""

    profile: OptimizationProfile
    station_count: int
    average_eta_minutes: float | None
    average_traffic_delay_minutes: float
    average_fuel_savings_eur: float
    best_profile_distribution: dict[str, int]
    profile_winners: list[ProfileWinner]


def _evaluate_station(
    sc: StationCost,
    profile: OptimizationProfile,
    *,
    time_cost_per_hour: float,
    traffic_penalty_factor: float,
) -> OptimizationResult:
    return evaluate(
        fuel_cost=float(sc.fuel_cost),
        travel_cost=float(sc.travel_cost),
        eta_minutes=sc.driving_duration_min,
        traffic_delay_seconds=sc.traffic_delay_seconds,
        profile=profile,
        time_cost_per_hour=time_cost_per_hour,
        traffic_penalty_factor=traffic_penalty_factor,
    )


def optimize(
    stations: Sequence[StationCost],
    profile: OptimizationProfile,
    *,
    time_cost_per_hour: float,
    traffic_penalty_factor: float,
    limit: int | None = None,
) -> list[OptimizedStation]:
    """Score every station under ``profile`` and re-rank by ascending score.

    Ties (equal score) fall back to the input order, which is already the
    cheapest-total-cost ordering from the cost calculator — a sensible
    tie-breaker that keeps results deterministic.
    """
    scored = [
        (
            sc,
            _evaluate_station(
                sc,
                profile,
                time_cost_per_hour=time_cost_per_hour,
                traffic_penalty_factor=traffic_penalty_factor,
            ),
        )
        for sc in stations
    ]
    # Stable sort preserves the cost-ranked input order for equal scores.
    scored.sort(key=lambda pair: pair[1].score)
    ranked = [
        OptimizedStation(station=sc, result=result, rank=i + 1)
        for i, (sc, result) in enumerate(scored)
    ]
    return ranked if limit is None else ranked[:limit]


def _winner_for(
    stations: Sequence[StationCost],
    profile: OptimizationProfile,
    *,
    time_cost_per_hour: float,
    traffic_penalty_factor: float,
) -> ProfileWinner | None:
    best = optimize(
        stations,
        profile,
        time_cost_per_hour=time_cost_per_hour,
        traffic_penalty_factor=traffic_penalty_factor,
        limit=1,
    )
    if not best:
        return None
    top = best[0]
    return ProfileWinner(
        profile=profile,
        station_id=top.station.station_id,
        optimization_score=top.result.score,
    )


def summarize(
    stations: Sequence[StationCost],
    *,
    profile: OptimizationProfile,
    time_cost_per_hour: float,
    traffic_penalty_factor: float,
) -> OptimizationSummary:
    """Aggregate optimization metrics over a candidate set.

    * ``average_eta_minutes`` — mean driving ETA (None when no station has one).
    * ``average_traffic_delay_minutes`` — mean delay across all candidates.
    * ``average_fuel_savings_eur`` — mean per-station saving versus the most
      expensive candidate's fuel cost (what the user avoids by not picking the
      priciest pump), a stable, storage-free proxy for "fuel savings".
    * ``best_profile_distribution`` — for each of the four profiles, which
      station wins; the distribution counts how often each station id is the
      winner (a measure of how preference-robust the top pick is).
    """
    n = len(stations)
    etas = [s.driving_duration_min for s in stations if s.driving_duration_min is not None]
    average_eta = round(sum(etas) / len(etas), 2) if etas else None

    delays_min = [
        (s.traffic_delay_seconds or 0) / 60.0 for s in stations
    ]
    average_delay = round(sum(delays_min) / n, 2) if n else 0.0

    if n:
        max_fuel = max(float(s.fuel_cost) for s in stations)
        savings = [max_fuel - float(s.fuel_cost) for s in stations]
        average_savings = round(sum(savings) / n, 3)
    else:
        average_savings = 0.0

    winners = [
        w
        for profile_key in PROFILE_WEIGHTS
        if (
            w := _winner_for(
                stations,
                profile_key,
                time_cost_per_hour=time_cost_per_hour,
                traffic_penalty_factor=traffic_penalty_factor,
            )
        )
        is not None
    ]
    distribution: dict[str, int] = {}
    for w in winners:
        key = str(w.station_id)
        distribution[key] = distribution.get(key, 0) + 1

    return OptimizationSummary(
        profile=profile,
        station_count=n,
        average_eta_minutes=average_eta,
        average_traffic_delay_minutes=average_delay,
        average_fuel_savings_eur=average_savings,
        best_profile_distribution=distribution,
        profile_winners=winners,
    )
