"""Optional LLM rephrase of a deterministic alert message.

Anti-hallucination by construction: the LLM may only restyle the prose. Any
output that introduces a number not present in the deterministic message is
rejected and the original text is kept. Disabled providers, failures, parse
errors and fabricated figures all silently fall back — alerts never depend on
the LLM being available.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from app.alerts.cache import alert_explanation_cache
from app.alerts.schemas import TriggerSource
from app.core.metrics import alert_ai_explanation_failures_total

if TYPE_CHECKING:
    from app.ai.providers.base import LLMProvider

log = logging.getLogger("app.alerts.enrich")

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_SYSTEM = (
    "Reescribe alertas de combustible en español, claras y breves "
    "(máx 240 caracteres). NUNCA inventes ni cambies cifras. "
    'Devuelve solo JSON: {"message": "..."}.'
)


def _numbers(text: str) -> set[str]:
    return {m.group().replace(",", ".") for m in _NUMBER.finditer(text)}


async def enrich_message(message: str, provider: LLMProvider) -> tuple[str, TriggerSource]:
    """Return (text, source). LLM-rephrased only if safe; deterministic otherwise."""
    if provider.name == "fallback":
        return message, "deterministic"

    cached = await alert_explanation_cache.get(message)
    if cached is not None:
        return cached, "llm"

    result = await provider.complete(_SYSTEM, f"Reescribe sin cambiar ninguna cifra: {message}")
    if not result.ok:
        alert_ai_explanation_failures_total.inc()
        return message, "deterministic"
    try:
        text = json.loads(result.text)["message"]
    except (ValueError, TypeError, KeyError):
        alert_ai_explanation_failures_total.inc()
        return message, "deterministic"
    if not isinstance(text, str) or not text.strip():
        alert_ai_explanation_failures_total.inc()
        return message, "deterministic"

    text = text.strip()[:240]
    if not _numbers(text) <= _numbers(message):  # fabricated/changed figure → reject
        alert_ai_explanation_failures_total.inc()
        return message, "deterministic"

    await alert_explanation_cache.set(message, text)
    return text, "llm"
