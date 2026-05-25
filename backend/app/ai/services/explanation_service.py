"""Explanation engine — the orchestration layer.

Coordinates cache → provider → validation → fallback, and is the single place
that turns platform facts into a public ``AIExplanation``.

Anti-hallucination by construction: the LLM only contributes *prose* (summary,
reasoning, supporting factors). The verdict, confidence, risk level and every
number come from the validated ``RecommendationFacts`` — never from the model.
If the model is disabled, fails, times out, or returns unparseable output, a
deterministic explanation built from the same facts is returned instead.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.cache import ai_explanation_cache, ai_trend_cache, make_cache_key
from app.ai.prompts import (
    PROMPT_VERSION,
    render_chat,
    render_prediction,
    render_recommendation,
    render_trend,
)
from app.ai.providers.base import LLMProvider, LLMResult
from app.ai.schemas import (
    AIExplanation,
    ExplanationKind,
    RecommendationFacts,
    RiskLevel,
    TrendFacts,
    TrendSummary,
)
from app.core.metrics import (
    ai_cache_operations_total,
    ai_fallbacks_total,
    ai_generation_duration_seconds,
    ai_hallucination_rejections_total,
    ai_requests_total,
    ai_tokens_total,
)

log = logging.getLogger("app.ai.engine")

_MAX_SUMMARY_CHARS = 600
_MAX_LIST_ITEMS = 6
_MAX_ITEM_CHARS = 240


def _risk_from_confidence(confidence: float) -> RiskLevel:
    if confidence >= 0.66:
        return "LOW"
    if confidence >= 0.40:
        return "MEDIUM"
    return "HIGH"


def _coerce_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip()[:_MAX_ITEM_CHARS])
        if len(out) >= _MAX_LIST_ITEMS:
            break
    return out


def _parse_prose(text: str) -> dict[str, Any] | None:
    """Parse the model's JSON; return a sanitised prose dict, or None if invalid."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return None
    pred = data.get("prediction_summary")
    return {
        "summary": summary.strip()[:_MAX_SUMMARY_CHARS],
        "reasoning": _coerce_str_list(data.get("reasoning")),
        "supporting_factors": _coerce_str_list(data.get("supporting_factors")),
        "prediction_summary": pred.strip()[:_MAX_SUMMARY_CHARS]
        if isinstance(pred, str) and pred.strip()
        else None,
    }


def _prediction_summary(facts: RecommendationFacts) -> str | None:
    p = facts.prediction
    if p is None:
        return None
    return (
        f"Predicción: {p.current_price:.3f} → {p.predicted_price:.3f} €/L "
        f"({p.variation_pct:+.1f}%) en {p.horizon_hours}h; confianza {p.confidence:.0%}."
    )


def _facts_reasoning(facts: RecommendationFacts) -> list[str]:
    reasoning: list[str] = []
    if facts.stations:
        top = facts.stations[0]
        reasoning.append(
            f"{top.brand} ({top.locality}): {top.price_per_liter:.3f} €/L, "
            f"{top.distance_km:.1f} km, coste real {top.total_cost:.2f} €."
        )
        if len(facts.stations) > 1:
            alt = facts.stations[1]
            reasoning.append(
                f"Frente a la alternativa {alt.brand}: coste real {alt.total_cost:.2f} € "
                f"({alt.price_per_liter:.3f} €/L a {alt.distance_km:.1f} km)."
            )
    pred = _prediction_summary(facts)
    if pred:
        reasoning.append(pred)
    reasoning.append(f"Confianza de la valoración: {facts.confidence:.0%}.")
    return reasoning


def _deterministic_explanation(
    kind: ExplanationKind, facts: RecommendationFacts
) -> AIExplanation:
    if facts.stations:
        top = facts.stations[0]
        summary = (
            f"Recomendamos {top.brand} en {top.locality}: el coste real total es "
            f"{top.total_cost:.2f} € ({top.price_per_liter:.3f} €/L a {top.distance_km:.1f} km), "
            "que combina precio y desplazamiento."
        )
    else:
        summary = "No hay estaciones suficientes en la zona para una recomendación."
    return AIExplanation(
        kind=kind,
        verdict=facts.verdict,
        summary=summary,
        reasoning=_facts_reasoning(facts),
        confidence=facts.confidence,
        risk_level=_risk_from_confidence(facts.confidence),
        supporting_factors=["Coste real = combustible + desplazamiento"],
        prediction_summary=_prediction_summary(facts),
        source="fallback",
        prompt_version=PROMPT_VERSION,
    )


