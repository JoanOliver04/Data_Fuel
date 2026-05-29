"""Schemas for the traffic-aware optimization analytics endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.optimization import OptimizationProfile


class ProfileWinnerOut(BaseModel):
    """The top station a given profile would select over the candidate set."""

    profile: OptimizationProfile
    station_id: int
    optimization_score: float


class OptimizationSummaryOut(BaseModel):
    """Aggregate optimization metrics for a query — future dashboard fodder."""

    profile: OptimizationProfile
    station_count: int = Field(ge=0)
    average_eta_minutes: float | None = None
    average_traffic_delay_minutes: float
    average_fuel_savings_eur: float
    # station_id (as string key) -> number of profiles that pick it as winner.
    best_profile_distribution: dict[str, int]
    profile_winners: list[ProfileWinnerOut]
