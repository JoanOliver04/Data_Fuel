"""TomTom routing provider: adapts TomTomClient to RoutingProvider.

Adds the two adapter-level concerns the client deliberately omits:
- Quota guard: a process-local daily counter short-circuits to haversine once
  the configured limit is spent (the client has no business logic).
- Graceful degradation: any TomTom failure (network, 5xx after retries, 429
  after retries, schema mismatch) or a per-leg routing failure falls back to
  haversine. The adapter NEVER raises — failed legs carry ``provider="tomtom"``
  and ``failed=True`` so the caller knows what degraded.

Mapping: TomTom returns metres + seconds, which map directly to ``RouteLeg``
(``length_in_meters``→km, ``travel_time_in_seconds``→``duration_seconds``,
``traffic_delay_in_seconds``→``traffic_delay_seconds``).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.infrastructure.external.tomtom import TomTomClient, TomTomError
from app.services.routing.dto import RouteLeg
from app.services.routing.providers.haversine_provider import haversine_leg
from app.services.routing.quota import DailyQuotaGuard, default_quota_guard

log = logging.getLogger(__name__)

PROVIDER_NAME = "tomtom"


class TomTomMatrixProvider:
    """RoutingProvider backed by TomTom Matrix Routing v2, with a quota guard."""

    def __init__(
        self,
        client: TomTomClient,
        daily_quota_limit: int,
        quota_guard: DailyQuotaGuard | None = None,
    ) -> None:
        self._client = client
        self._daily_quota_limit = daily_quota_limit
        self._guard = quota_guard if quota_guard is not None else default_quota_guard

    async def matrix(
        self,
        origin: tuple[float, float],
        destinations: Sequence[tuple[float, float]],
    ) -> list[RouteLeg]:
        if not destinations:
            return []

        dest_list = list(destinations)

        # Quota guard first: never spend a request we know is over budget.
        if not self._guard.try_acquire(self._daily_quota_limit):
            return self._all_fallback(origin, dest_list)

        try:
            async with self._client as tomtom:
                summaries = await tomtom.matrix(origin, dest_list)
        except TomTomError as exc:
            # TomTomError covers rate-limit and timeout subclasses too.
            log.warning("TomTom matrix failed (%s); degrading all legs to haversine", exc)
            return self._all_fallback(origin, dest_list)

        legs: list[RouteLeg] = []
        for dest, summary in zip(dest_list, summaries, strict=True):
            if summary is None:
                legs.append(haversine_leg(origin, dest, provider=PROVIDER_NAME, failed=True))
                continue
            legs.append(
                RouteLeg(
                    distance_km=round(summary.length_in_meters / 1000.0, 3),
                    duration_seconds=summary.travel_time_in_seconds,
                    traffic_delay_seconds=summary.traffic_delay_in_seconds,
                    provider=PROVIDER_NAME,
                    failed=False,
                )
            )
        return legs

    @staticmethod
    def _all_fallback(
        origin: tuple[float, float],
        destinations: list[tuple[float, float]],
    ) -> list[RouteLeg]:
        return [
            haversine_leg(origin, dest, provider=PROVIDER_NAME, failed=True)
            for dest in destinations
        ]
