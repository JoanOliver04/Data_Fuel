"""CLI: run the full retraining pipeline once.

    python -m app.ml.training.retrain

Exit codes:
    0  model retrained and activated
    2  model trained but rejected by the acceptance gate (active model kept)
    1  pipeline failed (export/training/activation error)
"""

from __future__ import annotations

import asyncio
import logging

from app.ml.lifecycle.history import TrainingRunStatus
from app.ml.lifecycle.pipeline import RetrainPipeline

log = logging.getLogger(__name__)

_EXIT_CODES = {
    TrainingRunStatus.ACTIVATED: 0,
    TrainingRunStatus.REJECTED: 2,
    TrainingRunStatus.FAILED: 1,
}


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    outcome = asyncio.run(RetrainPipeline().run())
    log.info(
        "Retrain finished: status=%s version=%s duration=%.1fs reason=%s",
        outcome.status.value,
        outcome.version,
        outcome.duration_seconds,
        outcome.reason,
    )
    return _EXIT_CODES[outcome.status]


if __name__ == "__main__":
    raise SystemExit(main())
