"""Optional LLM enrichment seam for analytics insights.

Deterministic insights are the source of truth. This wraps one with an LLM
rephrase **only when explicitly enabled and a provider is available**; any
failure, empty output, or fabricated numbers silently keep the deterministic
text. Analytics therefore never depends on LLM availability.
"""

from __future__ import annotations

import re

from app.ai.providers.base import LLMProvider
from app.analytics.schemas import Insight

_MAX_LEN = 300
_NUMBER = re.compile(r"\d+[.,]?\d*")

_SYSTEM = (
    "Reescribe la siguiente perspectiva de mercado de forma concisa y "
    "profesional. NO inventes datos ni cifras nuevas; conserva exactamente los "
    "números dados. Devuelve solo el texto, sin comillas ni JSON."
)


def _safe(original: str, candidate: str) -> bool:
    """Reject output that introduces numbers not present in the deterministic text."""
    allowed = set(_NUMBER.findall(original))
    return all(n in allowed for n in _NUMBER.findall(candidate))


async def enrich_insight(insight: Insight, provider: LLMProvider) -> Insight:
    """Return an LLM-rephrased insight, or the deterministic one on any issue."""
    if provider.name == "fallback":
        return insight
    result = await provider.complete(_SYSTEM, insight.text)
    if not result.ok:
        return insight
    text = result.text.strip().strip('"')[:_MAX_LEN]
    if not text or not _safe(insight.text, text):
        return insight
    return Insight(text=text, source="llm")
