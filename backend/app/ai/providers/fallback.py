"""Deterministic no-op provider.

The default when no LLM is configured (or ``LLM_PROVIDER=fallback``). It makes
no network calls and always reports ``ok=False`` with reason ``disabled`` — the
orchestration layer then produces a deterministic explanation from platform
data. This keeps the app and its test suite fully functional with zero LLM
dependency.
"""

from __future__ import annotations

from app.ai.providers.base import LLMResult, ProviderHealth


class FallbackProvider:
    name = "fallback"

    async def complete(self, system: str, user: str) -> LLMResult:
        return LLMResult(ok=False, reason="disabled", provider="fallback")

    async def health_check(self) -> ProviderHealth:
        # Always "healthy": deterministic, no network — the app works regardless.
        return ProviderHealth(provider="fallback", healthy=True, detail="deterministic fallback (no LLM)")
