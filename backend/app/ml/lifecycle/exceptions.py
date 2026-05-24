"""Exception hierarchy for the ML retraining lifecycle.

A single ``RetrainError`` base lets callers (CLI, scheduler job) catch every
recoverable lifecycle failure with one ``except`` and keep the active model
untouched, while the subclasses pinpoint *where* the pipeline stopped.
"""

from __future__ import annotations


class RetrainError(Exception):
    """Base class for every recoverable retraining-lifecycle failure."""


class ArtifactError(RetrainError):
    """Raised for problems reading, writing, or activating model artifacts."""


class VersionNotFoundError(ArtifactError):
    """Raised when a requested artifact version does not exist on disk."""


class InvalidArtifactError(ArtifactError):
    """Raised when an artifact exists but is empty, corrupt, or unloadable."""


class ModelRejectedError(RetrainError):
    """Raised when a freshly trained model fails the acceptance gate.

    Carries the human-readable rejection reason so the caller can log it and
    persist it to the training-run history without re-deriving it.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
