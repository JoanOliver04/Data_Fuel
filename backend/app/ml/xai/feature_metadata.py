"""Human-readable metadata for the Random Forest training features.

This is the single source of truth that turns the model's raw, engineered
feature names (``precio_semana_anterior``, ``municipio_enc``, …) into copy a
non-technical user can understand — labels, descriptions, and the directional
sentence fragments the :mod:`reasoning_engine` stitches into prose.

The structure is **locale-keyed** so the platform is multilingual-ready: today
only Spanish (``"es"``) is fully populated (the product is Spanish), and
``"en"`` ships as a complete parallel set so adding a language is purely
additive — no code path changes, only a new dict entry.

Feature names mirror ``FEATURE_COLUMNS`` in
:mod:`app.ml.training.entrenar` exactly; the metadata maps are keyed by those
names. ``año`` carries the accented spelling the trainer persists.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LOCALE = "es"


@dataclass(frozen=True)
class FeatureCopy:
    """Display copy for one feature in one locale.

    ``raises`` / ``lowers`` are clause fragments describing what it means when
    that feature pushes the predicted next-week price **up** or **down**
    respectively. They are written to read naturally after a connective such as
    "porque" / "because", e.g. "el precio de la semana pasada empuja al alza".
    """

    label: str
    description: str
    raises: str
    lowers: str


# ── Spanish (default) ───────────────────────────────────────────────────────

_ES: dict[str, FeatureCopy] = {
    "distancia": FeatureCopy(
        label="Distancia a la estación",
        description="Distancia geodésica (km) desde el punto de referencia hasta la estación.",
        raises="la ubicación de la estación se asocia a precios más altos",
        lowers="la ubicación de la estación se asocia a precios más bajos",
    ),
    "tipo_combustible": FeatureCopy(
        label="Tipo de combustible",
        description="Carburante consultado (gasolina 95/98, gasóleo A/premium).",
        raises="este tipo de combustible tiende a encarecerse",
        lowers="este tipo de combustible tiende a abaratarse",
    ),
    "dia_de_la_semana": FeatureCopy(
        label="Día de la semana",
        description="Día en que se consulta (lunes a domingo).",
        raises="el día de la semana presiona el precio al alza",
        lowers="el día de la semana presiona el precio a la baja",
    ),
    "es_festivo": FeatureCopy(
        label="Festivo o fin de semana",
        description="Indica si la fecha es festivo nacional o fin de semana.",
        raises="ser festivo o fin de semana encarece el carburante",
        lowers="no ser festivo abarata el carburante",
    ),
    "precio_semana_anterior": FeatureCopy(
        label="Precio de la semana anterior",
        description="Precio medio del municipio hace siete días (lag temporal).",
        raises="el precio de la semana pasada venía al alza",
        lowers="el precio de la semana pasada venía a la baja",
    ),
    "tendencia_ultimos_30_dias": FeatureCopy(
        label="Tendencia de 30 días",
        description="Desviación del precio actual frente a su media móvil de 30 días.",
        raises="la tendencia de los últimos 30 días es ascendente",
        lowers="la tendencia de los últimos 30 días es descendente",
    ),
    "is_low_cost": FeatureCopy(
        label="Estación low-cost",
        description="La marca pertenece a operadores de bajo coste (Plenoil, Petroprix…).",
        raises="el perfil de marca empuja el precio al alza",
        lowers="el perfil low-cost empuja el precio a la baja",
    ),
    "mes": FeatureCopy(
        label="Mes del año",
        description="Estacionalidad mensual del mercado del petróleo.",
        raises="la estacionalidad del mes presiona al alza",
        lowers="la estacionalidad del mes presiona a la baja",
    ),
    "precio_medio_municipio": FeatureCopy(
        label="Precio medio del municipio",
        description="Media diaria de precios del municipio para ese carburante.",
        raises="la media del municipio está alta",
        lowers="la media del municipio está baja",
    ),
    "es_autopista": FeatureCopy(
        label="Estación en autopista",
        description="La estación está junto a autopista o carretera principal.",
        raises="la ubicación en vía rápida encarece el precio",
        lowers="no estar en vía rápida abarata el precio",
    ),
    "precio_vs_media_comarca": FeatureCopy(
        label="Precio frente a la comarca",
        description="Diferencia entre el precio actual y la media de la comarca.",
        raises="el precio está por encima de la media de la comarca",
        lowers="el precio está por debajo de la media de la comarca",
    ),
    "momentum_7d": FeatureCopy(
        label="Momentum de 7 días",
        description="Velocidad del precio en la última semana (variación a 7 días).",
        raises="el momentum semanal es positivo (acelerando)",
        lowers="el momentum semanal es negativo (desacelerando)",
    ),
    "año": FeatureCopy(
        label="Año",
        description="Año natural de la observación (deriva macroeconómica).",
        raises="el contexto anual presiona al alza",
        lowers="el contexto anual presiona a la baja",
    ),
    "municipio_enc": FeatureCopy(
        label="Municipio",
        description="Municipio de la estación (codificado para el modelo).",
        raises="el municipio se asocia a precios más altos",
        lowers="el municipio se asocia a precios más bajos",
    ),
    "comarca_enc": FeatureCopy(
        label="Comarca",
        description="Comarca de la estación (codificada para el modelo).",
        raises="la comarca se asocia a precios más altos",
        lowers="la comarca se asocia a precios más bajos",
    ),
}


# ── English (parallel set; multilingual-ready) ──────────────────────────────

_EN: dict[str, FeatureCopy] = {
    "distancia": FeatureCopy(
        label="Distance to station",
        description="Geodesic distance (km) from the reference point to the station.",
        raises="the station's location is associated with higher prices",
        lowers="the station's location is associated with lower prices",
    ),
    "tipo_combustible": FeatureCopy(
        label="Fuel type",
        description="Fuel queried (petrol 95/98, diesel A/premium).",
        raises="this fuel type tends to get more expensive",
        lowers="this fuel type tends to get cheaper",
    ),
    "dia_de_la_semana": FeatureCopy(
        label="Day of week",
        description="Day the query is made (Monday-Sunday).",
        raises="the day of week pushes the price up",
        lowers="the day of week pushes the price down",
    ),
    "es_festivo": FeatureCopy(
        label="Holiday or weekend",
        description="Whether the date is a national holiday or weekend.",
        raises="being a holiday or weekend raises the price",
        lowers="being a regular weekday lowers the price",
    ),
    "precio_semana_anterior": FeatureCopy(
        label="Last week's price",
        description="Municipality average price seven days ago (time lag).",
        raises="last week's price was trending up",
        lowers="last week's price was trending down",
    ),
    "tendencia_ultimos_30_dias": FeatureCopy(
        label="30-day trend",
        description="Deviation of the current price from its 30-day moving average.",
        raises="the 30-day trend is rising",
        lowers="the 30-day trend is falling",
    ),
    "is_low_cost": FeatureCopy(
        label="Low-cost station",
        description="Brand belongs to discount operators (Plenoil, Petroprix…).",
        raises="the brand profile pushes the price up",
        lowers="the low-cost profile pushes the price down",
    ),
    "mes": FeatureCopy(
        label="Month",
        description="Monthly seasonality of the oil market.",
        raises="the month's seasonality pushes up",
        lowers="the month's seasonality pushes down",
    ),
    "precio_medio_municipio": FeatureCopy(
        label="Municipality average price",
        description="Daily mean price in the municipality for this fuel.",
        raises="the municipality average is high",
        lowers="the municipality average is low",
    ),
    "es_autopista": FeatureCopy(
        label="Highway station",
        description="The station sits on a motorway or main road.",
        raises="the highway location raises the price",
        lowers="not being on a highway lowers the price",
    ),
    "precio_vs_media_comarca": FeatureCopy(
        label="Price vs. comarca",
        description="Difference between the current price and the comarca average.",
        raises="the price is above the comarca average",
        lowers="the price is below the comarca average",
    ),
    "momentum_7d": FeatureCopy(
        label="7-day momentum",
        description="Price velocity over the last week (7-day change).",
        raises="weekly momentum is positive (accelerating)",
        lowers="weekly momentum is negative (decelerating)",
    ),
    "año": FeatureCopy(
        label="Year",
        description="Calendar year of the observation (macroeconomic drift).",
        raises="the yearly context pushes up",
        lowers="the yearly context pushes down",
    ),
    "municipio_enc": FeatureCopy(
        label="Municipality",
        description="Station municipality (encoded for the model).",
        raises="the municipality is associated with higher prices",
        lowers="the municipality is associated with lower prices",
    ),
    "comarca_enc": FeatureCopy(
        label="Comarca",
        description="Station comarca (encoded for the model).",
        raises="the comarca is associated with higher prices",
        lowers="the comarca is associated with lower prices",
    ),
}


_LOCALES: dict[str, dict[str, FeatureCopy]] = {"es": _ES, "en": _EN}


def _fallback_copy(feature: str) -> FeatureCopy:
    """A safe default for a feature with no curated copy (forward-compatible)."""
    return FeatureCopy(
        label=feature,
        description=feature,
        raises=f"'{feature}' pushes the price up",
        lowers=f"'{feature}' pushes the price down",
    )


def get_feature_copy(feature: str, locale: str = DEFAULT_LOCALE) -> FeatureCopy:
    """Return display copy for ``feature`` in ``locale`` (falls back gracefully).

    Unknown locales fall back to :data:`DEFAULT_LOCALE`; unknown features (e.g.
    a future schema addition) return a neutral default so the XAI layer never
    raises ``KeyError`` on a model trained with extra columns.
    """
    table = _LOCALES.get(locale, _LOCALES[DEFAULT_LOCALE])
    return table.get(feature) or _fallback_copy(feature)


def supported_locales() -> tuple[str, ...]:
    """Locales with a curated copy table."""
    return tuple(_LOCALES.keys())
