"""Conversation-safe schemas for the AI assistant layer.

These models are the *only* shapes that cross the AI boundary. Raw LLM output is
never returned directly — it is parsed into ``AIExplanation`` (prose fields
only); every number/verdict is set from validated platform data, not the model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Verdict = Literal["REFUEL_NOW", "WAIT", "NEUTRAL"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
ExplanationKind = Literal["recommendation", "prediction", "trend", "chat"]

# ── Facts injected into prompts (also drive deterministic fallback) ────────────


class StationFact(BaseModel):
    """One ranked station, as the recommendation engine already computed it."""

    rank: int
    brand: str
    locality: str
    price_per_liter: float
    distance_km: float
    total_cost: float
    driving_duration_min: float | None = None
    traffic_delay_seconds: int | None = None


class PredictionFact(BaseModel):
    """Price-forecast facts from the ML layer (never invented by the LLM)."""

    current_price: float
    predicted_price: float
    variation_pct: float
    horizon_hours: int
    confidence: float
    model_r2: float | None = None


class RecommendationFacts(BaseModel):
    """Everything the assistant is allowed to reason from for a recommendation."""

    fuel_type: str
    municipio: str | None = None
    comarca: str | None = None
    liters: float
    km_cost: float
    stations: list[StationFact]
    prediction: PredictionFact | None = None
    # Authoritative verdict/confidence derived from platform data, not the LLM.
    verdict: Verdict
    confidence: float
    model_version: str | None = None


class TrendFacts(BaseModel):
    """Aggregate price-trend facts for a comarca/municipio window."""

    fuel_type: str
    area_name: str
    mean_price_today: float | None = None
    mean_price_last_week: float | None = None
    delta_pct: float | None = None
    direction: Literal["UP", "DOWN", "STABLE"]


# ── Public AI responses ────────────────────────────────────────────────────────


class AIExplanation(BaseModel):
    """Structured, sanitised explanation returned by every AI endpoint."""

    kind: ExplanationKind
    verdict: Verdict
    summary: str
    reasoning: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    supporting_factors: list[str] = Field(default_factory=list)
    prediction_summary: str | None = None
    # Provenance / observability — honest about whether an LLM was involved.
    source: Literal["llm", "fallback"]
    cached: bool = False
    prompt_version: str


class TrendSummary(BaseModel):
    direction: Literal["UP", "DOWN", "STABLE"]
    summary: str
    delta_pct: float | None = None
    source: Literal["llm", "fallback"]
    cached: bool = False


# ── Requests ────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Free-text question, scoped to a recommendation context."""

    question: str = Field(min_length=1, max_length=4000)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    fuel_type: str
    liters: float = Field(gt=0, le=200, default=50.0)
    municipio: str | None = None
    comarca: str | None = None
