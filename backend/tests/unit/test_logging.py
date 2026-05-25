"""Unit tests for structured logging."""

import json
import logging

from app.core.logging import (
    JsonFormatter,
    RequestIdFilter,
    correlation_id_ctx,
    request_id_ctx,
)


def _record(msg: str, *args: object) -> logging.LogRecord:
    return logging.LogRecord(
        name="svc", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=args, exc_info=None,
    )


def test_json_formatter_emits_required_fields_and_extras() -> None:
    rec = _record("hello %s", "world")
    rec.request_id = "abc123"
    rec.correlation_id = "trace-9"
    rec.duration_ms = 12.5  # structured extra
    out = json.loads(JsonFormatter().format(rec))

    assert out["message"] == "hello world"
    assert out["level"] == "INFO"
    assert out["service"] == "datafuel-api"
    assert out["logger"] == "svc"
    assert out["request_id"] == "abc123"
    assert out["correlation_id"] == "trace-9"
    assert out["duration_ms"] == 12.5
    assert "timestamp" in out


def test_json_formatter_includes_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        rec = logging.LogRecord(
            name="svc", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="failed", args=(), exc_info=sys.exc_info(),
        )
    out = json.loads(JsonFormatter().format(rec))
    assert "exception" in out
    assert "ValueError: boom" in out["exception"]


def test_request_id_filter_injects_context() -> None:
    rtok = request_id_ctx.set("r1")
    ctok = correlation_id_ctx.set("c1")
    try:
        rec = _record("m")
        assert RequestIdFilter().filter(rec) is True
        assert rec.request_id == "r1"
        assert rec.correlation_id == "c1"
    finally:
        request_id_ctx.reset(rtok)
        correlation_id_ctx.reset(ctok)
