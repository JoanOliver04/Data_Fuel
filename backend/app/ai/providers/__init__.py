"""LLM provider abstraction: a Protocol plus interchangeable implementations."""

from app.ai.providers.base import LLMProvider, LLMResult
from app.ai.providers.factory import get_llm_provider

__all__ = ["LLMProvider", "LLMResult", "get_llm_provider"]
