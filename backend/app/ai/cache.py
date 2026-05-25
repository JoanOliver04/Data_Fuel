"""Async-safe cache for AI explanations.

Reuses the instrumented :class:`TTLCache`. The cache key folds in the prompt
version and the full fact payload (which includes the model version), so a
retrained model or changed prompt naturally produces a new key — old
explanations simply age out, no explicit invalidation needed.
"""

from __future__ import annotations

import hashlib

from app.ai.schemas import AIExplanation, TrendSummary
from app.core.cache import TTLCache

# TTL matches the Settings default; the store bound is fixed at import (fine for
# this traffic profile).
ai_explanation_cache: TTLCache[str, AIExplanation] = TTLCache(
    ttl_seconds=900.0, name="ai_explanations"
)
ai_trend_cache: TTLCache[str, TrendSummary] = TTLCache(
    ttl_seconds=900.0, name="ai_trends"
)


def make_cache_key(*parts: str) -> str:
    """Stable cache key from the given parts (sha256, hex-truncated)."""
    joined = "\x1f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]