def _build_llm_explanation(
    kind: ExplanationKind, facts: RecommendationFacts, prose: dict[str, Any]
) -> AIExplanation:
    return AIExplanation(
        kind=kind,
        verdict=facts.verdict,  # authoritative — never from the model
        summary=prose["summary"],
        reasoning=prose["reasoning"] or _facts_reasoning(facts),
        confidence=facts.confidence,  # authoritative
        risk_level=_risk_from_confidence(facts.confidence),
        supporting_factors=prose["supporting_factors"],
        prediction_summary=prose["prediction_summary"] or _prediction_summary(facts),
        source="llm",
        prompt_version=PROMPT_VERSION,
    )


def _render(kind: ExplanationKind, facts_json: str, question: str | None) -> tuple[str, str]:
    if kind == "prediction":
        return render_prediction(facts_json)
    if kind == "chat":
        return render_chat(question or "", facts_json)
    return render_recommendation(facts_json)


def _record_tokens(kind: str, result: LLMResult) -> None:
    if result.prompt_tokens:
        ai_tokens_total.labels(kind=kind, type="prompt").inc(result.prompt_tokens)
    if result.completion_tokens:
        ai_tokens_total.labels(kind=kind, type="completion").inc(result.completion_tokens)


async def explain(
    kind: ExplanationKind,
    facts: RecommendationFacts,
    provider: LLMProvider,
    *,
    question: str | None = None,
) -> AIExplanation:
    """Return a structured explanation, using the LLM when available else fallback."""
    facts_json = json.dumps(facts.model_dump(), sort_keys=True, default=str, ensure_ascii=False)
    key = make_cache_key(kind, PROMPT_VERSION, provider.name, question or "", facts_json)

    cached = await ai_explanation_cache.get(key)
    if cached is not None:
        ai_cache_operations_total.labels(result="hit").inc()
        ai_requests_total.labels(kind=kind, result="cached").inc()
        return cached.model_copy(update={"cached": True})
    ai_cache_operations_total.labels(result="miss").inc()

    system, user = _render(kind, facts_json, question)
    result = await provider.complete(system, user)
    ai_generation_duration_seconds.labels(kind=kind).observe(result.latency_s)
    _record_tokens(kind, result)

    explanation: AIExplanation | None = None
    if result.ok:
        prose = _parse_prose(result.text)
        if prose is not None:
            explanation = _build_llm_explanation(kind, facts, prose)
            ai_requests_total.labels(kind=kind, result="llm").inc()
        else:
            ai_hallucination_rejections_total.labels(reason="invalid_json").inc()
            log.warning("LLM output rejected (invalid JSON) for kind=%s", kind)

    if explanation is None:
        explanation = _deterministic_explanation(kind, facts)
        ai_fallbacks_total.labels(kind=kind).inc()
        ai_requests_total.labels(kind=kind, result="fallback").inc()

    # Only cache real LLM output, so transient provider failures recover at once.
    if explanation.source == "llm":
        await ai_explanation_cache.set(key, explanation)
    return explanation


def _deterministic_trend(facts: TrendFacts) -> TrendSummary:
    word = {"UP": "al alza", "DOWN": "a la baja", "STABLE": "estables"}[facts.direction]
    delta = f" ({facts.delta_pct:+.1f}%)" if facts.delta_pct is not None else ""
    summary = f"Los precios de {facts.fuel_type} en {facts.area_name} están {word}{delta} esta semana."
    return TrendSummary(
        direction=facts.direction,
        summary=summary,
        delta_pct=facts.delta_pct,
        source="fallback",
    )


async def summarize_trend(facts: TrendFacts, provider: LLMProvider) -> TrendSummary:
    """Return a short price-trend summary (LLM-enriched prose, fallback otherwise)."""
    facts_json = json.dumps(facts.model_dump(), sort_keys=True, default=str, ensure_ascii=False)
    key = make_cache_key("trend", PROMPT_VERSION, provider.name, facts_json)

    cached = await ai_trend_cache.get(key)
    if cached is not None:
        ai_cache_operations_total.labels(result="hit").inc()
        ai_requests_total.labels(kind="trend", result="cached").inc()
        return cached.model_copy(update={"cached": True})
    ai_cache_operations_total.labels(result="miss").inc()

    system, user = render_trend(facts_json)
    result = await provider.complete(system, user)
    ai_generation_duration_seconds.labels(kind="trend").observe(result.latency_s)
    _record_tokens("trend", result)

    summary: TrendSummary | None = None
    if result.ok:
        prose = _parse_prose(result.text)
        if prose is not None:
            summary = TrendSummary(
                direction=facts.direction,
                summary=prose["summary"],
                delta_pct=facts.delta_pct,
                source="llm",
            )
            ai_requests_total.labels(kind="trend", result="llm").inc()
        else:
            ai_hallucination_rejections_total.labels(reason="invalid_json").inc()

    if summary is None:
        summary = _deterministic_trend(facts)
        ai_fallbacks_total.labels(kind="trend").inc()
        ai_requests_total.labels(kind="trend", result="fallback").inc()

    if summary.source == "llm":
        await ai_trend_cache.set(key, summary)
    return summary
