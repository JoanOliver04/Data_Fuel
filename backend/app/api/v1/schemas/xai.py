"""API schemas for the Explainable AI (XAI) endpoints.

These mirror the dataclasses produced by :mod:`app.ml.xai` but live at the API
boundary as strict Pydantic models, so the OpenAPI contract is explicit and the
service layer stays framework-agnostic.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Direction of a feature's local effect on the predicted next-week price.
#   "lowers" → negative SHAP impact (good news for "ESPERA"); render green.
#   "raises" → positive SHAP impact (price goes up); render red.
ImpactDirection = Literal["lowers", "raises"]


class FeatureImportanceItem(BaseModel):
    """One feature's global (model-wide) importance, as a percentage 0-100."""

    feature: str = Field(description="Raw training feature name")
    display_name: str = Field(description="Human-readable label")
    description: str = Field(description="Plain-language description of the feature")
    importance: float = Field(description="Normalized importance percentage (Σ ≈ 100)")


class GlobalFeatureImportanceResponse(BaseModel):
    """Global feature importance plus the active model's metadata."""

    features: list[FeatureImportanceItem]
    feature_count: int
    model_trained_at: str | None = None
    model_version: str | None = None
    model_r2: float | None = None
    model_mae: float | None = None


class ShapFactor(BaseModel):
    """One feature's signed local SHAP contribution to a single prediction."""

    feature: str
    display_name: str
    impact: float = Field(description="Signed SHAP value in €/L (negative lowers price)")
    direction: ImpactDirection


class ExplainRecommendationResponse(BaseModel):
    """Full local explanation for one refuel recommendation.

    ``top_positive_factors`` are the strongest price-**lowering** factors
    (negative impact — they favour the "ESPERA" verdict); ``top_negative_factors``
    are the strongest price-**raising** factors (positive impact). Both are
    capped at five. ``feature_importance_local`` is the complete signed
    attribution, ordered by absolute impact, for the visual impact list.

    When SHAP is unavailable (optional dependency missing, or explainer build
    failed) ``shap_available`` is ``false``, the local lists are empty, and
    ``reasoning`` falls back to the model's global top features — the endpoint
    never errors on that account.
    """

    veredicto: Literal["REPOSTA AHORA", "ESPERA"]
    prediction: float = Field(description="Predicted next-week price (€/L)")
    base_value: float = Field(description="SHAP base value: model's mean output (€/L)")
    precio_actual: float
    variacion_pct: float
    confidence: float = Field(description="Model confidence (time-split R²), 0-1")
    reasoning: str
    shap_available: bool
    top_positive_factors: list[ShapFactor]
    top_negative_factors: list[ShapFactor]
    feature_importance_local: list[ShapFactor]
    feature_importance_global: list[FeatureImportanceItem]
