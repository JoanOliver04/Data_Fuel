"""Tests for the explanation engine: fallback, hallucination guard, cache."""

import json

from app.ai.providers.base import LLMResult
from app.ai.providers.fallback import FallbackProvider
from app.ai.schemas import PredictionFact, RecommendationFacts, StationFact, TrendFacts
from app.ai.services.explanation_service import explain, summarize_trend
from app.core.metrics import REGISTRY


class StubProvider:
    """Deterministic provider returning canned text; counts calls."""

    name = "stub"

    def __init__(self, text: str, ok: bool = True) -> None:
        self._text = text
        self._ok = ok
        self.calls = 0

    async def complete(self, system: str, user: str) -> LLMResult:
        self.calls += 1
        if not self._ok:
            return LLMResult(ok=False, reason="http", provider="stub")
        return LLMResult(
            ok=True, text=self._text, prompt_tokens=5, completion_tokens=5, provider="stub"
        )


def _facts(model_version: str) -> RecommendationFacts:
    return RecommendationFacts(
        fuel_type="gasolina_95",
        liters=40,
        km_cost=0.13,
        stations=[
            StationFact(rank=1, brand="REPSOL", locality="Alzira",
                        price_per_liter=1.489, distance_km=2.3, total_cost=60.10),
        ],
        prediction=PredictionFact(current_price=1.489, predicted_price=1.46,
                                  variation_pct=-1.9, horizon_hours=48, confidence=0.72),
        verdict="WAIT",
        confidence=0.72,
        model_version=model_version,
    )


async def test_fallback_when_provider_disabled() -> None:
    exp = await explain("recommendation", _facts("vF1"), FallbackProvider())
    assert exp.source == "fallback"
    assert exp.verdict == "WAIT"  # from facts
    assert "60.10" in exp.summary  # number from facts, not invented
    assert exp.risk_level == "LOW"  # confidence 0.72


async def test_llm_prose_used_but_verdict_stays_authoritative() -> None:
    # Model tries to override the verdict; engine must ignore it.
    text = json.dumps(
        {"summary": "Explicación LLM", "reasoning": ["r1", "r2"],
         "supporting_factors": ["f1"], "prediction_summary": "p", "verdict": "REFUEL_NOW"}
    )
    exp = await explain("recommendation", _facts("vL1"), StubProvider(text))
    assert exp.source == "llm"
    assert exp.summary == "Explicación LLM"
    assert exp.reasoning == ["r1", "r2"]
    assert exp.verdict == "WAIT"  # NOT the model's REFUEL_NOW
    assert exp.confidence == 0.72


async def test_invalid_json_is_rejected_and_falls_back() -> None:
    before = REGISTRY.get_sample_value(
        "datafuel_ai_hallucination_rejections_total", {"reason": "invalid_json"}
    ) or 0.0
    exp = await explain("recommendation", _facts("vL2"), StubProvider("not json at all"))
    assert exp.source == "fallback"
    after = REGISTRY.get_sample_value(
        "datafuel_ai_hallucination_rejections_total", {"reason": "invalid_json"}
    ) or 0.0
    assert after == before + 1.0


async def test_llm_result_is_cached() -> None:
    provider = StubProvider(json.dumps({"summary": "cacheable"}))
    facts = _facts("vCACHE")
    first = await explain("recommendation", facts, provider)
    second = await explain("recommendation", facts, provider)
    assert provider.calls == 1  # second served from cache
    assert first.cached is False
    assert second.cached is True
    assert second.summary == "cacheable"


async def test_trend_fallback_and_llm() -> None:
    facts = TrendFacts(fuel_type="gasolina_95", area_name="Ribera Alta",
                       mean_price_today=1.50, mean_price_last_week=1.53,
                       delta_pct=-1.96, direction="DOWN")
    fb = await summarize_trend(facts, FallbackProvider())
    assert fb.source == "fallback"
    assert fb.direction == "DOWN"

    llm = await summarize_trend(facts, StubProvider(json.dumps({"summary": "Bajando"})))
    assert llm.source == "llm"
    assert llm.summary == "Bajando"
