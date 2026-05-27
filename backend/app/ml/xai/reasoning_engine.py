"""Deterministic natural-language reasoning over SHAP explanations.

Turns a model's SHAP attribution into a short, professional paragraph a
non-technical user can read — with **no** generative AI and therefore **no**
hallucination risk. Every sentence is assembled from curated, locale-keyed
fragments (:mod:`app.ml.xai.feature_metadata`), so the output is fully
reproducible and auditable.

The narrative is verdict-aligned: it surfaces the factors whose SHAP impact
*supports* the predicted direction (price down → "ESPERA"; price up → "REPOSTA
AHORA"), which is what a user actually wants to know — "why this advice?".
"""

from __future__ import annotations

from app.ml.xai.feature_metadata import DEFAULT_LOCALE, get_feature_copy
from app.ml.xai.shap_explainer import ShapContribution

# Verdict strings (match RecommendationResponse.veredicto).
VERDICT_WAIT = "ESPERA"
VERDICT_REFUEL = "REPOSTA AHORA"

_DEFAULT_MAX_FACTORS = 3
# Impacts below this magnitude (€/L) are noise, not "reasons".
_MIN_IMPACT = 1e-4


_LEAD: dict[str, dict[str, str]] = {
    "es": {
        VERDICT_WAIT: (
            "Data Fuel prevé que el precio bajará un {pct:.1f}% la próxima semana. "
            "Conviene esperar, principalmente porque:"
        ),
        VERDICT_REFUEL: (
            "Data Fuel recomienda repostar ahora: el precio subirá un {pct:.1f}% "
            "la próxima semana, principalmente porque:"
        ),
    },
    "en": {
        VERDICT_WAIT: (
            "Data Fuel forecasts the price dropping {pct:.1f}% next week, so it is "
            "worth waiting — mainly because:"
        ),
        VERDICT_REFUEL: (
            "Data Fuel recommends refuelling now: the price will rise {pct:.1f}% "
            "next week, mainly because:"
        ),
    },
}

_NEUTRAL: dict[str, str] = {
    "es": (
        "Data Fuel no prevé cambios significativos en el precio la próxima semana; "
        "el modelo no encuentra factores con un peso claro en ninguna dirección."
    ),
    "en": (
        "Data Fuel does not foresee a significant price change next week; the model "
        "finds no factor weighing clearly in either direction."
    ),
}

_FALLBACK_LEAD: dict[str, dict[str, str]] = {
    "es": {
        VERDICT_WAIT: (
            "Data Fuel prevé que el precio bajará un {pct:.1f}% la próxima semana. "
            "El desglose por factor no está disponible; los más influyentes del "
            "modelo son:"
        ),
        VERDICT_REFUEL: (
            "Data Fuel recomienda repostar ahora (subida prevista del {pct:.1f}%). "
            "El desglose por factor no está disponible; los más influyentes del "
            "modelo son:"
        ),
    },
    "en": {
        VERDICT_WAIT: (
            "Data Fuel forecasts a {pct:.1f}% drop next week. A per-factor breakdown "
            "is unavailable; the model's most influential features are:"
        ),
        VERDICT_REFUEL: (
            "Data Fuel recommends refuelling now (forecast rise of {pct:.1f}%). A "
            "per-factor breakdown is unavailable; the model's most influential "
            "features are:"
        ),
    },
}


def _locale_table(table: dict[str, dict[str, str]], locale: str) -> dict[str, str]:
    return table.get(locale, table[DEFAULT_LOCALE])


def _join_bullets(lead: str, bullets: list[str]) -> str:
    return lead + "\n" + "\n".join(f"- {b}." for b in bullets)


def generate(
    *,
    veredicto: str,
    variacion_pct: float,
    contributions: list[ShapContribution],
    locale: str = DEFAULT_LOCALE,
    max_factors: int = _DEFAULT_MAX_FACTORS,
) -> str:
    """Build a verdict-aligned explanation paragraph from SHAP contributions.

    ``contributions`` is the full signed attribution (any order; this function
    selects and orders the relevant ones). Negative impact lowers the predicted
    price, positive raises it.
    """
    want_down = veredicto == VERDICT_WAIT
    # Factors whose sign supports the verdict, strongest first.
    supporting = [
        c
        for c in contributions
        if abs(c.impact) >= _MIN_IMPACT and ((c.impact < 0) == want_down)
    ]
    supporting.sort(key=lambda c: abs(c.impact), reverse=True)

    if not supporting:
        return _NEUTRAL.get(locale, _NEUTRAL[DEFAULT_LOCALE])

    lead = _locale_table(_LEAD, locale)[veredicto].format(pct=abs(variacion_pct))
    bullets = [
        (get_feature_copy(c.feature, locale).lowers if c.impact < 0
         else get_feature_copy(c.feature, locale).raises)
        for c in supporting[:max_factors]
    ]
    return _join_bullets(lead, bullets)


def generate_fallback(
    *,
    veredicto: str,
    variacion_pct: float,
    top_features: list[str],
    locale: str = DEFAULT_LOCALE,
    max_factors: int = _DEFAULT_MAX_FACTORS,
) -> str:
    """Reasoning when SHAP is unavailable: name the globally most-important features.

    Honest about the limitation (no per-instance breakdown) while still giving
    the user the model's headline drivers.
    """
    lead = _locale_table(_FALLBACK_LEAD, locale)[veredicto].format(pct=abs(variacion_pct))
    bullets = [get_feature_copy(f, locale).label for f in top_features[:max_factors]]
    if not bullets:
        return lead.rstrip(":") + "."
    return _join_bullets(lead, bullets)
