"""Versioned, anti-hallucination prompt templates for the AI assistant."""

from app.ai.prompts.templates import (
    PROMPT_VERSION,
    render_chat,
    render_prediction,
    render_recommendation,
    render_trend,
)

__all__ = [
    "PROMPT_VERSION",
    "render_chat",
    "render_prediction",
    "render_recommendation",
    "render_trend",
]
