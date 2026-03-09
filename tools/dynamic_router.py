"""
Dynamic Router — Faz 16: Self-Improvement Loop.
Performance-based agent routing with softmax weights and exploration-exploitation balance.
"""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Any

logger = logging.getLogger("dynamic_router")


class DynamicRouter:
    """Performance-based agent routing with exploration-exploitation balance."""

    RECALC_TASK_INTERVAL = 50
    RECALC_TIME_INTERVAL = 3600  # 1 hour

    def __init__(self):
        self._initialized = False
        self._weights: dict[str, dict[str, float]] = {}  # task_type → {agent → weight}
        self._task_counter = 0
        self._last_recalc = time.time()
        self.exploration_rate = 0.1

    def _get_conn(self):
        from tools.pg_connection import get_conn
        return get_conn()

    def _release(self, conn):
        from tools.pg_connection import release_conn
        release_conn(conn)


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
            conn.commit()
            self._release(conn)
            self._initialized = True
        except Exception as e:
            logger.warning(f"dynamic_router table check failed: {e}")

    def route(self, task_type: str) -> str | None:
        """
        Select best agent for task_type.
        With probability exploration_rate, pick random agent.
        Otherwise pick highest Routing_Weight agent.
        """
        self._ensure_table()
        self._task_counter += 1

        # Check if recalculation needed
        needs_recalc = (
            self._task_counter % self.RECALC_TASK_INTERVAL == 0
            or (time.time() - self._last_recalc) > self.RECALC_TIME_INTERVAL
            or task_type not in self._weights
        )
        if needs_recalc:
            self.recalculate_weights(task_type)

        weights = self._weights.get(task_type, {})
        if not weights:
            return None

        # Exploration: random agent
        if random.random() < self.exploration_rate:
            return random.choice(list(weights.keys()))

        # Exploitation: highest weight
        return max(weights, key=weights.get)

    def recalculate_weights(self, task_type: str | None = None) -> None:
        """
        Agent_Performance_Score = 0.4×success_rate + 0.25×norm_avg_score
                                + 0.2×latency_efficiency + 0.15×token_efficiency
        Routing_Weight = softmax(Agent_Performance_Scores)
        Publish ROUTING_WEIGHT_LOW if any weight < 0.05.
        """
        self._ensure_table()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                # Get all task types if not specified
                if task_type:
                    task_types = [task_type]
                else:
                    cur.execute("SELECT DISTINCT task_type FROM performance_metrics")
                    task_types = [r["task_type"] for r in cur.fetchall()]

                for tt in task_types:
                    cur.execute("""
                        SELECT agent_role,
                               COUNT(*) as total,
                               SUM(CASE WHEN score >= 3.0 THEN 1 ELSE 0 END) as success_count,
                               AVG(score) as avg_score,
                               AVG(latency_ms) as avg_latency,
                               AVG(tokens_used) as avg_tokens
                        FROM performance_metrics
                        WHERE task_type = %s
                        GROUP BY agent_role
                    """, (tt,))
                    rows = cur.fetchall()

                    if not rows:
                        continue

                    scores: dict[str, float] = {}
                    for row in rows:
                        total = int(row["total"] or 0)
                        success_rate = int(row["success_count"] or 0) / max(total, 1)
                        norm_avg_score = float(row["avg_score"] or 0) / 5.0
                        latency_eff = 1.0 - min(float(row["avg_latency"] or 0) / 30000.0, 1.0)
                        token_eff = 1.0 - min(float(row["avg_tokens"] or 0) / 10000.0, 1.0)

                        aps = (
                            0.4 * success_rate
                            + 0.25 * norm_avg_score
                            + 0.2 * latency_eff
                            + 0.15 * token_eff
                        )
                        scores[row["agent_role"]] = aps

                    if scores:
                        self._weights[tt] = self._softmax(scores)

                        # Check for low weights
                        for agent, weight in self._weights[tt].items():
                            if weight < 0.05:
                                self._publish_low_weight(agent, tt, weight)

            self._release(conn)
            self._last_recalc = time.time()
        except Exception as e:
            logger.error(f"recalculate_weights failed: {e}")

    def _softmax(self, scores: dict[str, float]) -> dict[str, float]:
        """Softmax normalization."""
        if not scores:
            return {}
        max_s = max(scores.values())
        exps = {k: math.exp(v - max_s) for k, v in scores.items()}
        total = sum(exps.values())
        if total == 0:
            n = len(scores)
            return {k: 1.0 / n for k in scores}
        return {k: v / total for k, v in exps.items()}

    def _publish_low_weight(self, agent_role: str, task_type: str, weight: float) -> None:
        """Publish ROUTING_WEIGHT_LOW event (fire-and-forget)."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._async_publish_low_weight(agent_role, task_type, weight))
        except Exception:
            pass

    async def _async_publish_low_weight(self, agent_role: str, task_type: str, weight: float) -> None:
        try:
            from core.event_bus import get_event_bus
            from core.protocols import MessageType as MT, MessageEnvelope, ChannelType, DeliveryGuarantee
            bus = get_event_bus()
            msg = MessageEnvelope(
                source_agent="dynamic_router",
                channel="optimization",
                channel_type=ChannelType.MULTICAST,
                message_type=MT.BROADCAST,
                payload={
                    "event": "routing_weight_low",
                    "agent_role": agent_role,
                    "task_type": task_type,
                    "weight": weight,
                },
                delivery=DeliveryGuarantee.AT_MOST_ONCE,
            )
            await bus.publish(msg)
        except Exception as e:
            logger.debug(f"Low weight publish failed (non-fatal): {e}")

    def get_weights(self) -> dict[str, dict[str, float]]:
        """Return current routing weights for all task types."""
        return dict(self._weights)

    def get_weights_for_task(self, task_type: str) -> dict[str, float]:
        """Return routing weights for a specific task type."""
        if task_type not in self._weights:
            self.recalculate_weights(task_type)
        return self._weights.get(task_type, {})


# ── Singleton ────────────────────────────────────────────────────

_instance: DynamicRouter | None = None


def get_dynamic_router() -> DynamicRouter:
    global _instance
    if _instance is None:
        _instance = DynamicRouter()
    return _instance
