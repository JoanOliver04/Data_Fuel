"""Deterministic Spanish copy for alert notifications.

Messages are built purely from validated data — never invented. Numbers come
from the recommendation/prediction layers; the optional LLM seam only rephrases
this text (it cannot add figures). This keeps notifications trustworthy and
hallucination-free.
"""

from __future__ import annotations

_FUEL_LABELS: dict[str, str] = {
    "gasolina_95": "Gasolina 95",
    "gasolina_95_e10": "Gasolina 95 E10",
    "gasolina_98": "Gasolina 98",
    "gasoil": "Gasóleo A",
    "gasoil_premium": "Gasóleo Premium",
}


def fuel_label(fuel: str) -> str:
    return _FUEL_LABELS.get(fuel, fuel)


def direction_word(pct: float) -> str:
    """Honest direction word for a percentage change."""
    if pct <= -0.05:
        return "bajado"
    if pct >= 0.05:
        return "subido"
    return "sin cambios"
