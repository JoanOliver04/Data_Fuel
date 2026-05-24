"""CLI: activate a specific archived model version (manual promotion / rollback).

    python -m app.ml.training.activate --version 2026-05-24T03-00-00

Atomically swaps ``artifacts/active`` to the requested version and records the
action in the training-run history. NOTE: this updates the on-disk active
model; a already-running API process keeps its in-memory model until it
restarts (or until the in-process scheduler reloads on its next retrain).

Exit codes:
    0  activated
    1  error (version missing / empty / activation failed)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import UTC, datetime

from app.ml.lifecycle.exceptions import ArtifactError
from app.ml.lifecycle.history import TrainingRunRecord, TrainingRunStatus
from app.ml.lifecycle.versioning import ArtifactStore
from app.repositories.training_run_repository import TrainingRunRepository

log = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Activate an archived model version.")
    parser.add_argument(
        "--version",
        type=str,
        required=True,
        help="Archived version id to activate (e.g. 2026-05-24T03-00-00).",
    )
    return parser.parse_args()


async def _record_activation(store: ArtifactStore, version: str) -> None:
    """Best-effort history entry for a manual activation."""
    from app.infrastructure.database.session import get_session_factory

    metrics = store.read_metrics(version)
    moment = datetime.now(UTC)
    record = TrainingRunRecord(
        status=TrainingRunStatus.ACTIVATED,
        started_at=moment,
        finished_at=moment,
        duration_seconds=0.0,
        version=version,
        mae=metrics.get("mae"),
        rmse=metrics.get("rmse"),
        r2=metrics.get("r2"),
        r2_oob=metrics.get("r2_oob"),
        reason="manual activation via CLI",
    )
    try:
        factory = get_session_factory()
        async with factory() as session:
            await TrainingRunRepository(session).record(record)
            await session.commit()
    except Exception:
        log.exception("Failed to record manual activation in history (non-fatal)")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    args = _parse_args()
    store = ArtifactStore()

    try:
        store.activate(args.version)
    except ArtifactError as exc:
        log.error("Activation failed: %s", exc)
        return 1

    asyncio.run(_record_activation(store, args.version))
    log.info(
        "Activated version=%s. Restart the API (or wait for the next in-process "
        "retrain) to load it into a running server.",
        args.version,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
