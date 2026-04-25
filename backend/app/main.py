"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.lifespan import lifespan
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.rate_limit import limiter


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings: Settings = get_settings()

    # DEBUG override beats LOG_LEVEL — opt-in verbose mode for local dev.
    setup_logging(level="DEBUG" if settings.debug else settings.log_level)
    log = logging.getLogger("app")
    log.info(
        "Starting %s v%s (debug=%s, distance_mode=%s, log_level=%s)",
        settings.app_name,
        settings.app_version,
        settings.debug,
        settings.distance_mode,
        settings.log_level,
    )

    # Hide API docs in production. Toggle with ``DEBUG=true`` in .env for local use.
    docs_url = "/docs" if settings.debug else None
    redoc_url = "/redoc" if settings.debug else None
    openapi_url = "/openapi.json" if settings.debug else None

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    # Rate limiter: slowapi reads ``app.state.limiter`` from the request context.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    # Request logging runs outermost so it sees the final status code (incl.
    # CORS/rate-limit responses) and tags every nested log with a request id.
    app.add_middleware(RequestLoggingMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
