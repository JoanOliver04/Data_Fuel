"""Analytics services — shape repository aggregates into DTOs.

Pure compute: services take a session, run windowed aggregations, fold
municipality rows into comarcas, derive deltas/directions, and attach a
deterministic insight. Caching, metrics and HTTP concerns live in the endpoints.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import insights
from app.analytics.comarcas import comarca_of
from app.analytics.repositories.analytics_repository import (
    AnalyticsRepository,
    GroupStatRow,
    LabeledTrendRow,
)
from app.analytics.schemas import (
    BrandsOut,
    BrandStat,
    ComarcasOut,
    ComarcaStat,
    Direction,
    GroupBy,
    HeatmapOut,
    HeatmapPoint,
    InsightsOut,
    OverviewOut,
    TimeRange,
    TrendPoint,
    TrendSeries,
    TrendsOut,
)
from app.core.metrics import analytics_heavy_queries_total
from app.infrastructure.database.dialects import Granularity

log = logging.getLogger("app.analytics")

_RANGE_DELTA: dict[TimeRange, timedelta] = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "1y": timedelta(days=365),
}
_OVERVIEW_FUEL = "gasolina_95"
_MAX_GROUPED_SERIES = 6
_HEAVY_ROW_THRESHOLD = 5000


def _window(rng: TimeRange) -> tuple[datetime, datetime, datetime]:
    """Return (start, end, prev_start) as naive UTC, matching stored timestamps."""
    end = datetime.now(UTC).replace(tzinfo=None)
    delta = _RANGE_DELTA[rng]
    start = end - delta
    return start, end, start - delta


def _bucket_granularity(rng: TimeRange) -> Granularity:
    return "hour" if rng == "24h" else "day"


def _direction(delta_pct: float | None) -> Direction:
    if delta_pct is None:
        return "STABLE"
    if delta_pct <= -0.3:
        return "DOWN"
    if delta_pct >= 0.3:
        return "UP"
    return "STABLE"


@dataclass
class _Acc:
    wsum: float = 0.0
    n: int = 0
    pmin: float = math.inf
    pmax: float = -math.inf
    stations: int = 0

    @property
    def avg(self) -> float:
        return self.wsum / self.n if self.n else 0.0


def _fold_to_comarca(rows: list[GroupStatRow]) -> dict[str, _Acc]:
    """Aggregate municipality-level rows into comarcas (sample-count weighted)."""
    acc: dict[str, _Acc] = {}
    for r in rows:
        comarca = comarca_of(r.key)
        if comarca is None:
            continue
        a = acc.setdefault(comarca, _Acc())
        a.wsum += r.avg * r.sample_count
        a.n += r.sample_count
        a.pmin = min(a.pmin, r.min)
        a.pmax = max(a.pmax, r.max)
        a.stations += r.station_count
    return acc


def _delta_pct(current: float, previous: float | None) -> float | None:
    if previous is None or previous <= 0:
        return None
    return round((current - previous) / previous * 100, 2)


# ── Overview ─────────────────────────────────────────────────────────────────


async def get_overview(session: AsyncSession) -> OverviewOut:
    repo = AnalyticsRepository(session)
    total_stations = await repo.count_stations()
    total_observations = await repo.count_observations()
    fuel_averages = await repo.current_fuel_averages()

    start, end, _ = _window("30d")
    muni = await repo.municipality_window_stats(_OVERVIEW_FUEL, start, end)
    folded = _fold_to_comarca(muni)
    cheapest = min(folded, key=lambda c: folded[c].avg) if folded else None
    dearest = max(folded, key=lambda c: folded[c].avg) if folded else None

    return OverviewOut(
        generated_at=datetime.now(UTC),
        total_stations=total_stations,
        total_observations=total_observations,
        fuel_averages=fuel_averages,
        cheapest_comarca=cheapest,
        most_expensive_comarca=dearest,
        insight=insights.overview_insight(fuel_averages, cheapest, dearest),
    )


# ── Trends ───────────────────────────────────────────────────────────────────


def _to_points(rows: list[LabeledTrendRow]) -> list[TrendPoint]:
    return [
        TrendPoint(
            bucket=r.bucket,
            avg_price=round(r.avg, 3),
            min_price=round(r.min, 3),
            max_price=round(r.max, 3),
            sample_count=r.count,
        )
        for r in rows
    ]


async def get_trends(
    session: AsyncSession, fuel: str, rng: TimeRange, group_by: GroupBy
) -> TrendsOut:
    repo = AnalyticsRepository(session)
    start, end, _ = _window(rng)
    granularity = _bucket_granularity(rng)

    base_rows = await repo.trend_rows(fuel, start, end, granularity)
    base_points = [
        TrendPoint(bucket=r.bucket, avg_price=round(r.avg, 3), min_price=round(r.min, 3),
                   max_price=round(r.max, 3), sample_count=r.count)
        for r in base_rows
    ]

    series: list[TrendSeries] = []
    if group_by == "brand":
        ranked = await repo.brand_window_stats(fuel, start, end)
        top = sorted(ranked, key=lambda g: g.sample_count, reverse=True)[:_MAX_GROUPED_SERIES]
        labeled = await repo.trend_rows_by_brand(
            fuel, start, end, granularity, [g.key for g in top]
        )
        series = _group_series(labeled)
    elif group_by == "comarca":
        labeled = await repo.trend_rows_by_municipality(fuel, start, end, granularity)
        series = _comarca_series(labeled)
    else:
        series = [TrendSeries(label="all", points=base_points)]

    if len(base_rows) > _HEAVY_ROW_THRESHOLD:
        analytics_heavy_queries_total.labels(endpoint="trends").inc()
        log.warning("analytics trends scanned %d buckets (fuel=%s range=%s)", len(base_rows), fuel, rng)

    return TrendsOut(
        fuel_type=fuel,
        range=rng,
        group_by=group_by,
        series=series,
        insight=insights.trend_insight(base_points, fuel, rng),
    )


def _group_series(rows: list[LabeledTrendRow]) -> list[TrendSeries]:
    by_label: dict[str, list[LabeledTrendRow]] = {}
    for r in rows:
        by_label.setdefault(r.label, []).append(r)
    return [TrendSeries(label=label, points=_to_points(rs)) for label, rs in by_label.items()]


@dataclass
class _BucketAcc:
    wsum: float = 0.0
    n: int = 0
    pmin: float = math.inf
    pmax: float = -math.inf


def _comarca_series(rows: list[LabeledTrendRow]) -> list[TrendSeries]:
    """Fold per-municipality bucket rows into per-comarca series."""
    nested: dict[str, dict[str, _BucketAcc]] = {}
    totals: dict[str, int] = {}
    for r in rows:
        comarca = comarca_of(r.label)
        if comarca is None:
            continue
        bucket_acc = nested.setdefault(comarca, {}).setdefault(r.bucket, _BucketAcc())
        bucket_acc.wsum += r.avg * r.count
        bucket_acc.n += r.count
        bucket_acc.pmin = min(bucket_acc.pmin, r.min)
        bucket_acc.pmax = max(bucket_acc.pmax, r.max)
        totals[comarca] = totals.get(comarca, 0) + r.count

    top = sorted(totals, key=lambda c: totals[c], reverse=True)[:_MAX_GROUPED_SERIES]
    series: list[TrendSeries] = []
    for comarca in top:
        points = [
            TrendPoint(bucket=b, avg_price=round(a.wsum / a.n, 3),
                       min_price=round(a.pmin, 3), max_price=round(a.pmax, 3), sample_count=a.n)
            for b, a in sorted(nested[comarca].items())
            if a.n
        ]
        series.append(TrendSeries(label=comarca, points=points))
    return series


# ── Comarcas ─────────────────────────────────────────────────────────────────


async def get_comarcas(
    session: AsyncSession, fuel: str, rng: TimeRange, sort: str, limit: int
) -> ComarcasOut:
    repo = AnalyticsRepository(session)
    start, end, prev_start = _window(rng)
    cur = _fold_to_comarca(await repo.municipality_window_stats(fuel, start, end))
    prev = _fold_to_comarca(await repo.municipality_window_stats(fuel, prev_start, start))

    items: list[ComarcaStat] = []
    for comarca, a in cur.items():
        prev_avg = prev[comarca].avg if comarca in prev and prev[comarca].n else None
        delta = _delta_pct(a.avg, prev_avg)
        items.append(
            ComarcaStat(
                comarca=comarca,
                avg_price=round(a.avg, 3),
                min_price=round(a.pmin, 3),
                max_price=round(a.pmax, 3),
                station_count=a.stations,
                sample_count=a.n,
                delta_pct=delta,
                direction=_direction(delta),
            )
        )

    if sort == "name":
        items.sort(key=lambda c: c.comarca)
    elif sort == "delta":
        items.sort(key=lambda c: c.delta_pct if c.delta_pct is not None else 0.0)
    else:  # "price" (default)
        items.sort(key=lambda c: c.avg_price)
    items = items[:limit]

    return ComarcasOut(
        fuel_type=fuel, range=rng, items=items, insight=insights.comarca_insight(items, fuel)
    )


# ── Brands ───────────────────────────────────────────────────────────────────


async def get_brands(session: AsyncSession, fuel: str, rng: TimeRange) -> BrandsOut:
    repo = AnalyticsRepository(session)
    start, end, prev_start = _window(rng)
    cur = await repo.brand_window_stats(fuel, start, end)
    prev = {g.key: g for g in await repo.brand_window_stats(fuel, prev_start, start)}

    ranked = sorted(cur, key=lambda g: g.avg)
    items: list[BrandStat] = []
    for rank, g in enumerate(ranked, start=1):
        prev_avg = prev[g.key].avg if g.key in prev else None
        delta = _delta_pct(g.avg, prev_avg)
        items.append(
            BrandStat(
                brand=g.key,
                rank=rank,
                avg_price=round(g.avg, 3),
                station_count=g.station_count,
                sample_count=g.sample_count,
                delta_pct=delta,
                direction=_direction(delta),
            )
        )

    return BrandsOut(
        fuel_type=fuel, range=rng, items=items, insight=insights.brand_insight(items, fuel)
    )


# ── Heatmap ──────────────────────────────────────────────────────────────────

_Bbox = tuple[float, float, float, float]


async def get_heatmap(
    session: AsyncSession, fuel: str, bbox: _Bbox | None, limit: int
) -> HeatmapOut:
    repo = AnalyticsRepository(session)
    if bbox is not None:
        north, south, east, west = bbox
        rows = await repo.heatmap_rows(
            fuel, north=north, south=south, east=east, west=west, limit=limit
        )
    else:
        rows = await repo.heatmap_rows(fuel, limit=limit)
    points = [
        HeatmapPoint(
            station_id=r.station_id, lat=r.lat, lon=r.lon, brand=r.brand,
            municipality=r.municipality, price=round(r.price, 3),
        )
        for r in rows
    ]
    prices = [p.price for p in points]
    return HeatmapOut(
        fuel_type=fuel,
        count=len(points),
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        points=points,
    )


# ── Insights bundle ──────────────────────────────────────────────────────────


async def get_insights(session: AsyncSession, fuel: str, rng: TimeRange) -> InsightsOut:
    trends = await get_trends(session, fuel, rng, "none")
    comarcas = await get_comarcas(session, fuel, rng, sort="price", limit=50)
    brands = await get_brands(session, fuel, rng)
    return InsightsOut(
        fuel_type=fuel,
        range=rng,
        items=[trends.insight, comarcas.insight, brands.insight],
    )
