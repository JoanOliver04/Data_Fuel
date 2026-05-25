"""Tests for prompt rendering."""

from app.ai.prompts import (
    PROMPT_VERSION,
    render_chat,
    render_prediction,
    render_recommendation,
    render_trend,
)

FACTS = '{"fuel_type":"gasolina_95","stations":[]}'


def test_prompt_version_is_set() -> None:
    assert PROMPT_VERSION


def test_recommendation_prompt_grounds_in_facts_and_json() -> None:
    system, user = render_recommendation(FACTS)
    assert "FACTS" in user
    assert FACTS in user
    # Anti-hallucination + JSON-only constraints present in the system prompt.
    assert "No inventes" in system
    assert "JSON" in system


def test_prediction_and_trend_prompts_render() -> None:
    s1, u1 = render_prediction(FACTS)
    s2, u2 = render_trend(FACTS)
    assert FACTS in u1 and FACTS in u2
    assert "JSON" in s1 and "JSON" in s2


def test_chat_prompt_embeds_question_as_untrusted() -> None:
    _system, user = render_chat("¿por qué esta estación?", FACTS)
    assert "¿por qué esta estación?" in user
    assert "no fiable" in user  # marked untrusted
