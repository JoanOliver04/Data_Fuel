"""Tests for get_routing_provider — DISTANCE_MODE → provider mapping.

Confirms backward-compatible selection: EUCLIDEAN and key-less DRIVING both
yield the haversine provider; DRIVING with a key yields the ORS provider.
"""

import pytest

from app.core.config import get_settings
from app.services.routing import HaversineProvider, OrsMatrixProvider, get_routing_provider


def _settings(monkeypatch: pytest.MonkeyPatch, mode: str, ors_key: str) -> object:
    monkeypatch.setenv("DISTANCE_MODE", mode)
    monkeypatch.setenv("ORS_API_KEY", ors_key)
    get_settings.cache_clear()
    return get_settings()


def test_euclidean_mode_returns_haversine_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = get_routing_provider(_settings(monkeypatch, "EUCLIDEAN", "irrelevant"))
    assert isinstance(provider, HaversineProvider)


def test_driving_mode_with_key_returns_ors_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = get_routing_provider(_settings(monkeypatch, "DRIVING", "a-real-key"))
    assert isinstance(provider, OrsMatrixProvider)


def test_driving_mode_without_key_falls_back_to_haversine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = get_routing_provider(_settings(monkeypatch, "DRIVING", ""))
    assert isinstance(provider, HaversineProvider)
