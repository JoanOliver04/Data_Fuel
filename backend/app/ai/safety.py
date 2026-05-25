"""Input safety for the AI layer: sanitisation and prompt-injection mitigation.

User free-text never reaches the model verbatim. We strip control characters,
collapse whitespace, hard-cap length, and neutralise the most common
prompt-injection / role-override patterns. This is defence-in-depth alongside
the structural guarantee that all numbers/verdicts come from platform data, so
even a successful injection cannot fabricate metrics.
"""

from __future__ import annotations

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")

# Patterns that try to override instructions or leak the system prompt.
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+|the\s+)?(previous|above|prior)\s+(instructions|prompts?))"
    r"|(disregard\s+(all\s+|the\s+)?(previous|above|prior))"
    r"|(system\s+prompt)"
    r"|(you\s+are\s+now)"
    r"|(act\s+as\s+(an?\s+)?)"
    r"|(</?\s*system\s*>)"
    r"|(\bBEGIN\s+SYSTEM\b)"
    r"|(```+)",
    re.IGNORECASE,
)

_REDACTION = "[filtered]"


def looks_like_injection(text: str) -> bool:
    """True if the text contains a known prompt-injection / override pattern."""
    return _INJECTION_PATTERNS.search(text) is not None


def sanitize_question(text: str, max_chars: int) -> str:
    """Return a model-safe version of user free-text.

    Strips control chars, neutralises injection patterns, collapses whitespace
    and truncates to ``max_chars``. Never raises.
    """
    cleaned = _CONTROL_CHARS.sub("", text)
    cleaned = _INJECTION_PATTERNS.sub(_REDACTION, cleaned)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip()
    return cleaned
