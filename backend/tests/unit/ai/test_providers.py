"""Tests for the LLM provider abstraction."""

import json

import httpx
import pytest

from app.ai.providers.base import LLMProvider
from app.ai.providers.factory import get_llm_provider
from app.ai.providers.fallback import FallbackProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.core.config import Settings


def _provider(handler: httpx.MockTransport) -> OpenAICompatibleProvider:
    client = httpx.AsyncClient(base_url="http://llm.test", transport=handler)
    return OpenAICompatibleProvider(
        api_key="sk-test", base_url="http://llm.test", model="m",
        timeout_s=1.0, max_retries=0, max_output_tokens=100, client=client,
    )


async def test_fallback_provider_never_calls_and_reports_disabled() -> None:
    result = await FallbackProvider().complete("s", "u")
    assert result.ok is False
    assert result.reason == "disabled"


def test_factory_defaults_to_fallback_without_key() -> None:
    settings = Settings(llm_provider="openai", llm_api_key=None)
    assert isinstance(get_llm_provider(settings), FallbackProvider)
    assert isinstance(get_llm_provider(settings), LLMProvider)


def test_factory_returns_openai_when_configured() -> None:
    settings = Settings(llm_provider="openai", llm_api_key="sk-x")
    assert isinstance(get_llm_provider(settings), OpenAICompatibleProvider)


async def test_openai_provider_success_parses_text_and_tokens() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps({"summary": "ok"})}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 22},
            },
        )

    result = await _provider(httpx.MockTransport(handler)).complete("s", "u")
    assert result.ok is True
    assert json.loads(result.text)["summary"] == "ok"
    assert result.prompt_tokens == 11


async def test_openai_provider_http_error_degrades() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    result = await _provider(httpx.MockTransport(handler)).complete("s", "u")
    assert result.ok is False
    assert result.reason == "http"


async def test_openai_provider_timeout_degrades() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=req)

    result = await _provider(httpx.MockTransport(handler)).complete("s", "u")
    assert result.ok is False
    assert result.reason == "timeout"


# ── Multi-provider preset selection ───────────────────────────────────────────


def _settings(**overrides: object) -> Settings:
    """Hermetic Settings: ignore the dev .env and start with no keys, so factory
    selection depends only on the explicit overrides."""
    base: dict[str, object] = {"llm_api_key": None, "openrouter_api_key": None, "groq_api_key": None}
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[call-arg]


def test_factory_openrouter_uses_preset_and_deepseek_default() -> None:
    provider = get_llm_provider(_settings(llm_provider="openrouter", openrouter_api_key="sk-or"))
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.name == "openrouter"
    assert provider._model == "deepseek/deepseek-chat"
    assert "openrouter.ai" in provider._base_url


def test_factory_groq_uses_preset() -> None:
    provider = get_llm_provider(_settings(llm_provider="groq", groq_api_key="gk"))
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.name == "groq"
    assert "groq.com" in provider._base_url


def test_factory_ollama_needs_no_key() -> None:
    provider = get_llm_provider(_settings(llm_provider="ollama"))
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.name == "ollama"
    assert "11434" in provider._base_url


def test_factory_openrouter_without_key_degrades() -> None:
    assert isinstance(get_llm_provider(_settings(llm_provider="openrouter")), FallbackProvider)


def test_factory_anthropic_is_reserved_and_degrades() -> None:
    settings = _settings(llm_provider="anthropic", llm_api_key="sk-x")
    assert isinstance(get_llm_provider(settings), FallbackProvider)


def test_factory_generic_overrides_win() -> None:
    provider = get_llm_provider(_settings(
        llm_provider="openrouter", openrouter_api_key="sk-or",
        llm_base_url="http://local/v1", llm_model="my-model",
    ))
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider._base_url == "http://local/v1"
    assert provider._model == "my-model"


def test_datafuel_llm_provider_alias_and_openrouter_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAFUEL_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    monkeypatch.setenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.llm_provider == "openrouter"
    assert settings.openrouter_api_key == "sk-or"
    assert settings.openrouter_model == "deepseek/deepseek-chat"


# ── Health checks ─────────────────────────────────────────────────────────────


async def test_health_check_ok() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    health = await _provider(httpx.MockTransport(handler)).health_check()
    assert health.healthy is True
    assert health.provider == "openai"


async def test_health_check_http_error() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={})

    health = await _provider(httpx.MockTransport(handler)).health_check()
    assert health.healthy is False


async def test_fallback_health_is_healthy() -> None:
    health = await FallbackProvider().health_check()
    assert health.healthy is True
    assert health.provider == "fallback"
