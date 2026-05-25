"""Provider selection from settings.

A small **preset registry** maps each supported provider id to its base URL,
default model and whether it needs an API key. One OpenAI-compatible transport
serves them all (OpenRouter, Groq, Ollama, OpenAI); only the preset differs.
Anything misconfigured — disabled, unknown id, missing key — degrades to the
deterministic fallback, so a deployment is safe by default rather than erroring.

Adding Anthropic later: implement a provider class for its native API and route
to it here; the orchestration layer is unaffected (same Protocol).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.ai.providers.base import LLMProvider
from app.ai.providers.fallback import FallbackProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.core.config import Settings

log = logging.getLogger("app.ai.provider")


@dataclass(frozen=True, slots=True)
class _Preset:
    base_url: str
    default_model: str
    requires_key: bool


# OpenAI-compatible presets. OpenRouter is the recommended production default.
_PRESETS: dict[str, _Preset] = {
    "openrouter": _Preset("https://openrouter.ai/api/v1", "deepseek/deepseek-chat", True),
    "groq": _Preset("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", True),
    "ollama": _Preset("http://localhost:11434/v1", "llama3.1", False),
    "openai": _Preset("https://api.openai.com/v1", "gpt-4o-mini", True),
}

# Provider-specific API key, falling back to the generic LLM_API_KEY.
_KEY_GETTERS: dict[str, Callable[[Settings], str | None]] = {
    "openrouter": lambda s: s.openrouter_api_key,
    "groq": lambda s: s.groq_api_key,
}

# Reserved: recognised by config but not yet implemented (native API, not
# OpenAI-compatible). Degrades to fallback until a provider class is added.
_RESERVED = frozenset({"anthropic"})


def _resolve_key(settings: Settings, provider: str) -> str | None:
    getter = _KEY_GETTERS.get(provider)
    specific = getter(settings) if getter is not None else None
    return specific or settings.llm_api_key


def _resolve_model(settings: Settings, provider: str, preset: _Preset) -> str:
    if settings.llm_model:  # explicit generic override wins
        return settings.llm_model
    if provider == "openrouter":
        return settings.openrouter_model
    return preset.default_model


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Build the LLM provider for the current settings, degrading to fallback."""
    provider = settings.llm_provider
    if not settings.ai_enabled or provider == "fallback":
        return FallbackProvider()
    if provider in _RESERVED:
        log.warning("LLM_PROVIDER=%s is not yet implemented — using fallback", provider)
        return FallbackProvider()

    preset = _PRESETS.get(provider)
    if preset is None:
        log.warning("Unknown LLM_PROVIDER=%s — using fallback", provider)
        return FallbackProvider()

    api_key = _resolve_key(settings, provider)
    if preset.requires_key and not api_key:
        log.warning("LLM_PROVIDER=%s but no API key set — using fallback", provider)
        return FallbackProvider()

    return OpenAICompatibleProvider(
        name=provider,
        api_key=api_key or "",
        base_url=settings.llm_base_url or preset.base_url,
        model=_resolve_model(settings, provider, preset),
        timeout_s=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        max_output_tokens=settings.llm_max_output_tokens,
    )
