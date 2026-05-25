"""Analytics HTTP endpoints.

Thin layer over the analytics services: validates query params, serves from a
short-TTL cache, records per-endpoint metrics, and optionally enriches insights
via the LLM seam. Responses are GZip-compressed by the global middleware.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal, TypeVar, cast

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_llm_provider
from app.analytics import enrich
from app.analytics.cache import analytics_cache
from app.analytics.schemas import (
    BrandsOut,
    ComarcasOut,
    HeatmapOut,
    Insight,
    InsightsOut,
    OverviewOut,
    TimeRange,
    TrendsOut,
)
from app.analytics.services import analytics_service
from app.core.config import Settings, get_settings
from app.core.metrics import (
    analytics_cache_operations_total,
    analytics_query_duration_seconds,
    analytics_requests_total,
)
from app.domain.entities.fuel_type import FuelType
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/analytics", tags=["analytics"])

T = TypeVar("T", bound=BaseModel)

_SortBy = Literal["price", "delta", "name"]


async def _serve(endpoint: str, key: str, factory: Callable[[], Awaitable[T]]) -> T:
    """Cache → build → record. Single place for cache + metrics per endpoint."""
    cached = await analytics_cache.get(key)
    if cached is not None:
        analytics_cache_operations_total.labels(result="hit").inc()
        analytics_requests_total.labels(endpoint=endpoint, result="cached").inc()
        return cast(T, cached)
    analytics_cache_operations_total.labels(result="miss").inc()

    start = time.perf_counter()
    try:
        result = await factory()
    except Exception:
        analytics_requests_total.labels(endpoint=endpoint, result="error").inc()
        raise
    analytics_query_duration_seconds.labels(endpoint=endpoint).observe(time.perf_counter() - start)
    analytics_requests_total.labels(endpoint=endpoint, result="ok").inc()
    await analytics_cache.set(key, result)
    return result


async def _enrich(insight: Insight, settings: Settings) -> Insight:
    """Optionally LLM-rephrase an insight; deterministic by default."""
    if not settings.analytics_llm_insights:
        return insight
    return await enrich.enrich_insight(insight, get_llm_provider(settings))


@router.get("/overview", response_model=OverviewOut, summary="Dashboard KPI overview")
async def overview(session: AsyncSession = Depends(get_async_session)) -> OverviewOut:
    settings = get_settings()

    async def build() -> OverviewOut:
        out = await analytics_service.get_overview(session)
        out.insight = await _enrich(out.insight, settings)
        return out

    return await _serve("overview", "overview", build)


@router.get("/trends", response_model=TrendsOut, summary="Temporal price evolution")
async def trends(
    fuel_type: Annotated[FuelType, Query()],
    time_range: Annotated[TimeRange, Query(alias="range")] ="7d",
    group_by: Annotated[Literal["none", "brand", "comarca"], Query()] = "none",
    session: AsyncSession = Depends(get_async_session),
) -> TrendsOut:
    settings = get_settings()
    key = f"trends:{fuel_type.value}:{time_range}:{group_by}"

    async def build() -> TrendsOut:
        out = await analytics_service.get_trends(session, fuel_type.value, time_range, group_by)
        out.insight = await _enrich(out.insight, settings)
        return out

    return await _serve("trends", key, build)


@router.get("/comarcas", response_model=ComarcasOut, summary="Comarca-level analytics")
async def comarcas(
    fuel_type: Annotated[FuelType, Query()],
    time_range: Annotated[TimeRange, Query(alias="range")] ="30d",
    sort: Annotated[_SortBy, Query()] = "price",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    session: AsyncSession = Depends(get_async_session),
) -> ComarcasOut:
    settings = get_settings()
    key = f"comarcas:{fuel_type.value}:{time_range}:{sort}:{limit}"

    async def build() -> ComarcasOut:
        out = await analytics_service.get_comarcas(session, fuel_type.value, time_range, sort, limit)
        out.insight = await _enrich(out.insight, settings)
        return out

    return await _serve("comarcas", key, build)


@router.get("/brands", response_model=BrandsOut, summary="Brand comparison analytics")
async def brands(
    fuel_type: Annotated[FuelType, Query()],
    time_range: Annotated[TimeRange, Query(alias="range")] ="30d",
    session: AsyncSession = Depends(get_async_session),
) -> BrandsOut:
    settings = get_settings()
    key = f"brands:{fuel_type.value}:{time_range}"

    async def build() -> BrandsOut:
        out = await analytics_service.get_brands(session, fuel_type.value, time_range)
        out.insight = await _enrich(out.insight, settings)
        return out

    return await _serve("brands", key, build)


@router.get("/heatmap", response_model=HeatmapOut, summary="Geographic price density")
async def heatmap(
    fuel_type: Annotated[FuelType, Query()],
    north: Annotated[float | None, Query(ge=-90, le=90)] = None,
    south: Annotated[float | None, Query(ge=-90, le=90)] = None,
    east: Annotated[float | None, Query(ge=-180, le=180)] = None,
    west: Annotated[float | None, Query(ge=-180, le=180)] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 2000,
    session: AsyncSession = Depends(get_async_session),
) -> HeatmapOut:
    bbox = (
        (north, south, east, west)
        if None not in (north, south, east, west)
        else None
    )
    key = f"heatmap:{fuel_type.value}:{north},{south},{east},{west}:{limit}"
    return await _serve(
        "heatmap",
        key,
        lambda: analytics_service.get_heatmap(
            session, fuel_type.value, cast("tuple[float, float, float, float] | None", bbox), limit
        ),
    )


@router.get("/insights", response_model=InsightsOut, summary="Headline AI insights bundle")
async def insights_bundle(
    fuel_type: Annotated[FuelType, Query()],
    time_range: Annotated[TimeRange, Query(alias="range")] ="7d",
    session: AsyncSession = Depends(get_async_session),
) -> InsightsOut:
    settings = get_settings()
    key = f"insights:{fuel_type.value}:{time_range}"

    async def build() -> InsightsOut:
        out = await analytics_service.get_insights(session, fuel_type.value, time_range)
        if settings.analytics_llm_insights:
            out.items = [await _enrich(i, settings) for i in out.items]
        return out

    return await _serve("insights", key, build)
