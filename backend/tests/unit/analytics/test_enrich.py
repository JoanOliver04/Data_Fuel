"""Unit tests for the optional LLM insight-enrichment seam."""

from app.ai.providers.base import LLMResult
from app.ai.providers.fallback import FallbackProvider
from app.analytics.enrich import enrich_insight
from app.analytics.schemas import Insight


class StubProvider:
    name = "stub"

    def __init__(self, text: str, ok: bool = True) -> None:
        self._text = text
        self._ok = ok

    async def complete(self, system: str, user: str) -> LLMResult:
        if not self._ok:
            return LLMResult(ok=False, reason="http", provider="stub")
        return LLMResult(ok=True, text=self._text, provider="stub")


async def test_fallback_provider_keeps_deterministic() -> None:
    base = Insight(text="Gasolina 95 ha bajado 1.5% esta semana.")
    out = await enrich_insight(base, FallbackProvider())
    assert out is base
    assert out.source == "deterministic"


async def test_valid_rephrase_marked_llm() -> None:
    base = Insight(text="Gasolina 95 ha bajado 1.5% esta semana.")
    rephrase = "Esta semana, la Gasolina 95 cae un 1.5%."
    out = await enrich_insight(base, StubProvider(rephrase))
    assert out.source == "llm"
    assert out.text == rephrase


async def test_fabricated_numbers_rejected() -> None:
    base = Insight(text="Gasolina 95 ha bajado 1.5% esta semana.")
    out = await enrich_insight(base, StubProvider("Gasolina 95 ha bajado 9.9% esta semana."))
    assert out.source == "deterministic"  # 9.9 not in original → rejected
    assert out.text == base.text


async def test_provider_failure_keeps_deterministic() -> None:
    base = Insight(text="Sin cambios relevantes.")
    out = await enrich_insight(base, StubProvider("", ok=False))
    assert out.source == "deterministic"
