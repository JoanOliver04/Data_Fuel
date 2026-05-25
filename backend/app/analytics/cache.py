"""Short-TTL cache for analytics responses (instrumented TTLCache)."""

from __future__ import annotations

from pydantic import BaseModel

from app.core.cache import TTLCache

# TTL matches the Settings default; analytics data refreshes on MITECO sync, so
# a short window keeps payloads fresh while absorbing dashboard request bursts.
analytics_cache: TTLCache[str, BaseModel] = TTLCache(ttl_seconds=300.0, name="analytics")
