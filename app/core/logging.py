"""Structured JSON logging with OTel trace context injection."""

from __future__ import annotations

import json
import logging

from opentelemetry import trace

_SKIP_ATTRS = frozenset((
    "name", "msg", "args", "levelname", "levelno",
    "pathname", "filename", "module", "exc_info",
    "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread",
    "threadName", "processName", "process", "message",
    "taskName",
))


class OtelJsonFormatter(logging.Formatter):
    """Format log records as JSON and inject the active OTel span context."""

    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span()
        ctx = span.get_span_context()

        entry: dict = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else "",
            "span_id": format(ctx.span_id, "016x") if ctx.is_valid else "",
        }

        for key, val in record.__dict__.items():
            if key not in _SKIP_ATTRS and not key.startswith("_"):
                entry[key] = val

        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install OtelJsonFormatter on the root logger.

    Must be called before OTel SDK initialisation so that the formatter
    is in place before any instrumentation logs are emitted.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(OtelJsonFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)
