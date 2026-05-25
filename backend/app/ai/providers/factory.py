"""Provider selection from settings.

Returns the configured provider, degrading to the deterministic fallback when
the LLM is disabled or no API key is present — so a misconfigured deployment is
safe by default rather than erroring.
"""

from __future__ import annotations

import logging

from app.ai.providers.base import LLMProvider
from app.ai.providers.fallback import FallbackProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.core.config import Settings

log = logging.getLogger("app.ai.provider")


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Build the LLM provider for the current settings."""
    if not settings.ai_enabled or settings.llm_provider == "fallback":
        return FallbackProvider()
    if settings.llm_provider == "openai":
        if not settings.llm_api_key:
            log.warning("LLM_PROVIDER=openai but LLM_API_KEY is unset — using fallback")
            return FallbackProvider()
        return OpenAICompatibleProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_s=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            max_output_tokens=settings.llm_max_output_tokens,
        )
    return FallbackProvider()
