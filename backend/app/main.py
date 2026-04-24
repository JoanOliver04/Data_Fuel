"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.lifespan import lifespan
from app.core.rate_limit import limiter


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings: Settings = get_settings()

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
