"""
Observability — Structured logging, trace_id, execution traces.
Lightweight: no external dependencies (no Prometheus/Grafana).
Uses PostgreSQL for trace storage, JSON structured logging.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Any

from tools.pg_connection import db_conn, get_conn, release_conn

logger = logging.getLogger(__name__)

# ── 1. TRACE ID CONTEXT ─────────────────────────────────────────
# contextvars propagate through async calls automatically

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def new_trace_id() -> str:
    """Generate and set a new trace ID for the current context."""
    tid = uuid.uuid4().hex[:16]
    trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    """Get the current trace ID (empty string if none set)."""
    return trace_id_var.get()


# ── 2. STRUCTURED JSON LOGGER ───────────────────────────────────


class StructuredFormatter(logging.Formatter):
    """JSON formatter that includes trace_id in every log line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
            "trace_id": trace_id_var.get(""),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Allow extra structured fields via record.__dict__
        for key in ("agent_role", "tool_name", "latency_ms", "status"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_structured_logging(level: int = logging.INFO) -> None:
    """Replace root logger handlers with structured JSON output."""
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger(__name__).info("Structured logging initialized")


# ── 3. SCHEMA ────────────────────────────────────────────────────

_TRACES_SCHEMA = """
CREATE TABLE IF NOT EXISTS execution_traces (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trace_id       TEXT NOT NULL,
    agent_role     TEXT NOT NULL,
    step           INTEGER NOT NULL DEFAULT 0,
    tool_name      TEXT,
    input_summary  TEXT DEFAULT '',
    output_summary TEXT DEFAULT '',
    latency_ms     REAL DEFAULT 0,
    tokens         INTEGER DEFAULT 0,
    cost_usd       REAL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'ok',
    error_message  TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_traces_trace_id   ON execution_traces(trace_id);
CREATE INDEX IF NOT EXISTS idx_traces_agent      ON execution_traces(agent_role, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traces_created    ON execution_traces(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traces_status     ON execution_traces(status);
"""


def init_traces_table() -> None:
    """Create execution_traces table. Safe to call multiple times."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_TRACES_SCHEMA)
        conn.commit()
    logger.info("execution_traces table initialized")


# ── 4. EXECUTION TRACE RECORDER ─────────────────────────────────


def record_trace(
    agent_role: str,
    step: int,
    tool_name: str | None = None,
    input_summary: str = "",
    output_summary: str = "",
    latency_ms: float = 0,
    tokens: int = 0,
    cost_usd: float = 0,
    status: str = "ok",
    error_message: str | None = None,
) -> None:
    """Record an execution trace step to PostgreSQL (sync, thread-safe)."""
    tid = trace_id_var.get("")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO execution_traces
                   (trace_id, agent_role, step, tool_name, input_summary,
                    output_summary, latency_ms, tokens, cost_usd, status, error_message)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    tid, agent_role, step, tool_name,
                    input_summary[:500],  # cap summary length
                    output_summary[:500],
                    latency_ms, tokens, cost_usd, status,
                    error_message[:1000] if error_message else None,
                ),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning(f"Failed to record trace: {e}")
    finally:
        release_conn(conn)


# ── 5. TRACE QUERY FUNCTIONS ────────────────────────────────────


def get_traces(trace_id: str) -> list[dict[str, Any]]:
    """Get all steps for a specific trace."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM execution_traces
                   WHERE trace_id = %s ORDER BY step, created_at""",
                (trace_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_recent_traces(limit: int = 50) -> list[dict[str, Any]]:
    """Get recent traces grouped by trace_id."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT trace_id,
                          MIN(agent_role) AS agent_role,
                          COUNT(*) AS step_count,
                          SUM(latency_ms) AS total_latency_ms,
                          SUM(tokens) AS total_tokens,
                          SUM(cost_usd) AS total_cost_usd,
                          MAX(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS has_error,
                          MIN(created_at) AS started_at,
                          MAX(created_at) AS ended_at
                   FROM execution_traces
                   GROUP BY trace_id
                   ORDER BY MAX(created_at) DESC
                   LIMIT %s""",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_agent_traces(agent_role: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get traces for a specific agent role."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM execution_traces
                   WHERE agent_role = %s
                   ORDER BY created_at DESC LIMIT %s""",
                (agent_role, limit),
            )
            return [dict(r) for r in cur.fetchall()]


def get_trace_stats() -> dict[str, Any]:
    """Aggregate trace statistics: avg latency, error rate, top tools."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            # Overall stats
            cur.execute(
                """SELECT
                       COUNT(*) AS total_steps,
                       COUNT(DISTINCT trace_id) AS total_traces,
                       AVG(latency_ms) AS avg_latency_ms,
                       MAX(latency_ms) AS max_latency_ms,
                       SUM(tokens) AS total_tokens,
                       SUM(cost_usd) AS total_cost_usd,
                       COUNT(*) FILTER (WHERE status = 'error') AS error_count
                   FROM execution_traces
                   WHERE created_at > now() - INTERVAL '24 hours'"""
            )
            overall = dict(cur.fetchone() or {})

            total = overall.get("total_steps") or 0
            errors = overall.get("error_count") or 0
            overall["error_rate"] = round(errors / total, 4) if total > 0 else 0

            # Top tools by usage
            cur.execute(
                """SELECT tool_name, COUNT(*) AS usage_count,
                          AVG(latency_ms) AS avg_latency_ms
                   FROM execution_traces
                   WHERE tool_name IS NOT NULL
                     AND created_at > now() - INTERVAL '24 hours'
                   GROUP BY tool_name
                   ORDER BY usage_count DESC
                   LIMIT 10"""
            )
            overall["top_tools"] = [dict(r) for r in cur.fetchall()]

            # Top agents by trace count
            cur.execute(
                """SELECT agent_role, COUNT(DISTINCT trace_id) AS trace_count,
                          AVG(latency_ms) AS avg_latency_ms
                   FROM execution_traces
                   WHERE created_at > now() - INTERVAL '24 hours'
                   GROUP BY agent_role
                   ORDER BY trace_count DESC
                   LIMIT 10"""
            )
            overall["top_agents"] = [dict(r) for r in cur.fetchall()]

            return overall


# ── 6. DECORATOR — auto-trace tool calls ────────────────────────


def traced_tool(tool_name: str):
    """Decorator that auto-records execution trace for a tool call.

    Works with both sync and async functions.
    Expects `agent_role` as a kwarg or defaults to 'unknown'.
    """
    def decorator(func):
        if _is_coroutine_function(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                agent = kwargs.get("agent_role", "unknown")
                try:
                    result = await func(*args, **kwargs)
                    latency = (time.perf_counter() - start) * 1000
                    record_trace(
                        agent_role=agent,
                        step=0,
                        tool_name=tool_name,
                        latency_ms=round(latency, 2),
                        status="ok",
                    )
                    return result
                except Exception as e:
                    latency = (time.perf_counter() - start) * 1000
                    record_trace(
                        agent_role=agent,
                        step=0,
                        tool_name=tool_name,
                        latency_ms=round(latency, 2),
                        status="error",
                        error_message=str(e),
                    )
                    raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                agent = kwargs.get("agent_role", "unknown")
                try:
                    result = func(*args, **kwargs)
                    latency = (time.perf_counter() - start) * 1000
                    record_trace(
                        agent_role=agent,
                        step=0,
                        tool_name=tool_name,
                        latency_ms=round(latency, 2),
                        status="ok",
                    )
                    return result
                except Exception as e:
                    latency = (time.perf_counter() - start) * 1000
                    record_trace(
                        agent_role=agent,
                        step=0,
                        tool_name=tool_name,
                        latency_ms=round(latency, 2),
                        status="error",
                        error_message=str(e),
                    )
                    raise
            return sync_wrapper
    return decorator


def _is_coroutine_function(func) -> bool:
    """Check if function is async (handles both native and wrapped)."""
    import asyncio
    import inspect
    return asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func)
