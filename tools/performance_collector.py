"""
Performance Metrics Collector — agent bazlı performans ölçümleri.

Her agent çağrısının response_time, token kullanımı, başarı durumu
agent_metrics_log tablosuna kaydedilir. DB hatalarında in-memory buffer'a düşer.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from core.event_bus import EventBus, get_event_bus
from core.protocols import (
    ChannelType,
    DeliveryGuarantee,
    MessageEnvelope,
    MessagePriority,
    MessageType,
)
from tools.pg_connection import get_conn, release_conn, db_conn

logger = logging.getLogger(__name__)

# Period → PostgreSQL interval mapping
PERIOD_MAP: dict[str, str] = {
    "1h": "1 hour",
    "24h": "24 hours",
    "7d": "7 days",
}

# Default cost: $0.002 per 1K tokens
DEFAULT_COST_PER_1K = 0.002


@dataclass
class MetricRecord:
    """In-memory buffer entry."""
    agent_role: str
    response_time_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    success: bool = True
    model_name: str | None = None
    skill_id: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PerformanceCollector:
    """
    Agent performans metriklerini toplar ve raporlar.

    - record(): metriği DB'ye yazar, hata olursa buffer'a alır
    - flush_buffer(): buffer'daki metrikleri toplu DB'ye yazar
    - get_agent_summary(): agent bazlı özet istatistik
    - get_system_summary(): sistem geneli özet
    """

    def __init__(
        self,
        pool: Any | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._pool = pool  # reserved for future pool injection
        self._event_bus = event_bus or get_event_bus()
        self._buffer: list[MetricRecord] = []
        self._start_time = time.time()

    # ── Record ───────────────────────────────────────────────────

    def record(
        self,
        agent_role: str,
        response_time_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        success: bool = True,
        model_name: str | None = None,
        skill_id: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Metriği DB'ye kaydet. Hata olursa buffer'a al."""
        import json

        meta_json = json.dumps(metadata or {})
        conn = None
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO agent_metrics_log
                       (agent_role, response_time_ms, input_tokens, output_tokens,
                        total_tokens, success, model_name, skill_id, error_message, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)""",
                    (
                        agent_role, response_time_ms, input_tokens, output_tokens,
                        total_tokens, success, model_name, skill_id, error_message,
                        meta_json,
                    ),
                )
            conn.commit()
            self._publish_event(agent_role, response_time_ms, total_tokens, success)
            return True
        except Exception as e:
            logger.warning(f"DB write failed, buffering metric: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            self._buffer.append(
                MetricRecord(
                    agent_role=agent_role,
                    response_time_ms=response_time_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    success=success,
                    model_name=model_name,
                    skill_id=skill_id,
                    error_message=error_message,
                    metadata=metadata or {},
                )
            )
            return False
        finally:
            if conn:
                release_conn(conn)

    # ── Flush Buffer ─────────────────────────────────────────────

    def flush_buffer(self) -> int:
        """Buffer'daki metrikleri toplu DB'ye yaz. Başarılı kayıt sayısını döner."""
        if not self._buffer:
            return 0

        import json

        conn = None
        flushed = 0
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                for rec in self._buffer:
                    cur.execute(
                        """INSERT INTO agent_metrics_log
                           (agent_role, response_time_ms, input_tokens, output_tokens,
                            total_tokens, success, model_name, skill_id, error_message, metadata)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)""",
                        (
                            rec.agent_role, rec.response_time_ms, rec.input_tokens,
                            rec.output_tokens, rec.total_tokens, rec.success,
                            rec.model_name, rec.skill_id, rec.error_message,
                            json.dumps(rec.metadata),
                        ),
                    )
                    flushed += 1
            conn.commit()
            self._buffer.clear()
            logger.info(f"Flushed {flushed} buffered metrics to DB")
        except Exception as e:
            logger.error(f"Buffer flush failed: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            flushed = 0
        finally:
            if conn:
                release_conn(conn)
        return flushed

    # ── Agent Summary ────────────────────────────────────────────

    def get_agent_summary(
        self, agent_role: str, period: str = "24h"
    ) -> dict[str, Any]:
        """Agent bazlı özet: avg response time, success rate, token count, task count."""
        interval = PERIOD_MAP.get(period, "24 hours")
        try:
            with db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT
                             COALESCE(AVG(response_time_ms), 0)       AS avg_response_time,
                             COALESCE(AVG(success::int) * 100, 0)     AS success_rate,
                             COALESCE(SUM(total_tokens), 0)           AS total_tokens,
                             COUNT(*)                                  AS task_count
                           FROM agent_metrics_log
                           WHERE agent_role = %s
                             AND recorded_at >= now() - %s::interval""",
                        (agent_role, interval),
                    )
                    row = cur.fetchone()
            return {
                "agent_role": agent_role,
                "period": period,
                "avg_response_time": round(float(row["avg_response_time"]), 2),
                "success_rate": round(float(row["success_rate"]), 2),
                "total_tokens": int(row["total_tokens"]),
                "task_count": int(row["task_count"]),
            }
        except Exception as e:
            logger.error(f"Agent summary query failed: {e}")
            return {
                "agent_role": agent_role,
                "period": period,
                "avg_response_time": 0,
                "success_rate": 0,
                "total_tokens": 0,
                "task_count": 0,
                "error": str(e),
            }

    # ── System Summary ───────────────────────────────────────────

    def get_system_summary(self) -> dict[str, Any]:
        """Sistem geneli özet: toplam token, görev, uptime, tahmini maliyet."""
        try:
            with db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT
                             COALESCE(SUM(total_tokens), 0) AS total_tokens,
                             COUNT(*)                        AS total_tasks
                           FROM agent_metrics_log"""
                    )
                    row = cur.fetchone()
            total_tokens = int(row["total_tokens"])
            total_tasks = int(row["total_tasks"])
            uptime = time.time() - self._start_time
            cost_estimate = round(total_tokens / 1000 * DEFAULT_COST_PER_1K, 4)
            return {
                "total_tokens": total_tokens,
                "total_tasks": total_tasks,
                "uptime_seconds": round(uptime, 1),
                "cost_estimate_usd": cost_estimate,
            }
        except Exception as e:
            logger.error(f"System summary query failed: {e}")
            return {
                "total_tokens": 0,
                "total_tasks": 0,
                "uptime_seconds": round(time.time() - self._start_time, 1),
                "cost_estimate_usd": 0,
                "error": str(e),
            }

    # ── Event Publishing ─────────────────────────────────────────

    def _publish_event(
        self,
        agent_role: str,
        response_time_ms: float,
        total_tokens: int,
        success: bool,
    ) -> None:
        """metrics.recorded event'ini EventBus'a yayınla (fire-and-forget)."""
        try:
            envelope = MessageEnvelope(
                source_agent="performance_collector",
                channel="metrics.recorded",
                channel_type=ChannelType.MULTICAST,
                message_type=MessageType.TASK_PROGRESS,
                priority=MessagePriority.LOW,
                delivery=DeliveryGuarantee.AT_MOST_ONCE,
                payload={
                    "agent_role": agent_role,
                    "response_time_ms": response_time_ms,
                    "total_tokens": total_tokens,
                    "success": success,
                },
            )
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._event_bus.publish(envelope))
            else:
                loop.run_until_complete(self._event_bus.publish(envelope))
        except RuntimeError:
            # No event loop — skip silently (CLI / test context)
            pass
        except Exception as e:
            logger.debug(f"Event publish skipped: {e}")

    # ── Buffer Info ──────────────────────────────────────────────

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)
