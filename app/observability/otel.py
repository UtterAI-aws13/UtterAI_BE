"""OpenTelemetry bootstrap and framework instrumentation."""

from __future__ import annotations

import logging
import sys
from functools import lru_cache
from typing import Any

from fastapi import FastAPI
from opentelemetry import metrics, trace

from app.core.config import get_settings
from app.core.db import engine as sqlalchemy_engine

_LOGGER = logging.getLogger(__name__)
_INITIALIZED = False


def _running_under_pytest() -> bool:
    return "pytest" in sys.modules


def _parse_resource_attributes(raw_attributes: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for item in raw_attributes.split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        attributes[key.strip()] = value.strip()
    return attributes


def _build_resource(settings: Any):
    from opentelemetry.sdk.resources import Resource

    attributes = _parse_resource_attributes(settings.otel_resource_attributes)
    attributes.setdefault("service.name", settings.otel_service_name)
    attributes.setdefault("service.version", settings.app_version)
    return Resource.create(attributes)


def _build_trace_exporter(settings: Any):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter

    base_endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
    return HTTPSpanExporter(endpoint=f"{base_endpoint}/v1/traces")


def _build_metric_exporter(settings: Any):
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HTTPMetricExporter

    base_endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
    return HTTPMetricExporter(endpoint=f"{base_endpoint}/v1/metrics")


def initialize_observability() -> None:
    """Install OpenTelemetry providers and framework instrumentors once."""

    global _INITIALIZED
    if _INITIALIZED:
        return
    if _running_under_pytest():
        _INITIALIZED = True
        return

    try:
        _initialize_observability()
    except Exception:  # pragma: no cover - observability must not block startup
        _LOGGER.exception("Failed to initialize OpenTelemetry; observability disabled")
    finally:
        _INITIALIZED = True


def _initialize_observability() -> None:
    """Install OpenTelemetry providers and framework instrumentors."""

    from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    settings = get_settings()
    resource = _build_resource(settings)

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(_build_trace_exporter(settings)))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(_build_metric_exporter(settings))
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    try:
        SQLAlchemyInstrumentor().instrument(engine=sqlalchemy_engine)
    except Exception:  # pragma: no cover - instrumentation should not fail startup
        _LOGGER.exception("Failed to instrument SQLAlchemy")

    try:
        HTTPXClientInstrumentor().instrument()
    except Exception:  # pragma: no cover - instrumentation should not fail startup
        _LOGGER.exception("Failed to instrument HTTPX")

    try:
        BotocoreInstrumentor().instrument()
    except Exception:  # pragma: no cover - instrumentation should not fail startup
        _LOGGER.exception("Failed to instrument botocore")


def instrument_fastapi_app(app: FastAPI) -> None:
    """Attach FastAPI request spans to the application instance."""

    if _running_under_pytest():
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        initialize_observability()
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health.*")
    except Exception:  # pragma: no cover - instrumentation should not fail startup
        _LOGGER.exception("Failed to instrument FastAPI; OTel tracing disabled")


def get_tracer(name: str):
    """Return a tracer from the active provider."""

    return trace.get_tracer(name)


def get_meter(name: str):
    """Return a meter from the active provider."""

    return metrics.get_meter(name)
