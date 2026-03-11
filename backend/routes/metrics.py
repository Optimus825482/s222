"""
Performance Metrics API — agent bazlı ve sistem geneli metrik endpoint'leri.
"""

import logging
import sys
import time
from pathlib import Path
import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

VALID_PERIODS = {"1h", "24h", "7d"}
PERIOD_MAP = {"1h": "1 hour", "24h": "24 hours", "7d": "7 days"}

from config import MODELS, RUNTIME_EVENT_SCHEMA_VERSION, get_feature_flags, get_model_capabilities, get_provider_registry_summary

VALID_ROLES = {cfg["role"] for cfg in MODELS.values()}


def _row_dict(row):
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {}


def _agent_metrics_payload(rows):
    agents = []
    for row in rows:
        row_data = _row_dict(row)
        agents.append(
            {
                "agent_role": row_data.get("agent_role", "unknown"),
                "avg_response_time": round(
                    float(row_data.get("avg_response_time", 0) or 0), 2
                ),
                "success_rate": round(float(row_data.get("success_rate", 0) or 0), 2),
                "total_tokens": int(row_data.get("total_tokens", 0) or 0),
                "task_count": int(row_data.get("task_count", 0) or 0),
            }
        )
    return agents


def _get_collector():
    from tools.performance_collector import PerformanceCollector
    return PerformanceCollector()


def _runtime_gauge_lines() -> list[str]:
    lines: list[str] = []
    flags = get_feature_flags()
    capabilities = {
        role: get_model_capabilities(role)
        for role in sorted({cfg["role"] for cfg in MODELS.values()})
    }
    provider_summary = get_provider_registry_summary()

    lines.append("# HELP runtime_feature_flag_enabled Runtime feature flag state")
    lines.append("# TYPE runtime_feature_flag_enabled gauge")
    for flag_name, enabled in flags.items():
        lines.append(f'runtime_feature_flag_enabled{{flag="{flag_name}"}} {1 if enabled else 0}')
    lines.append("")

    lines.append("# HELP runtime_schema_version_info Runtime event schema version")
    lines.append("# TYPE runtime_schema_version_info gauge")
    lines.append(f'runtime_schema_version_info{{version="{RUNTIME_EVENT_SCHEMA_VERSION}"}} 1')
    lines.append("")

    lines.append("# HELP runtime_model_capability_enabled Model capability state")
    lines.append("# TYPE runtime_model_capability_enabled gauge")
    for role, caps in capabilities.items():
        for cap_name, enabled in caps.items():
            if isinstance(enabled, bool):
                lines.append(
                    f'runtime_model_capability_enabled{{agent="{role}",capability="{cap_name}"}} {1 if enabled else 0}'
                )
    lines.append("")

    lines.append("# HELP runtime_provider_gateway_enabled Gateway routing availability by agent")
    lines.append("# TYPE runtime_provider_gateway_enabled gauge")
    roles = provider_summary.get("roles", {})
    if isinstance(roles, dict):
        for role, item in roles.items():
            if not isinstance(item, dict):
                continue
            lines.append(
                f'runtime_provider_gateway_enabled{{agent="{role}",provider="{item.get("primary_provider", "unknown")}"}} {1 if item.get("gateway_enabled") else 0}'
            )
    lines.append("")
    return lines


