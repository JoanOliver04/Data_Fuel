"""Central logging configuration.

One ``setup_logging()`` call wires every logger in the app to the same
formatter and level. Use ``logging.getLogger(__name__)`` everywhere — never
``print``.

Two formats are available:

* **text** (default in DEBUG): human-readable single line, easy to scan locally.
* **json**  (default in production): one JSON object per line — machine-readable
  for log shippers (Loki/ELK/CloudWatch), with ``request_id`` / ``correlation_id``
  promoted to top-level fields and arbitrary ``extra={...}`` merged in.

Correlation: ``request_id`` identifies a single HTTP hop; ``correlation_id`` is
adopted from an inbound ``X-Correlation-ID`` / ``X-Request-ID`` header (or falls
back to the request_id) so a trace can be followed across services. Both are
carried in :class:`contextvars.ContextVar`, which is coroutine/task-safe.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import logging.config
from contextvars import ContextVar
from typing import Any

# Per-request correlation ids; set by RequestLoggingMiddleware. "-" when absent.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")

SERVICE_NAME = "datafuel-api"

# LogRecord attributes that are intrinsic — anything *else* on the record is a
# user-supplied ``extra={...}`` field and gets merged into the JSON output.
_RESERVED_LOGRECORD_KEYS = frozenset(
    logging.makeLogRecord({}).__dict__.keys()
    | {"request_id", "correlation_id", "message", "asctime", "taskName"}
)


class RequestIdFilter(logging.Filter):
    """Inject the current request_id and correlation_id into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        record.correlation_id = correlation_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    """Render each record as a single compact JSON line.

    Non-serialisable values fall back to ``str`` so logging can never raise.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _dt.datetime.fromtimestamp(
                record.created, tz=_dt.UTC
            ).isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        # Merge structured extras (e.g. log.info("...", extra={"duration_ms": 12})).
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOGRECORD_KEYS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


_TEXT_FORMAT = "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO", *, json_format: bool = False) -> None:
    """Configure the root logger and silence overly chatty third-party loggers."""
    level = level.upper()
    formatter: dict[str, Any] = (
        {"()": JsonFormatter}
        if json_format
        else {"format": _TEXT_FORMAT, "datefmt": _DATE_FORMAT}
    )
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id": {"()": RequestIdFilter},
            },
            "formatters": {
                "default": formatter,
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
