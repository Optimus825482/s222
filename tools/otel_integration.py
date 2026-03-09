"""
OpenTelemetry Integration — Distributed tracing for multi-agent system.

Provides:
- Trace context propagation across agents
- Span creation for agent operations, tool calls, LLM requests
- Integration with existing observability.py trace_id system
- Export to Jaeger/Tempo/OTLP backends
- Graceful fallback when OTel SDK not installed

Usage:
    from tools.otel_integration import tracer, start_agent_span

    with start_agent_span("researcher", "web_search") as span:
        span.set_attribute("query", "test")
        result = await do_search()
        span.set_attribute("result_count", len(result))
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger("otel_integration")

# ── Lazy OTel imports ────────────────────────────────────────────

_otel_available = False
_tracer = None
_meter = None

try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    _otel_available = True
except ImportError:
    pass


# ── Initialization ───────────────────────────────────────────────

def init_otel(
    service_name: str = "multi-agent-ops",
    otlp_endpoint: str | None = None,
) -> bool:
    """
    Initialize OpenTelemetry with OTLP exporter.
    Returns True if successfully initialized.
    """
    global _tracer, _meter

    if not _otel_available:
        logger.info("OpenTelemetry SDK not installed — tracing disabled")
        return False

    endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    try:
        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.getenv("APP_VERSION", "1.0.0"),
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        })

        # Traces
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            span_exporter = OTLPSpanExporter(endpoint=endpoint)
        except ImportError:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                span_exporter = OTLPSpanExporter(endpoint=endpoint.replace("4317", "4318"))
            except ImportError:
                logger.warning("No OTLP exporter available — using console exporter")
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter
                span_exporter = ConsoleSpanExporter()

        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("multi-agent-ops")

        # Metrics
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=endpoint),
                export_interval_millis=30_000,
            )
            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
            metrics.set_meter_provider(meter_provider)
            _meter = metrics.get_meter("multi-agent-ops")
        except ImportError:
            logger.info("OTel metrics exporter not available — metrics disabled")

        logger.info(f"OpenTelemetry initialized → {endpoint}")
        return True

    except Exception as e:
        logger.warning(f"OpenTelemetry init failed: {e}")
        return False


# ── Tracer Access ────────────────────────────────────────────────

def get_tracer():
    """Get the OTel tracer (or a no-op stub)."""
    global _tracer
    if _tracer:
        return _tracer
    if _otel_available:
        return trace.get_tracer("multi-agent-ops")
    return _NoOpTracer()


def get_meter():
    """Get the OTel meter (or None)."""
    return _meter


# ── Span Helpers ─────────────────────────────────────────────────

@contextmanager
def start_agent_span(
    agent_role: str,
    operation: str,
    attributes: dict[str, Any] | None = None,
) -> Generator:
    """
    Start a span for an agent operation.
    Integrates with existing trace_id from observability.py.
    """
    tracer = get_tracer()

    # Link to existing trace_id if available
    extra_attrs = {
        "agent.role": agent_role,
        "agent.operation": operation,
    }
    try:
        from tools.observability import get_trace_id
        tid = get_trace_id()
        if tid:
            extra_attrs["trace.legacy_id"] = tid
    except ImportError:
        pass

    if attributes:
        extra_attrs.update(attributes)

    if isinstance(tracer, _NoOpTracer):
        yield _NoOpSpan(extra_attrs)
        return

    span = tracer.start_span(
        f"{agent_role}.{operation}",
        attributes=extra_attrs,
    )
    ctx = trace.set_span_in_context(span)
    token = None
    try:
        from opentelemetry.context import attach
        token = attach(ctx)
    except ImportError:
        pass

    try:
        yield span
    except Exception as e:
        span.set_status(trace.StatusCode.ERROR, str(e))
        span.record_exception(e)
        raise
    finally:
        span.end()
        if token:
            try:
                from opentelemetry.context import detach
                detach(token)
            except ImportError:
                pass


@contextmanager
def start_tool_span(
    agent_role: str,
    tool_name: str,
    input_summary: str = "",
) -> Generator:
    """Start a span for a tool invocation."""
    with start_agent_span(
        agent_role,
        f"tool.{tool_name}",
        {"tool.name": tool_name, "tool.input": input_summary[:200]},
    ) as span:
        yield span


@contextmanager
def start_llm_span(
    agent_role: str,
    model: str,
    prompt_tokens: int = 0,
) -> Generator:
    """Start a span for an LLM API call."""
    with start_agent_span(
        agent_role,
        "llm.call",
        {
            "llm.model": model,
            "llm.prompt_tokens": prompt_tokens,
        },
    ) as span:
        yield span


# ── No-Op Stubs ──────────────────────────────────────────────────

class _NoOpSpan:
    """Stub span when OTel is not available."""
    def __init__(self, attrs=None):
        self._attrs = attrs or {}

    def set_attribute(self, key: str, value: Any): self._attrs[key] = value
    def set_status(self, *a, **kw): pass
    def record_exception(self, *a): pass
    def end(self): pass
    def add_event(self, name: str, attributes=None): pass


class _NoOpTracer:
    """Stub tracer when OTel is not available."""
    def start_span(self, name: str, **kwargs) -> _NoOpSpan:
        return _NoOpSpan(kwargs.get("attributes"))

    def start_as_current_span(self, name: str, **kwargs):
        return contextmanager(lambda: (yield _NoOpSpan()))()