def _runtime_failure_analytics() -> dict[str, object]:
    from tools.pg_connection import get_conn, release_conn

    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT
                     COUNT(*) FILTER (WHERE success = FALSE) AS failure_count,
                     COUNT(*) FILTER (
                                WHERE LOWER(COALESCE(metadata->>'fallback_used', 'false')) = 'true'
                     ) AS fallback_usage_count,
                     COUNT(*) FILTER (
                        WHERE metadata->>'event_schema_version' = %s
                     ) AS runtime_v2_adoption_count,
                     COUNT(*) AS total_count
                   FROM agent_metrics_log
                   WHERE recorded_at >= now() - '24 hours'::interval""",
                (RUNTIME_EVENT_SCHEMA_VERSION,),
            )
            totals = _row_dict(cur.fetchone())

            cur.execute(
                """SELECT
                     agent_role,
                     COUNT(*) FILTER (WHERE success = FALSE) AS failure_count,
                     COUNT(*) AS total_count
                   FROM agent_metrics_log
                   WHERE recorded_at >= now() - '24 hours'::interval
                   GROUP BY agent_role
                   ORDER BY failure_count DESC, total_count DESC"""
            )
            rows = cur.fetchall()

        failures_by_agent = []
        for row in rows:
            row_data = _row_dict(row)
            failures_by_agent.append(
                {
                    "agent_role": row_data.get("agent_role", "unknown"),
                    "failure_count": int(row_data.get("failure_count", 0) or 0),
                    "total_count": int(row_data.get("total_count", 0) or 0),
                }
            )

        total_count = int(totals.get("total_count", 0) or 0)
        adoption_count = int(totals.get("runtime_v2_adoption_count", 0) or 0)
        return {
            "period": "24h",
            "failure_count": int(totals.get("failure_count", 0) or 0),
            "fallback_usage_count": int(totals.get("fallback_usage_count", 0) or 0),
            "runtime_v2_adoption_count": adoption_count,
            "runtime_v2_adoption_rate": round((adoption_count / total_count) * 100, 2) if total_count else 0.0,
            "total_count": total_count,
            "failures_by_agent": failures_by_agent,
        }
    except Exception as e:
        logger.error("Runtime failure analytics query failed: %s", e)
        return {"period": "24h", "error": str(e)}
    finally:
        if conn:
            release_conn(conn)


# ── Prometheus Endpoint ───────────────────────────────────────────

@router.get("", response_class=PlainTextResponse)
def get_prometheus_metrics():
    """Prometheus text formatında metrikler."""
    from tools.pg_connection import get_conn, release_conn

    lines = []
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            # Agent metrics (24h)
            cur.execute("""
                SELECT
                    agent_role,
                    COALESCE(AVG(response_time_ms), 0) AS avg_response_time,
                    COALESCE(AVG(success::int) * 100, 0) AS success_rate,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COUNT(*) AS task_count
                FROM agent_metrics_log
                WHERE recorded_at >= now() - '24 hours'::interval
                GROUP BY agent_role
            """)
            agent_rows = cur.fetchall()

            # Total system metrics
            cur.execute("""
                SELECT
                    COUNT(*) AS total_tasks,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(AVG(success::int) * 100, 0) AS success_rate,
                    COALESCE(AVG(response_time_ms), 0) AS avg_response_time
                FROM agent_metrics_log
                WHERE recorded_at >= now() - '24 hours'::interval
            """)
            sys_row = cur.fetchone()

    except Exception as e:
        logger.error("Prometheus metrics query failed: %s", e)
        return f"# ERROR: {e}\n"
    finally:
        if conn:
            release_conn(conn)

    # Agent response time
    lines.append("# HELP agent_response_time_ms Average response time in milliseconds")
    lines.append("# TYPE agent_response_time_ms gauge")
    for row in agent_rows:
        row_data = _row_dict(row)
        lines.append(
            f'agent_response_time_ms{{agent="{row_data.get("agent_role", "unknown")}"}} {float(row_data.get("avg_response_time", 0) or 0):.2f}'
        )
    lines.append("")

    # Agent success rate
    lines.append("# HELP agent_success_rate_percent Success rate percentage")
    lines.append("# TYPE agent_success_rate_percent gauge")
    for row in agent_rows:
        row_data = _row_dict(row)
        lines.append(
            f'agent_success_rate_percent{{agent="{row_data.get("agent_role", "unknown")}"}} {float(row_data.get("success_rate", 0) or 0):.2f}'
        )
    lines.append("")

    # Agent task count
    lines.append("# HELP agent_tasks_total Total tasks processed")
    lines.append("# TYPE agent_tasks_total counter")
    for row in agent_rows:
        row_data = _row_dict(row)
        lines.append(
            f'agent_tasks_total{{agent="{row_data.get("agent_role", "unknown")}"}} {int(row_data.get("task_count", 0) or 0)}'
        )
    lines.append("")

    # Agent tokens
    lines.append("# HELP agent_tokens_total Total tokens used")
    lines.append("# TYPE agent_tokens_total counter")
    for row in agent_rows:
        row_data = _row_dict(row)
        lines.append(
            f'agent_tokens_total{{agent="{row_data.get("agent_role", "unknown")}"}} {int(row_data.get("total_tokens", 0) or 0)}'
        )
    lines.append("")

    # System metrics
    sys_data = _row_dict(sys_row)
    if sys_data:
        lines.append("# HELP system_tasks_total Total system tasks in 24h")
        lines.append("# TYPE system_tasks_total counter")
        lines.append(f"system_tasks_total {int(sys_data.get('total_tasks', 0) or 0)}")
        lines.append("")

        lines.append("# HELP system_tokens_total Total system tokens in 24h")
        lines.append("# TYPE system_tokens_total counter")
        lines.append(f"system_tokens_total {int(sys_data.get('total_tokens', 0) or 0)}")
        lines.append("")

        lines.append("# HELP system_success_rate_percent Overall success rate")
        lines.append("# TYPE system_success_rate_percent gauge")
        lines.append(
            f"system_success_rate_percent {float(sys_data.get('success_rate', 0) or 0):.2f}"
        )
        lines.append("")

        lines.append("# HELP system_avg_response_time_ms Average system response time")
        lines.append("# TYPE system_avg_response_time_ms gauge")
        lines.append(
            f"system_avg_response_time_ms {float(sys_data.get('avg_response_time', 0) or 0):.2f}"
        )
        lines.append("")

    # Uptime metric
    lines.append("# HELP agent_dashboard_up Dashboard availability")
    lines.append("# TYPE agent_dashboard_up gauge")
    lines.append("agent_dashboard_up 1")
    lines.append("")

    lines.extend(_runtime_gauge_lines())

    return "\n".join(lines)


# ── JSON Endpoints ───────────────────────────────────────────────


@router.get("/agents")
def get_all_agents_metrics(period: str = Query("24h")):
    """Tüm agent'ların özet performans metrikleri."""
    if period not in VALID_PERIODS:
        raise HTTPException(400, f"Invalid period '{period}'. Valid: {', '.join(sorted(VALID_PERIODS))}")

    from tools.pg_connection import get_conn, release_conn

    interval = PERIOD_MAP[period]
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT
                     agent_role,
                     COALESCE(AVG(response_time_ms), 0)   AS avg_response_time,
                     COALESCE(AVG(success::int) * 100, 0)  AS success_rate,
                     COALESCE(SUM(total_tokens), 0)        AS total_tokens,
                     COUNT(*)                               AS task_count
                   FROM agent_metrics_log
                   WHERE recorded_at >= now() - %s::interval
                   GROUP BY agent_role
                   ORDER BY task_count DESC""",
                (interval,),
            )
            rows = cur.fetchall()

        return {"period": period, "agents": _agent_metrics_payload(rows)}
    except Exception as e:
        logger.error("All agents metrics query failed: %s", e)
        raise HTTPException(500, f"Metrics query failed: {e}")
    finally:
        if conn:
            release_conn(conn)


@router.get("/agents/{agent_role}")
def get_agent_metrics(agent_role: str, period: str = Query("24h")):
    """Belirli bir agent'ın detaylı performans metrikleri."""
    if agent_role not in VALID_ROLES:
        raise HTTPException(
            404,
            f"Agent role '{agent_role}' not found. Valid roles: {', '.join(sorted(VALID_ROLES))}",
        )
    if period not in VALID_PERIODS:
        raise HTTPException(400, f"Invalid period '{period}'. Valid: {', '.join(sorted(VALID_PERIODS))}")

    collector = _get_collector()
    return collector.get_agent_summary(agent_role, period)


@router.get("/system")
def get_system_metrics():
    """Sistem geneli metrikler: toplam token, görev sayısı, uptime, tahmini maliyet."""
    collector = _get_collector()
    system_summary = collector.get_system_summary()
    system_summary["cost_estimate"] = system_summary.get("cost_estimate_usd", 0)
    system_summary["runtime"] = {
        "schema_version": RUNTIME_EVENT_SCHEMA_VERSION,
        "feature_flags": get_feature_flags(),
        "provider_registry": get_provider_registry_summary(),
        "capabilities": {
            role: get_model_capabilities(role)
            for role in sorted(VALID_ROLES)
        },
    }
    system_summary["failure_analytics"] = _runtime_failure_analytics()
    return system_summary
