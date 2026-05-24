"""Production ML lifecycle: artifact versioning, evaluation, activation, history.

This package implements the automated retraining lifecycle for the Random
Forest *recommendation* model (``artifacts/modelo_combustible.pkl`` →
``artifacts/active/model.pkl``). It does NOT touch the on-demand Ridge
``PredictionService`` in ``app.domain.services.prediction_service``, which
trains itself in-memory per request and owns no on-disk artifact.
"""
