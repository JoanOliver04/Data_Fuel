"""LLM provider contract.

Providers are deliberately dumb: given a system + user message they return a
typed :class:`LLMResult`. They **never raise** — transport, timeout, HTTP and
parse failures all surface as ``ok=False`` with a ``reason``, so the
orchestration layer can degrade gracefully without try/except at every call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

FailureReason = Literal["timeout", "http", "transport", "parse", "disabled"]


@dataclass(frozen=True, slots=True)
class LLMResult:
    """Outcome of one completion request. Success carries ``text`` (raw model
    output, still to be validated); failure carries a ``reason``."""

    ok: bool
    text: str = ""
    reason: FailureReason | None = None
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_s: float = 0.0
    provider: str = "fallback"


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal completion interface every provider implements."""

    name: str

    async def complete(self, system: str, user: str) -> LLMResult:
        """Return a completion for the given system + user messages. Never raises."""
        ...
