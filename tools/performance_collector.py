"""
Performance Collector — Faz 16: Self-Improvement Loop.
Records agent performance metrics to PostgreSQL and publishes events to EventBus.
Maintains 24h rolling in-memory cache for low-latency queries.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("performance_collector")


class PerformanceCollector:
    """Collects agent performance metrics after each subtask execution."""

    def __init__(self):
        self._cache: deque[dict] = deque(maxlen=5000)
        self._initialized = False

    def _get_conn(self):
        from tools.pg_connection import get_pg_connection
        return get_pg_connection()

    def _ensure_table(self):
        if self._initialized:
            return
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id SERIAL PRIMARY KEY,
                        agent_role VARCHAR(32) NOT NULL,
                        task_type VARCHAR(64) NOT NULL,
                        score REAL NOT NULL,
                        latency_ms REAL DEFAULT 0,
                        tokens_used INTEGER DEFAULT 0,
                        skill_ids_used TEXT[] DEFAULT '{}',
                        prompt_strategy_id INTEGER DEFAULT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_perf_agent ON performance_metrics(agent_role)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_perf_task ON performance_metrics(task_type)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_perf_created ON performance_metrics(created_at)")
            conn.commit()
            conn.close()
            self._initialized = True
        except Exception as e:
            logger.warning(f"performance_metrics table init failed: {e}")

    def record(
        self,
        agent_role: str,
        task_type: str,
        score: float,
        latency_ms: float = 0,
        tokens_used: int = 0,
        skill_ids_used: list[str] | None = None,
        prompt_strategy_id: int | None = None,
    ) -> dict:
        """Record a performance metric synchronously. Returns the recorded entry."""
        self._ensure_table()
        skill_ids = skill_ids_used or []
        entry = {
            "agent_role": agent_role,
            "task_type": task_type,
            "score": score,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "skill_ids_used": skill_ids,
            "prompt_strategy_id": prompt_strategy_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Persist to PostgreSQL
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO performance_metrics
                       (agent_role, task_type, score, latency_ms, tokens_used, skill_ids_used, prompt_strategy_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (agent_role, task_type, score, latency_ms, tokens_used, skill_ids, prompt_strategy_id),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist metric: {e}")

        # Add to rolling cache
        self._cache.append(entry)

        # Publish event to bus (fire-and-forget, non-blocking)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._publish_metric_event(entry))
        except Exception:
            pass  # Bus publish failure never breaks collection

        logger.debug(f"Metric recorded: {agent_role}/{task_type} score={score:.2f}")
        return entry

    async def _publish_metric_event(self, entry: dict) -> None:
        """Publish METRIC_RECORDED event to event bus."""
        try:
            from core.event_bus import get_event_bus
            from core.protocols import MessageType as MT, MessageEnvelope, ChannelType, DeliveryGuarantee
            bus = get_event_bus()
            msg = MessageEnvelope(
                source_agent="performance_collector",
                channel="metrics",
                channel_type=ChannelType.MULTICAST,
                message_type=MT.BROADCAST,
                payload={"event": "metric_recorded", **entry},
                delivery=DeliveryGuarantee.AT_LEAST_ONCE,
            )
            await bus.publish(msg)
        except Exception as e:
            logger.debug(f"Bus publish failed (non-fatal): {e}")

    def get_agent_stats(self, agent_role: str) -> dict[str, Any]:
        """Aggregated stats for an agent: avg_score, success_rate, avg_latency, per-task breakdown."""
        self._ensure_table()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                # Overall stats
                cur.execute("""
                    SELECT COUNT(*) as total, AVG(score) as avg_score,
                           AVG(latency_ms) as avg_latency, SUM(tokens_used) as total_tokens
                    FROM performance_metrics WHERE agent_role = %s
                """, (agent_role,))
                row = cur.fetchone()
                total = row["total"] if row else 0
                avg_score = float(row["avg_score"] or 0) if row else 0
                avg_latency = float(row["avg_latency"] or 0) if row else 0
                total_tokens = int(row["total_tokens"] or 0) if row else 0

                # Success rate (score >= 3.0 considered success)
                cur.execute("""
                    SELECT COUNT(*) as success_count
                    FROM performance_metrics WHERE agent_role = %s AND score >= 3.0
                """, (agent_role,))
                success_row = cur.fetchone()
                success_count = success_row["success_count"] if success_row else 0
                success_rate = success_count / max(total, 1)

                # Per-task breakdown
                cur.execute("""
                    SELECT task_type, COUNT(*) as count, AVG(score) as avg_score,
                           AVG(latency_ms) as avg_latency
                    FROM performance_metrics WHERE agent_role = %s
                    GROUP BY task_type ORDER BY count DESC
                """, (agent_role,))
                breakdown = [
                    {
                        "task_type": r["task_type"],
                        "count": r["count"],
                        "avg_score": round(float(r["avg_score"] or 0), 2),
                        "avg_latency_ms": round(float(r["avg_latency"] or 0), 1),
                    }
                    for r in cur.fetchall()
                ]
            conn.close()
            return {
                "agent_role": agent_role,
                "total_tasks": total,
                "avg_score": round(avg_score, 2),
                "success_rate": round(success_rate, 3),
                "avg_latency_ms": round(avg_latency, 1),
                "total_tokens": total_tokens,
                "per_task_type": breakdown,
            }
        except Exception as e:
            logger.error(f"get_agent_stats failed: {e}")
            return {"agent_role": agent_role, "total_tasks": 0, "error": str(e)}

    def get_skill_stats(self, skill_id: str) -> dict[str, Any]:
        """Skill usage stats: total_uses, avg_score_when_used, per-agent breakdown."""
        self._ensure_table()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as total, AVG(score) as avg_score
                    FROM performance_metrics WHERE %s = ANY(skill_ids_used)
                """, (skill_id,))
                row = cur.fetchone()
                total = row["total"] if row else 0
                avg_score = float(row["avg_score"] or 0) if row else 0

                cur.execute("""
                    SELECT agent_role, COUNT(*) as count, AVG(score) as avg_score
                    FROM performance_metrics WHERE %s = ANY(skill_ids_used)
                    GROUP BY agent_role ORDER BY count DESC
                """, (skill_id,))
                breakdown = [
                    {
                        "agent_role": r["agent_role"],
                        "count": r["count"],
                        "avg_score": round(float(r["avg_score"] or 0), 2),
                    }
                    for r in cur.fetchall()
                ]
            conn.close()
            return {
                "skill_id": skill_id,
                "total_uses": total,
                "avg_score_when_used": round(avg_score, 2),
                "per_agent": breakdown,
            }
        except Exception as e:
            logger.error(f"get_skill_stats failed: {e}")
            return {"skill_id": skill_id, "total_uses": 0, "error": str(e)}

    def get_recent_metrics(self, agent_role: str = None, limit: int = 50) -> list[dict]:
        """Get recent metrics from in-memory cache."""
        items = list(self._cache)
        if agent_role:
            items = [m for m in items if m["agent_role"] == agent_role]
        return items[-limit:]


# ── Singleton ────────────────────────────────────────────────────

_instance: PerformanceCollector | None = None


def get_performance_collector() -> PerformanceCollector:
    global _instance
    if _instance is None:
        _instance = PerformanceCollector()
    return _instance
