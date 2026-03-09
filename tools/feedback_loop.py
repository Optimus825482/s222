"""
Feedback Loop — Faz 16: Self-Improvement Loop.
Closed-loop optimization: listens to events, triggers improvements.
Subscribes to event bus, monitors agent performance, triggers skill re-ranking
and prompt strategy updates, logs all optimizations.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

logger = logging.getLogger("feedback_loop")


class FeedbackLoop:
    """Closed-loop optimization: listens to events, triggers improvements."""

    def __init__(self):
        self._initialized = False
        self._recent_metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self._started = False

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
                # Separate table from migration 006's optimization_history
                # (which tracks recommendation actions with different schema)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS feedback_optimization_log (
                        id SERIAL PRIMARY KEY,
                        optimization_type VARCHAR(32) NOT NULL,
                        agent_role VARCHAR(32) NOT NULL,
                        task_type VARCHAR(64) NOT NULL,
                        before_value TEXT DEFAULT '',
                        after_value TEXT DEFAULT '',
                        reason TEXT DEFAULT '',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_fol_created ON feedback_optimization_log(created_at)")
            conn.commit()
            self._release(conn)
            self._initialized = True
        except Exception as e:
            logger.warning(f"feedback_optimization_log table init failed: {e}")

    async def start(self) -> None:
        """Subscribe to 'metrics' and 'experiments' channels on event bus."""
        if self._started:
            return
        self._ensure_table()
        try:
            from core.event_bus import get_event_bus
            bus = get_event_bus()
            bus.subscribe(
                agent_role="feedback_loop",
                channel="metrics",
                handler=self._on_metric_recorded,
            )
            bus.subscribe(
                agent_role="feedback_loop",
                channel="experiments",
                handler=self._on_experiment_concluded,
            )
            self._started = True
            logger.info("FeedbackLoop started — subscribed to metrics + experiments channels")
        except Exception as e:
            logger.warning(f"FeedbackLoop start failed: {e}")

    async def _on_metric_recorded(self, msg) -> None:
        """
        Process METRIC_RECORDED event:
        1. Track rolling window per agent+task_type
        2. If success_rate < 60% over last 20 → trigger skill re-ranking
        3. Update skill_performance records
        4. Increment Dynamic Router task counter
        5. Check dynamic thresholds for anomaly detection
        6. Feed Prometheus metrics
        """
        try:
            payload = msg.payload if hasattr(msg, "payload") else {}
            agent_role = payload.get("agent_role", "")
            task_type = payload.get("task_type", "")
            score = float(payload.get("score", 0))
            skill_ids = payload.get("skill_ids_used", [])
            latency_ms = float(payload.get("latency_ms", 0))

            if not agent_role or not task_type:
                return

            key = f"{agent_role}:{task_type}"
            self._recent_metrics[key].append(score)

            # Feed Prometheus metrics
            try:
                from tools.prometheus_metrics import metrics
                metrics.record_request(
                    agent_role, task_type,
                    latency_s=latency_ms / 1000 if latency_ms else 0,
                    status="ok" if score >= 3.0 else "degraded",
                )
            except Exception:
                pass

            # Update skill_performance
            if skill_ids:
                try:
                    from tools.optimization_engine import get_optimization_engine
                    engine = get_optimization_engine()
                    engine.update_skill_performance(skill_ids, agent_role, task_type, score)
                except Exception as e:
                    logger.debug(f"Skill performance update failed: {e}")

            # Check dynamic thresholds for anomaly detection
            if latency_ms > 0:
                try:
                    from tools.dynamic_thresholds import get_threshold_engine
                    th = get_threshold_engine().compute("latency_ms", agent_role)
                    if latency_ms > th.get("upper", 99999):
                        logger.warning(
                            f"ANOMALY: {agent_role} latency {latency_ms:.0f}ms exceeds "
                            f"dynamic threshold {th['upper']:.0f}ms (method={th['method']})"
                        )
                        self._log_optimization(
                            "anomaly_detected", agent_role, task_type,
                            f"latency={latency_ms:.0f}ms", f"threshold={th['upper']:.0f}ms",
                            f"Dynamic threshold breach (method={th['method']}, samples={th.get('samples', 0)})",
                        )
                except Exception:
                    pass

            # Check rolling window — trigger re-rank if success_rate < 60%
            window = list(self._recent_metrics[key])
            if len(window) >= 10:
                success_count = sum(1 for s in window if s >= 3.0)
                success_rate = success_count / len(window)
                if success_rate < 0.6:
                    logger.info(f"Low success rate ({success_rate:.0%}) for {key} — triggering skill re-rank")
                    try:
                        from tools.optimization_engine import get_optimization_engine
                        engine = get_optimization_engine()
                        ranked = engine.rank_skills(task_type, agent_role)
                        self._log_optimization(
                            "skill_rerank", agent_role, task_type,
                            f"success_rate={success_rate:.2f}", f"top_skills={ranked[:3]}",
                            f"Success rate below 60% over last {len(window)} tasks",
                        )
                    except Exception as e:
                        logger.debug(f"Skill re-rank failed: {e}")

            # Auto-apply safe recommendations periodically (every 50 metrics)
            try:
                total_metrics = sum(len(v) for v in self._recent_metrics.values())
                if total_metrics % 50 == 0:
                    self._auto_apply_safe_recommendations()
            except Exception as e:
                logger.debug(f"Auto-apply check failed: {e}")

        except Exception as e:
            logger.error(f"_on_metric_recorded error: {e}")

    async def _on_experiment_concluded(self, msg) -> None:
        """
        Process EXPERIMENT_CONCLUDED event:
        1. Get winning strategy details
        2. Update agent_param_overrides with winning prompt
        3. Log to feedback_optimization_log
        """
        try:
            payload = msg.payload if hasattr(msg, "payload") else {}
            experiment_id = payload.get("experiment_id", "")
            winner = payload.get("winner", "")
            p_value = payload.get("p_value", 0)

            if not experiment_id or not winner:
                return

            # Get experiment details
            from tools.ab_testing import get_ab_test_manager
            ab_mgr = get_ab_test_manager()
            exp = ab_mgr.get_experiment(experiment_id)
            if not exp:
                return

            agent_role = exp["agent_role"]
            task_type = exp["task_type"]

            # Get winning strategy
            winning_id = exp["control_strategy_id"] if winner == "control" else exp["variant_strategy_id"]
            from tools.prompt_strategies import get_prompt_strategy_manager
            ps_mgr = get_prompt_strategy_manager()
            strategy = ps_mgr.get_by_id(winning_id)

            if strategy:
                # Activate winning strategy
                try:
                    ps_mgr.activate(winning_id)
                    logger.info(f"Activated winning strategy {winning_id} for {agent_role}/{task_type}")
                except Exception as e:
                    logger.warning(f"Failed to activate winning strategy: {e}")

            self._log_optimization(
                "prompt_strategy", agent_role, task_type,
                f"experiment={experiment_id}", f"winner={winner}, strategy_id={winning_id}",
                f"A/B test concluded with p={p_value:.4f}",
            )

            # Publish OPTIMIZATION_APPLIED event
            try:
                from core.event_bus import get_event_bus
                from core.protocols import MessageType as MT, MessageEnvelope, ChannelType, DeliveryGuarantee
                bus = get_event_bus()
                opt_msg = MessageEnvelope(
                    source_agent="feedback_loop",
                    channel="optimization",
                    channel_type=ChannelType.MULTICAST,
                    message_type=MT.BROADCAST,
                    payload={
                        "event": "optimization_applied",
                        "type": "prompt_strategy",
                        "agent_role": agent_role,
                        "task_type": task_type,
                        "experiment_id": experiment_id,
                        "winner": winner,
                    },
                    delivery=DeliveryGuarantee.AT_MOST_ONCE,
                )
                await bus.publish(opt_msg)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"_on_experiment_concluded error: {e}")

    def _log_optimization(
        self, opt_type: str, agent_role: str, task_type: str,
        before: str, after: str, reason: str,
    ) -> None:
        """Insert into feedback_optimization_log table."""
        self._ensure_table()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO feedback_optimization_log
                       (optimization_type, agent_role, task_type, before_value, after_value, reason)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (opt_type, agent_role, task_type, before, after, reason),
                )
            conn.commit()
            self._release(conn)
        except Exception as e:
            logger.error(f"_log_optimization failed: {e}")

    def get_optimization_log(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get feedback optimization history."""
        self._ensure_table()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM feedback_optimization_log ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    (limit, offset),
                )
                rows = cur.fetchall()
            self._release(conn)
            result = []
            for r in rows:
                d = dict(r)
                if "created_at" in d and hasattr(d["created_at"], "isoformat"):
                    d["created_at"] = d["created_at"].isoformat()
                result.append(d)
            return result
        except Exception as e:
            logger.error(f"get_optimization_log failed: {e}")
            return []

    def _auto_apply_safe_recommendations(self) -> None:
        """Auto-apply safe (non-critical) recommendations.
        
        Called periodically by feedback loop.
        Uses auto_optimizer's auto_apply_safe_recommendations method.
        """
        try:
            from tools.auto_optimizer import get_auto_optimizer
            opt = get_auto_optimizer()
            result = opt.auto_apply_safe_recommendations(confidence_threshold=0.85)
            
            if result["applied_count"] > 0:
                logger.info(
                    "Auto-applied %d recommendations: %s",
                    result["applied_count"],
                    result["applied_ids"],
                )
                self._log_optimization(
                    "auto_apply", "system", "all",
                    f"{result['skipped_count']} skipped",
                    f"{result['applied_count']} applied",
                    f"IDs: {result['applied_ids']}",
                )
        except Exception as e:
            logger.error(f"_auto_apply_safe_recommendations failed: {e}")


# ── Singleton ────────────────────────────────────────────────────

_instance: FeedbackLoop | None = None


def get_feedback_loop() -> FeedbackLoop:
    global _instance
    if _instance is None:
        _instance = FeedbackLoop()
    return _instance
