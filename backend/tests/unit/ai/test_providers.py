"""Tests for the LLM provider abstraction."""

import json

import httpx

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
