"""
Prometheus Metrics Exporter — Exposes agent metrics for Prometheus scraping.

Provides:
- Agent request counters (by role, task_type, status)
- Latency histograms (by agent, tool)
- Token usage gauges
- Cost tracking
- Active task gauges
- Custom MLflow model metrics (if MLflow available)
- /metrics endpoint for Prometheus scraping

Usage:
    from tools.prometheus_metrics import metrics, track_request

    # Auto-track via decorator
    @track_request("researcher")
    async def handle_research(query): ...

    # Manual recording
    metrics.record_request("orchestrator", "planning", 1.5, 500, "ok")
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger("prometheus_metrics")

# Try importing prometheus_client — graceful fallback if not installed
_prom = None
try:
    import prometheus_client
    _prom = prometheus_client
except ImportError:
    logger.info("prometheus_client not installed — metrics will be collected in-memory only")


# ── Metric Definitions ───────────────────────────────────────────

class MetricsCollector:
    """
    Collects and exposes metrics in Prometheus format.
    Works with or without prometheus_client library.
    """

    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = defaultdict(float)

        if _prom:
            self._init_prometheus()
        else:
            self._prom_request_total = None
            self._prom_latency = None
            self._prom_tokens = None
            self._prom_cost = None
            self._prom_active_tasks = None
            self._prom_errors = None
            self._prom_model_accuracy = None
            self._prom_model_latency = None

    def _init_prometheus(self):
        """Initialize Prometheus metric objects."""
        self._prom_request_total = _prom.Counter(
            "agent_requests_total",
            "Total agent requests",
            ["agent_role", "task_type", "status"],
        )
        self._prom_latency = _prom.Histogram(
            "agent_request_duration_seconds",
            "Agent request latency in seconds",
            ["agent_role", "tool_name"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
        )
        self._prom_tokens = _prom.Counter(
            "agent_tokens_total",
            "Total tokens consumed",
            ["agent_role", "direction"],  # direction: input/output
        )
        self._prom_cost = _prom.Counter(
            "agent_cost_usd_total",
            "Total cost in USD",
            ["agent_role", "model"],
        )
        self._prom_active_tasks = _prom.Gauge(
            "agent_active_tasks",
            "Currently active tasks per agent",
            ["agent_role"],
        )
        self._prom_errors = _prom.Counter(
            "agent_errors_total",
            "Total agent errors",
            ["agent_role", "error_type"],
        )
        # MLflow model metrics
        self._prom_model_accuracy = _prom.Gauge(
            "mlflow_model_accuracy",
            "Model accuracy from MLflow",
            ["model_name", "version"],
        )
        self._prom_model_latency = _prom.Gauge(
            "mlflow_model_inference_seconds",
            "Model inference latency from MLflow",
            ["model_name", "version"],
        )

    # ── Recording Methods ────────────────────────────────────────

    def record_request(
        self,
        agent_role: str,
        task_type: str,
        latency_s: float,
        tokens: int = 0,
        status: str = "ok",
        tool_name: str = "",
        model: str = "",
        cost_usd: float = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record a completed agent request with all dimensions."""
        # In-memory counters (always available)
        self._counters[f"requests:{agent_role}:{task_type}:{status}"] += 1
        self._histograms[f"latency:{agent_role}:{tool_name}"].append(latency_s)
        self._gauges[f"tokens:{agent_role}:total"] += tokens
        self._gauges[f"cost:{agent_role}:total"] += cost_usd

        # Prometheus native metrics
        if self._prom_request_total:
            self._prom_request_total.labels(
                agent_role=agent_role, task_type=task_type, status=status
            ).inc()
        if self._prom_latency and tool_name:
            self._prom_latency.labels(
                agent_role=agent_role, tool_name=tool_name
            ).observe(latency_s)
        if self._prom_tokens:
            if input_tokens:
                self._prom_tokens.labels(agent_role=agent_role, direction="input").inc(input_tokens)
            if output_tokens:
                self._prom_tokens.labels(agent_role=agent_role, direction="output").inc(output_tokens)
            elif tokens:
                self._prom_tokens.labels(agent_role=agent_role, direction="total").inc(tokens)
        if self._prom_cost and cost_usd > 0:
            self._prom_cost.labels(agent_role=agent_role, model=model).inc(cost_usd)

    def set_active_tasks(self, agent_role: str, count: int) -> None:
        """Update active task gauge for an agent."""
        self._gauges[f"active_tasks:{agent_role}"] = count
        if self._prom_active_tasks:
            self._prom_active_tasks.labels(agent_role=agent_role).set(count)

    def record_error(self, agent_role: str, error_type: str) -> None:
        """Record an agent error."""
        self._counters[f"errors:{agent_role}:{error_type}"] += 1
        if self._prom_errors:
            self._prom_errors.labels(agent_role=agent_role, error_type=error_type).inc()

    def record_mlflow_metric(
        self,
        model_name: str,
        version: str,
        accuracy: float | None = None,
        inference_latency: float | None = None,
    ) -> None:
        """Record MLflow model metrics for Prometheus export."""
        if accuracy is not None:
            self._gauges[f"mlflow:accuracy:{model_name}:{version}"] = accuracy
            if self._prom_model_accuracy:
                self._prom_model_accuracy.labels(
                    model_name=model_name, version=version
                ).set(accuracy)
        if inference_latency is not None:
            self._gauges[f"mlflow:latency:{model_name}:{version}"] = inference_latency
            if self._prom_model_latency:
                self._prom_model_latency.labels(
                    model_name=model_name, version=version
                ).set(inference_latency)

    # ── Query Methods ────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all collected metrics."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histogram_counts": {k: len(v) for k, v in self._histograms.items()},
        }

    def generate_text_metrics(self) -> str:
        """
        Generate Prometheus text exposition format.
        Used when prometheus_client is not installed.
        """
        if _prom:
            return _prom.generate_latest().decode("utf-8")

        # Manual text format
        lines = []
        lines.append("# HELP agent_requests_total Total agent requests")
        lines.append("# TYPE agent_requests_total counter")
        for key, val in self._counters.items():
            if key.startswith("requests:"):
                parts = key.split(":", 3)
                if len(parts) == 4:
                    _, role, task, status = parts
                    lines.append(
                        f'agent_requests_total{{agent_role="{role}",task_type="{task}",status="{status}"}} {val}'
                    )

        lines.append("# HELP agent_cost_usd_total Total cost in USD")
        lines.append("# TYPE agent_cost_usd_total counter")
        for key, val in self._gauges.items():
            if key.startswith("cost:") and key.endswith(":total"):
                role = key.split(":")[1]
                lines.append(f'agent_cost_usd_total{{agent_role="{role}"}} {val}')

        lines.append("# HELP agent_active_tasks Currently active tasks")
        lines.append("# TYPE agent_active_tasks gauge")
        for key, val in self._gauges.items():
            if key.startswith("active_tasks:"):
                role = key.split(":", 1)[1]
                lines.append(f'agent_active_tasks{{agent_role="{role}"}} {val}')

        return "\n".join(lines) + "\n"


# ── Singleton ────────────────────────────────────────────────────

_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


# Convenience alias
metrics = get_metrics()


# ── Decorator ────────────────────────────────────────────────────

def track_request(agent_role: str, tool_name: str = ""):
    """Decorator to automatically track request metrics."""
    def decorator(func):
        import asyncio
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            status = "ok"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                metrics.record_error(agent_role, type(e).__name__)
                raise
            finally:
                latency = time.time() - start
                metrics.record_request(agent_role, "auto", latency, status=status, tool_name=tool_name)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            status = "ok"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                metrics.record_error(agent_role, type(e).__name__)
                raise
            finally:
                latency = time.time() - start
                metrics.record_request(agent_role, "auto", latency, status=status, tool_name=tool_name)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
