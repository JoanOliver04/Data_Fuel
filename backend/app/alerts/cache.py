"""Short-TTL cache for optional LLM-rephrased alert messages.

Keyed by the deterministic message, so identical alerts reuse one generation
(dedup) and transient provider blips don't re-spend tokens.
"""

from __future__ import annotations

from app.core.cache import TTLCache

alert_explanation_cache: TTLCache[str, str] = TTLCache(ttl_seconds=900.0, name="alerts")
