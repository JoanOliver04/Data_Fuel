"""Central logging configuration.

One ``setup_logging()`` call wires every logger in the app to the same
formatter and level. Use ``logging.getLogger(__name__)`` everywhere — never
``print``.

Format includes timestamp, level, logger name, request_id (when set by the
RequestLoggingMiddleware), and the message. Tracebacks are emitted via
``logger.exception(...)``.
"""

from __future__ import annotations

import logging
import logging.config
from contextvars import ContextVar

# Per-request correlation id; set by RequestLoggingMiddleware. "-" when absent.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject the current request_id into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


_LOG_FORMAT = (
    "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s — %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger and silence overly chatty third-party loggers."""
    level = level.upper()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id": {"()": RequestIdFilter},
            },
            "formatters": {
                "default": {
                    "format": _LOG_FORMAT,
                    "datefmt": _DATE_FORMAT,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_id"],
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {"handlers": ["console"], "level": level},
            "loggers": {
                # Quiet noisy libs: they still log warnings/errors.
                "httpx": {"level": "WARNING"},
                "httpcore": {"level": "WARNING"},
                "uvicorn.access": {"level": "WARNING"},
                "apscheduler": {"level": "INFO"},
            },
        }
    )
