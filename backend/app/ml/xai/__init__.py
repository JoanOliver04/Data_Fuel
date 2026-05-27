"""Explainable AI (XAI) subsystem for the Random Forest recommendation model.

This package is a read-only observability layer over the already-trained model
(:mod:`app.ml.inference.model_loader`). It never trains, never mutates the
model, and degrades gracefully when its optional dependency (``shap``) is
absent — so importing it can never break the recommendation pipeline.

Modules
-------
``feature_metadata``
    Single source of truth mapping raw training feature names to human-readable
    labels, descriptions, and natural-language reasoning fragments. Locale-keyed
    so the UI copy is multilingual-ready.
``feature_importance_service``
    Global Random Forest feature importance: normalized to percentages, sorted
    descending, cached per loaded artifact.
``shap_explainer``
    Process-singleton :class:`shap.TreeExplainer` producing exact, additive
    per-feature SHAP contributions for a single prediction.
``reasoning_engine``
    Deterministic, template-based natural-language explanation generator. No
    generative AI, no hallucinations.
"""
