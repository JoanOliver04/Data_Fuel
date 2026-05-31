#!/usr/bin/env python
"""Create a deployment-sized SQLite slice for the demo image.

DEPLOYMENT ASSET ONLY. This is a pure ``sqlite3`` data-copy utility: it does not
import, read, or modify any business / ML / API code. It produces a small,
self-contained database for the demo container.

What it keeps
-------------
* **All** stations  → full geographic / station coverage is preserved.
* **All** ``alembic_version`` rows → the slice reports the same migration head,
  so the app's startup ``alembic upgrade head`` is a no-op (no surprise migration).
* The **last N days** of ``price_history`` (default 40). That window covers
  every lookback the inference/feature layer needs:
    - the 30-day municipio trend window (``_TREND_WINDOW_DAYS = 30``),
    - the 7-day price lag,
  plus enough range for analytics trends, XAI and the recommendation engine.
* Other tables (``vehicle_profiles``, ``training_runs``, ``alerts``,
  ``notifications``) are created empty — none are required for read endpoints,
  and the model loads from the ``.pkl`` artifact, not from ``training_runs``.

Usage (run from backend/):
    python scripts/make_demo_slice.py                 # 40-day slice → data/datafuel.db
    python scripts/make_demo_slice.py --days 30       # smaller slice
    python scripts/make_demo_slice.py --src ./datafuel.db --dst ./data/datafuel.db
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # backend/
DEFAULT_SRC = ROOT / "datafuel.db"
DEFAULT_DST = ROOT / "data" / "datafuel.db"


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a demo-sized SQLite slice.")
    ap.add_argument("--src", default=str(DEFAULT_SRC), help="source full DB")
    ap.add_argument("--dst", default=str(DEFAULT_DST), help="destination slice DB")
    ap.add_argument("--days", type=int, default=40, help="days of price_history to keep")
    args = ap.parse_args()

    src_path = Path(args.src)
    dst_path = Path(args.dst)
    if not src_path.exists():
        raise SystemExit(f"source DB not found: {src_path}")
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    if dst_path.exists():
        dst_path.unlink()

    src = sqlite3.connect(str(src_path))
    max_recorded = src.execute("SELECT MAX(recorded_at) FROM price_history").fetchone()[0]
    cutoff = (
        datetime.fromisoformat(max_recorded) - timedelta(days=args.days)
    ).strftime("%Y-%m-%d %H:%M:%S")

    # Copy CREATE TABLE statements first; defer indexes until after bulk insert
    # so the load is not slowed by index maintenance per row.
    tables = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' AND sql IS NOT NULL"
    ).fetchall()
    indexes = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' "
        "AND name NOT LIKE 'sqlite_%' AND sql IS NOT NULL"
    ).fetchall()

    dst = sqlite3.connect(str(dst_path))
    for (sql,) in tables:
        dst.execute(sql)
    dst.commit()
    dst.close()

    # Copy data through an ATTACH so it stays a single streaming SQL operation.
    src.execute(f"ATTACH DATABASE '{dst_path.as_posix()}' AS dst")
    src.execute("BEGIN")
    src.execute("INSERT INTO dst.stations SELECT * FROM stations")
    src.execute("INSERT INTO dst.alembic_version SELECT * FROM alembic_version")
    src.execute(
        "INSERT INTO dst.price_history SELECT * FROM price_history WHERE recorded_at >= ?",
        (cutoff,),
    )
    src.execute("COMMIT")
    src.execute("DETACH DATABASE dst")
    src.close()

    # Recreate indexes and compact the file to its minimum on-disk footprint.
    dst = sqlite3.connect(str(dst_path))
    for (sql,) in indexes:
        dst.execute(sql)
    dst.commit()
    dst.execute("VACUUM")
    dst.commit()

    n_st = dst.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    n_ph = dst.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]
    lo, hi = dst.execute("SELECT MIN(recorded_at), MAX(recorded_at) FROM price_history").fetchone()
    dst.close()

    size_mb = dst_path.stat().st_size / 1_000_000
    print(
        f"slice written: {dst_path}\n"
        f"  cutoff        : {cutoff}\n"
        f"  stations      : {n_st:,}\n"
        f"  price_history : {n_ph:,}\n"
        f"  date range    : {lo}  ->  {hi}\n"
        f"  file size     : {size_mb:.0f} MB"
    )


if __name__ == "__main__":
    main()
