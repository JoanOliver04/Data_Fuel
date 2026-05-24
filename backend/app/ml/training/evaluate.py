"""CLI: evaluate an archived model version against the active model.

    python -m app.ml.training.evaluate [--version VERSION]

Read-only: never activates anything. Defaults to the latest archived version.

Exit codes:
    0  candidate would be accepted by the gate
    2  candidate would be rejected
    1  error (no such version / no archived versions)
"""

from __future__ import annotations

import argparse
import logging

from app.core.config import get_settings
from app.ml.lifecycle.evaluation import evaluate_candidate
from app.ml.lifecycle.pipeline import thresholds_from_settings
from app.ml.lifecycle.versioning import ArtifactStore

log = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an archived model version.")
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help="Archived version id to evaluate (default: latest archived).",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    args = _parse_args()
    store = ArtifactStore()

    version = args.version or store.latest_version()
    if version is None:
        log.error("No archived versions to evaluate.")
        return 1
    if version not in store.list_versions():
        log.error("Version %r not found in archive.", version)
        return 1

    candidate = store.read_metrics(version)
    baseline = store.read_active_metrics()
    decision = evaluate_candidate(candidate, baseline, thresholds_from_settings(get_settings()))

    log.info(
        "Evaluation: version=%s accepted=%s reason=%s",
        version,
        decision.accepted,
        decision.reason,
    )
    return 0 if decision.accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
