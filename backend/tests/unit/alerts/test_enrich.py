"""Anti-hallucination tests for the optional alert-message enrichment seam."""

import json

from app.ai.providers.base import LLMResult
from app.ai.providers.fallback import FallbackProvider
from app.alerts.enrich import enrich_message


class StubProvider:
    name = "stub"

    def __init__(self, text: str, *, ok: bool = True) -> None:
        self._text = text
        self._ok = ok

    async def complete(self, system: str, user: str) -> LLMResult:
        if not self._ok:
            return LLMResult(ok=False, reason="http", provider="stub")
        return LLMResult(ok=True, text=self._text, provider="stub")


async def test_fallback_provider_keeps_deterministic() -> None:
    msg = "Gasolina 95 a 1.43 €/L en Alzira."
    text, source = await enrich_message(msg, FallbackProvider())
    assert text == msg and source == "deterministic"


async def test_valid_rephrase_marked_llm() -> None:
    msg = "Gasolina 95 a 1.41 €/L en Alzira."
    rephrase = json.dumps({"message": "En Alzira, la Gasolina 95 está a 1.41 €/L."})
    text, source = await enrich_message(msg, StubProvider(rephrase))
    assert source == "llm" and "1.41" in text


async def test_fabricated_number_rejected() -> None:
    msg = "Gasolina 95 a 1.42 €/L en Alzira."
    rephrase = json.dumps({"message": "Gasolina 95 a 9.99 €/L en Alzira."})
    text, source = await enrich_message(msg, StubProvider(rephrase))
    assert source == "deterministic" and text == msg


async def test_provider_failure_keeps_deterministic() -> None:
    msg = "Gasolina 95 a 1.40 €/L en Alzira."
    text, source = await enrich_message(msg, StubProvider("", ok=False))
    assert source == "deterministic" and text == msg
