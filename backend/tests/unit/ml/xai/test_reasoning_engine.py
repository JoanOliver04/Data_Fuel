"""Unit tests for app.ml.xai.reasoning_engine."""

from __future__ import annotations

from app.ml.xai import reasoning_engine as re
from app.ml.xai.shap_explainer import ShapContribution


def _c(feature: str, impact: float) -> ShapContribution:
    return ShapContribution(feature=feature, impact=impact)


def test_wait_uses_lowering_factors() -> None:
    contribs = [
        _c("precio_semana_anterior", -0.04),
        _c("momentum_7d", -0.02),
        _c("mes", 0.01),  # raises — should be ignored for an ESPERA verdict
    ]
    text = re.generate(
        veredicto="ESPERA", variacion_pct=-2.5, contributions=contribs, locale="es"
    )
    assert "bajará" in text
    assert "2.5%" in text
    # A lowering fragment of the strongest factor appears.
    assert "semana pasada venía a la baja" in text
    # The raising factor must not be cited.
    assert "estacionalidad del mes" not in text


def test_refuel_uses_raising_factors() -> None:
    contribs = [_c("precio_medio_municipio", 0.05), _c("año", 0.02)]
    text = re.generate(
        veredicto="REPOSTA AHORA", variacion_pct=3.1, contributions=contribs, locale="es"
    )
    assert "subirá" in text
    assert "media del municipio está alta" in text


def test_neutral_when_no_supporting_factors() -> None:
    # ESPERA but every meaningful factor raises the price -> no support.
    contribs = [_c("mes", 0.03), _c("año", 0.02)]
    text = re.generate(
        veredicto="ESPERA", variacion_pct=-0.1, contributions=contribs, locale="es"
    )
    assert "no prevé cambios" in text.lower() or "no encuentra factores" in text.lower()


def test_tiny_impacts_are_filtered_as_noise() -> None:
    contribs = [_c("precio_semana_anterior", -1e-6)]
    text = re.generate(
        veredicto="ESPERA", variacion_pct=-0.05, contributions=contribs, locale="es"
    )
    assert "no prevé cambios" in text.lower()


def test_max_factors_caps_bullets() -> None:
    contribs = [_c(f"f{i}", -(0.1 - i * 0.001)) for i in range(10)]
    text = re.generate(
        veredicto="ESPERA", variacion_pct=-2.0, contributions=contribs, locale="es",
        max_factors=2,
    )
    assert text.count("\n- ") == 2


def test_fallback_lists_global_features() -> None:
    text = re.generate_fallback(
        veredicto="ESPERA",
        variacion_pct=-1.0,
        top_features=["precio_semana_anterior", "precio_medio_municipio"],
        locale="es",
    )
    assert "no está disponible" in text
    assert "Precio de la semana anterior" in text
    assert "Precio medio del municipio" in text


def test_fallback_without_features() -> None:
    text = re.generate_fallback(
        veredicto="REPOSTA AHORA", variacion_pct=2.0, top_features=[], locale="es"
    )
    assert text.endswith(".")
    assert "\n-" not in text


def test_english_locale() -> None:
    contribs = [_c("precio_semana_anterior", -0.04)]
    text = re.generate(
        veredicto="ESPERA", variacion_pct=-2.0, contributions=contribs, locale="en"
    )
    assert "worth waiting" in text
    assert "last week's price was trending down" in text
