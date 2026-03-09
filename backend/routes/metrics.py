"""
Performance Metrics API — agent bazlı ve sistem geneli metrik endpoint'leri.
"""

import logging
import sys
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

VALID_PERIODS = {"1h", "24h", "7d"}
VALID_ROLES = {"orchestrator", "thinker", "speed", "researcher", "reasoner", "critic"}
PERIOD_MAP = {"1h": "1 hour", "24h": "24 hours", "7d": "7 days"}


def _get_collector():
    from tools.performance_collector import PerformanceCollector
    return PerformanceCollector()


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
        lines.append(f'agent_response_time_ms{{agent="{row["agent_role"]}"}} {row["avg_response_time"]:.2f}')
    lines.append("")

    # Agent success rate
    lines.append("# HELP agent_success_rate_percent Success rate percentage")
    lines.append("# TYPE agent_success_rate_percent gauge")
    for row in agent_rows:
        lines.append(f'agent_success_rate_percent{{agent="{row["agent_role"]}"}} {row["success_rate"]:.2f}')
    lines.append("")

    # Agent task count
    lines.append("# HELP agent_tasks_total Total tasks processed")
    lines.append("# TYPE agent_tasks_total counter")
    for row in agent_rows:
        lines.append(f'agent_tasks_total{{agent="{row["agent_role"]}"}} {row["task_count"]}')
    lines.append("")

    # Agent tokens
    lines.append("# HELP agent_tokens_total Total tokens used")
    lines.append("# TYPE agent_tokens_total counter")
    for row in agent_rows:
        lines.append(f'agent_tokens_total{{agent="{row["agent_role"]}"}} {row["total_tokens"]}')
    lines.append("")

    # System metrics
    if sys_row:
        lines.append("# HELP system_tasks_total Total system tasks in 24h")
        lines.append("# TYPE system_tasks_total counter")
        lines.append(f"system_tasks_total {sys_row['total_tasks']}")
        lines.append("")

        lines.append("# HELP system_tokens_total Total system tokens in 24h")
        lines.append("# TYPE system_tokens_total counter")
        lines.append(f"system_tokens_total {sys_row['total_tokens']}")
        lines.append("")

        lines.append("# HELP system_success_rate_percent Overall success rate")
        lines.append("# TYPE system_success_rate_percent gauge")
        lines.append(f"system_success_rate_percent {sys_row['success_rate']:.2f}")
        lines.append("")

        lines.append("# HELP system_avg_response_time_ms Average system response time")
        lines.append("# TYPE system_avg_response_time_ms gauge")
        lines.append(f"system_avg_response_time_ms {sys_row['avg_response_time']:.2f}")
        lines.append("")

    # Uptime metric
    lines.append("# HELP agent_dashboard_up Dashboard availability")
    lines.append("# TYPE agent_dashboard_up gauge")
    lines.append("agent_dashboard_up 1")
    lines.append("")

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

        return {
            "period": period,
            "agents": [
                {
                    "agent_role": r["agent_role"],
                    "avg_response_time": round(float(r["avg_response_time"]), 2),
                    "success_rate": round(float(r["success_rate"]), 2),
                    "total_tokens": int(r["total_tokens"]),
                    "task_count": int(r["task_count"]),
                }
                for r in rows
            ],
        }
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
    return collector.get_system_summary()
