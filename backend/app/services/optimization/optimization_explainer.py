"""Deterministic natural-language rationale for an optimization choice.

Mirrors the XAI reasoning engine philosophy: curated, locale-keyed templates,
**no** generative AI and therefore no hallucination risk. Each profile has a
fixed rationale plus an optional data-driven addendum (ETA, traffic, savings
versus the runner-up) assembled from the winning station's own figures.

Default locale is Spanish (``es``) to match the rest of Data Fuel; English
(``en``) is provided so the optimization layer is multilingual-ready.
"""

from __future__ import annotations

from app.services.optimization.optimization_profiles import OptimizationProfile

DEFAULT_LOCALE = "es"

# Per-profile rationale (the "why this station" headline).
_RATIONALE: dict[str, dict[OptimizationProfile, str]] = {
    "es": {
        OptimizationProfile.CHEAPEST: (
            "Esta gasolinera maximiza el ahorro en combustible manteniendo el coste "
            "de desplazamiento dentro de lo razonable."
        ),
        OptimizationProfile.BALANCED: (
            "Esta gasolinera se ha elegido porque ofrece un buen equilibrio entre "
            "precio del combustible, distancia y tiempo estimado de llegada."
        ),
        OptimizationProfile.FASTEST: (
            "Esta gasolinera se ha priorizado porque minimiza el tiempo total de "
            "viaje y evita las rutas congestionadas."
        ),
        OptimizationProfile.COMMUTER: (
            "Esta gasolinera es óptima para el día a día porque reduce la exposición "
            "al tráfico y el tiempo de viaje."
        ),
    },
    "en": {
        OptimizationProfile.CHEAPEST: (
            "This station maximises fuel savings while keeping travel costs acceptable."
        ),
        OptimizationProfile.BALANCED: (
            "This station was selected because it offers a strong balance between "
            "fuel price, travel distance and estimated arrival time."
        ),
        OptimizationProfile.FASTEST: (
            "This station was prioritised because it minimises total travel time and "
            "avoids congested routes."
        ),
        OptimizationProfile.COMMUTER: (
            "This station is optimal for daily commuting because it reduces traffic "
            "exposure and travel time."
        ),
    },
}

_ADDENDA: dict[str, dict[str, str]] = {
    "es": {
        "eta": "Llegada estimada: {eta:.0f} min.",
        "traffic": "Retraso por tráfico: {delay:.0f} min.",
        "savings": "Ahorras {savings:.2f} € frente a la segunda opción.",
    },
    "en": {
        "eta": "Estimated arrival: {eta:.0f} min.",
        "traffic": "Traffic delay: {delay:.0f} min.",
        "savings": "You save {savings:.2f} € versus the runner-up.",
    },
}


def _locale_key(locale: str) -> str:
    return locale if locale in _RATIONALE else DEFAULT_LOCALE


def explain(
    *,
    profile: OptimizationProfile,
    eta_minutes: float | None = None,
    traffic_delay_minutes: float | None = None,
    savings_vs_runner_up: float | None = None,
    locale: str = DEFAULT_LOCALE,
) -> str:
    """Build the rationale for the winning station under ``profile``.

    The headline is profile-specific and always present; the ETA / traffic /
    savings sentences are appended only when the underlying figure is available
    and meaningful, so the text never asserts data the route did not provide.
    """
    key = _locale_key(locale)
    parts = [_RATIONALE[key][profile]]
    addenda = _ADDENDA[key]
    if eta_minutes is not None and eta_minutes > 0:
        parts.append(addenda["eta"].format(eta=eta_minutes))
    if traffic_delay_minutes is not None and traffic_delay_minutes > 0:
        parts.append(addenda["traffic"].format(delay=traffic_delay_minutes))
    if savings_vs_runner_up is not None and savings_vs_runner_up > 0:
        parts.append(addenda["savings"].format(savings=savings_vs_runner_up))
    return " ".join(parts)
