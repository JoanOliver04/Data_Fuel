"""Unit tests for app.ml.xai.feature_metadata."""

from __future__ import annotations

import pytest

from app.ml.training.entrenar import FEATURE_COLUMNS
from app.ml.xai.feature_metadata import (
    DEFAULT_LOCALE,
    get_feature_copy,
    supported_locales,
)


def test_known_feature_has_curated_copy() -> None:
    copy = get_feature_copy("precio_semana_anterior", "es")
    assert copy.label == "Precio de la semana anterior"
    assert copy.raises and copy.lowers
    assert copy.label != "precio_semana_anterior"  # not the fallback


def test_unknown_feature_falls_back_to_name() -> None:
    copy = get_feature_copy("totally_new_feature", "es")
    assert copy.label == "totally_new_feature"
    assert "totally_new_feature" in copy.raises


def test_unknown_locale_falls_back_to_default() -> None:
    assert get_feature_copy("mes", "de") == get_feature_copy("mes", DEFAULT_LOCALE)


def test_supported_locales_includes_es_and_en() -> None:
    locales = supported_locales()
    assert "es" in locales
    assert "en" in locales


@pytest.mark.parametrize("locale", ["es", "en"])
@pytest.mark.parametrize("feature", FEATURE_COLUMNS)
def test_every_training_feature_is_curated(feature: str, locale: str) -> None:
    """No training feature should fall back to the raw-name default."""
    copy = get_feature_copy(feature, locale)
    assert copy.label != feature, f"{feature} missing curated label in {locale}"
    assert copy.description
