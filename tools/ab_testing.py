"""
A/B Test Manager — Faz 16: Self-Improvement Loop.
Manages A/B experiments for prompt strategies.
Deterministic variant assignment, Welch's t-test significance check.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ab_testing")


class ABTestManager:
    """Manages A/B experiments for prompt strategies."""

    def __init__(self):
        self._initialized = False

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
                    CREATE TABLE IF NOT EXISTS ab_experiments (
                        id SERIAL PRIMARY KEY,
                        experiment_id VARCHAR(64) UNIQUE NOT NULL,
                        agent_role VARCHAR(32) NOT NULL,
                        task_type VARCHAR(64) NOT NULL,
                        control_strategy_id INTEGER,
                        variant_strategy_id INTEGER,
                        traffic_split REAL DEFAULT 0.5 CHECK (traffic_split BETWEEN 0 AND 1),
                        status VARCHAR(16) DEFAULT 'active',
                        winner VARCHAR(16) DEFAULT NULL,
                        p_value REAL DEFAULT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        concluded_at TIMESTAMPTZ DEFAULT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ab_experiment_results (
                        id SERIAL PRIMARY KEY,
                        experiment_id VARCHAR(64) NOT NULL,
                        variant VARCHAR(16) NOT NULL,
                        score REAL NOT NULL,
                        latency_ms REAL DEFAULT 0,
                        tokens_used INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_abr_exp ON ab_experiment_results(experiment_id)")
            conn.commit()
            self._release(conn)
            self._initialized = True
        except Exception as e:
            logger.warning(f"ab_experiments table init failed: {e}")

    def create_experiment(
        self,
        experiment_id: str,
        agent_role: str,
        task_type: str,
        control_strategy_id: int,
        variant_strategy_id: int,
        traffic_split: float = 0.5,
    ) -> dict:
        """Create new experiment. Fails if active experiment exists for role+task."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM ab_experiments WHERE agent_role = %s AND task_type = %s AND status = 'active'",
                    (agent_role, task_type),
                )
                row = cur.fetchone()
                if row and row["cnt"] > 0:
                    raise ValueError(f"Active experiment already exists for {agent_role}/{task_type}")

                cur.execute(
                    """INSERT INTO ab_experiments
                       (experiment_id, agent_role, task_type, control_strategy_id, variant_strategy_id, traffic_split)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       RETURNING id, created_at""",
                    (experiment_id, agent_role, task_type, control_strategy_id, variant_strategy_id, traffic_split),
                )
                result = cur.fetchone()
            conn.commit()
            logger.info(f"A/B experiment created: {experiment_id} for {agent_role}/{task_type}")
            return {
                "id": result["id"],
                "experiment_id": experiment_id,
                "agent_role": agent_role,
                "task_type": task_type,
                "control_strategy_id": control_strategy_id,
                "variant_strategy_id": variant_strategy_id,
                "traffic_split": traffic_split,
                "status": "active",
                "created_at": result["created_at"].isoformat() if result["created_at"] else None,
            }
        finally:
            self._release(conn)

    def assign_variant(self, experiment_id: str, task_id: str) -> str:
        """Deterministic variant assignment via hash(experiment_id + task_id) % 100."""
        self._ensure_table()
        # Get traffic split
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT traffic_split FROM ab_experiments WHERE experiment_id = %s AND status = 'active'",
                    (experiment_id,),
                )
                row = cur.fetchone()
            if not row:
                return "control"  # Default fallback
            split = float(row["traffic_split"])
        finally:
            self._release(conn)

        hash_val = int(hashlib.md5(f"{experiment_id}:{task_id}".encode()).hexdigest(), 16)
        return "control" if (hash_val % 100) < (split * 100) else "variant"

    def record_result(
        self,
        experiment_id: str,
        variant: str,
        score: float,
        latency_ms: float = 0,
        tokens_used: int = 0,
    ) -> None:
        """Record sample result + auto-check significance if min samples reached."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO ab_experiment_results
                       (experiment_id, variant, score, latency_ms, tokens_used)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (experiment_id, variant, score, latency_ms, tokens_used),
                )
            conn.commit()
        finally:
            self._release(conn)

        # Auto-check significance
        try:
            result = self.check_significance(experiment_id)
            if result and result.get("significant"):
                self.conclude_experiment(experiment_id, result["winner"], result["p_value"])
        except Exception as e:
            logger.debug(f"Auto-significance check failed (non-fatal): {e}")

    def check_significance(self, experiment_id: str) -> dict | None:
        """Two-sample Welch's t-test. Returns {winner, p_value} if p < 0.05 and n >= 30."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT score FROM ab_experiment_results WHERE experiment_id = %s AND variant = 'control'",
                    (experiment_id,),
                )
                control_scores = [float(r["score"]) for r in cur.fetchall()]

                cur.execute(
                    "SELECT score FROM ab_experiment_results WHERE experiment_id = %s AND variant = 'variant'",
                    (experiment_id,),
                )
                variant_scores = [float(r["score"]) for r in cur.fetchall()]
            self._release(conn)
        except Exception:
            self._release(conn)
            return None

        if len(control_scores) < 30 or len(variant_scores) < 30:
            return {
                "significant": False,
                "reason": f"Insufficient samples: control={len(control_scores)}, variant={len(variant_scores)} (need 30+)",
                "control_n": len(control_scores),
                "variant_n": len(variant_scores),
            }

        try:
            from scipy.stats import ttest_ind
            t_stat, p_value = ttest_ind(control_scores, variant_scores, equal_var=False)
        except ImportError:
            # Fallback: manual Welch's t-test
            import math
            n1, n2 = len(control_scores), len(variant_scores)
            m1 = sum(control_scores) / n1
            m2 = sum(variant_scores) / n2
            v1 = sum((x - m1) ** 2 for x in control_scores) / (n1 - 1) if n1 > 1 else 0
            v2 = sum((x - m2) ** 2 for x in variant_scores) / (n2 - 1) if n2 > 1 else 0
            se = math.sqrt(v1 / n1 + v2 / n2) if (v1 / n1 + v2 / n2) > 0 else 1e-10
            t_stat = (m1 - m2) / se
            # Approximate p-value (two-tailed) using normal distribution for large n
            z = abs(t_stat)
            p_value = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))

        control_mean = sum(control_scores) / len(control_scores)
        variant_mean = sum(variant_scores) / len(variant_scores)
        winner = "control" if control_mean >= variant_mean else "variant"

        significant = p_value < 0.05
        return {
            "significant": significant,
            "winner": winner if significant else None,
            "p_value": round(p_value, 6),
            "t_stat": round(t_stat, 4),
            "control_mean": round(control_mean, 3),
            "variant_mean": round(variant_mean, 3),
            "control_n": len(control_scores),
            "variant_n": len(variant_scores),
        }

    def conclude_experiment(self, experiment_id: str, winner: str, p_value: float) -> None:
        """Mark concluded + publish EXPERIMENT_CONCLUDED event."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE ab_experiments
                       SET status = 'concluded', winner = %s, p_value = %s, concluded_at = NOW()
                       WHERE experiment_id = %s AND status = 'active'""",
                    (winner, p_value, experiment_id),
                )
            conn.commit()
            logger.info(f"A/B experiment concluded: {experiment_id} winner={winner} p={p_value}")
        finally:
            self._release(conn)

        # Publish event (fire-and-forget)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._publish_concluded_event(experiment_id, winner, p_value))
        except Exception:
            pass

    async def _publish_concluded_event(self, experiment_id: str, winner: str, p_value: float) -> None:
        """Publish EXPERIMENT_CONCLUDED event to event bus."""
        try:
            from core.event_bus import get_event_bus
            from core.protocols import MessageType as MT, MessageEnvelope, ChannelType, DeliveryGuarantee
            bus = get_event_bus()
            msg = MessageEnvelope(
                source_agent="ab_testing",
                channel="experiments",
                channel_type=ChannelType.MULTICAST,
                message_type=MT.BROADCAST,
                payload={
                    "event": "experiment_concluded",
                    "experiment_id": experiment_id,
                    "winner": winner,
                    "p_value": p_value,
                },
                delivery=DeliveryGuarantee.AT_LEAST_ONCE,
            )
            await bus.publish(msg)
        except Exception as e:
            logger.debug(f"Bus publish failed (non-fatal): {e}")

    def get_experiment(self, experiment_id: str) -> dict | None:
        """Get experiment details."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM ab_experiments WHERE experiment_id = %s", (experiment_id,))
                row = cur.fetchone()
            return dict(row) if row else None
        finally:
            self._release(conn)

    def list_experiments(self, status: str | None = None) -> list[dict]:
        """List experiments with optional status filter."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                if status:
                    cur.execute("SELECT * FROM ab_experiments WHERE status = %s ORDER BY created_at DESC", (status,))
                else:
                    cur.execute("SELECT * FROM ab_experiments ORDER BY created_at DESC")
                rows = cur.fetchall()
            return [self._row_to_dict(dict(r)) for r in rows]
        finally:
            self._release(conn)

    @staticmethod
    def _row_to_dict(row: dict) -> dict:
        for key in ("created_at", "concluded_at"):
            if key in row and hasattr(row[key], "isoformat"):
                row[key] = row[key].isoformat()
        return row


# ── Singleton ────────────────────────────────────────────────────

_instance: ABTestManager | None = None


def get_ab_test_manager() -> ABTestManager:
    global _instance
    if _instance is None:
        _instance = ABTestManager()
    return _instance
