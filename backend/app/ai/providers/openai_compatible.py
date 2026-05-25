"""OpenAI-compatible chat-completions provider.

Works against any service exposing ``POST {base_url}/chat/completions`` with the
OpenAI schema (OpenAI, Azure OpenAI, OpenRouter, local Ollama, vLLM, …). It is
async, bounded by a wall-clock timeout, retries transient failures, requests a
JSON object response, and — per the contract — never raises: every failure
becomes ``LLMResult(ok=False, reason=...)`` and increments a failure metric.

No secrets live in code: the API key comes from settings/env at call time.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.ai.providers.base import FailureReason, LLMResult
from app.core.metrics import ai_provider_failures_total

log = logging.getLogger("app.ai.provider")

_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_s: float,
        max_retries: int,
        max_output_tokens: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._max_output_tokens = max_output_tokens
        self._client = client  # injected (tests) → not closed here

    def _fail(self, reason: FailureReason, error: str, latency: float) -> LLMResult:
        ai_provider_failures_total.labels(provider=self.name, reason=reason).inc()
        log.warning("LLM provider failure: reason=%s error=%s", reason, error)
        return LLMResult(
            ok=False, reason=reason, error=error, latency_s=latency, provider=self.name
        )

    async def complete(self, system: str, user: str) -> LLMResult:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
            "max_tokens": self._max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        start = time.perf_counter()

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._post(payload, headers)
            except (TimeoutError, httpx.TimeoutException) as exc:
                if attempt < self._max_retries:
                    continue
                return self._fail("timeout", str(exc), time.perf_counter() - start)
            except httpx.HTTPError as exc:
                return self._fail("transport", str(exc), time.perf_counter() - start)

            if response.status_code in _RETRYABLE_STATUSES and attempt < self._max_retries:
                continue
            if response.status_code >= 400:
                return self._fail(
                    "http", f"HTTP {response.status_code}", time.perf_counter() - start
                )
            return self._parse(response, time.perf_counter() - start)

        return self._fail("timeout", "retries exhausted", time.perf_counter() - start)

    async def _post(self, payload: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
        """POST under a hard wall-clock timeout, reusing an injected client if given."""
        if self._client is not None:
            return await asyncio.wait_for(
                self._client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                ),
                timeout=self._timeout_s,
            )
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            return await asyncio.wait_for(
                client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                ),
                timeout=self._timeout_s,
            )

    def _parse(self, response: httpx.Response, latency: float) -> LLMResult:
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            return self._fail("parse", str(exc), latency)
        return LLMResult(
            ok=True,
            text=str(text),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            latency_s=latency,
            provider=self.name,
        )
