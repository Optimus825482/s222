"""
Performance Metrics API — agent bazlı ve sistem geneli metrik endpoint'leri.
"""

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

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


# ── Endpoints ────────────────────────────────────────────────────


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
