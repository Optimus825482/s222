"""
Optimization Engine — Faz 16: Self-Improvement Loop.
Ranks skills by Skill_Score, updates skill_performance records,
and selects optimal prompt strategies based on performance data.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("optimization_engine")


class OptimizationEngine:
    """Ranks skills and selects optimal prompt strategies based on performance data."""

    def __init__(self):
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
                    CREATE TABLE IF NOT EXISTS skill_performance (
                        id SERIAL PRIMARY KEY,
                        skill_id VARCHAR(64) NOT NULL,
                        agent_role VARCHAR(32) NOT NULL,
                        task_type VARCHAR(64) NOT NULL,
                        avg_score REAL DEFAULT 0,
                        use_count INTEGER DEFAULT 0,
                        last_used_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(skill_id, agent_role, task_type)
                    )
                """)
            conn.commit()
            conn.close()
            self._initialized = True
        except Exception as e:
            logger.warning(f"skill_performance table init failed: {e}")

    def rank_skills(self, task_type: str, agent_role: str, top_n: int = 3) -> list[str]:
        """
        Rank skills by Skill_Score for given task_type + agent_role.
        Skill_Score = (0.4 × avg_rating/5.0) + (0.3 × min(use_count/100, 1.0)) + (0.3 × success_rate)
        Exploration bonus: +0.5 if use_count < 5 for this task_type.
        """
        self._ensure_table()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                # Get all active skills with their performance data
                cur.execute("""
                    SELECT s.id, s.name, s.avg_score as avg_rating, s.use_count as global_use_count,
                           sp.avg_score as perf_score, sp.use_count as task_use_count
                    FROM skills s
                    LEFT JOIN skill_performance sp
                        ON s.id = sp.skill_id AND sp.agent_role = %s AND sp.task_type = %s
                    WHERE s.active = TRUE
                """, (agent_role, task_type))
                rows = cur.fetchall()
            conn.close()

            scored: list[tuple[float, str]] = []
            for row in rows:
                avg_rating = float(row["avg_rating"] or 0) / 5.0
                task_use = int(row["task_use_count"] or 0)
                norm_use = min(task_use / 100.0, 1.0)
                perf_score = float(row["perf_score"] or 0) / 5.0  # success_rate proxy

                skill_score = (0.4 * avg_rating) + (0.3 * norm_use) + (0.3 * perf_score)

                # Exploration bonus for underused skills
                if task_use < 5:
                    skill_score += 0.5

                scored.append((skill_score, row["id"]))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [sid for _, sid in scored[:top_n]]
        except Exception as e:
            logger.error(f"rank_skills failed: {e}")
            return []

    def update_skill_performance(
        self, skill_ids: list[str], agent_role: str, task_type: str, score: float,
    ) -> None:
        """Upsert skill_performance records after task completion."""
        self._ensure_table()
        if not skill_ids:
            return
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                for skill_id in skill_ids:
                    cur.execute("""
                        INSERT INTO skill_performance (skill_id, agent_role, task_type, avg_score, use_count, last_used_at)
                        VALUES (%s, %s, %s, %s, 1, NOW())
                        ON CONFLICT (skill_id, agent_role, task_type)
                        DO UPDATE SET
                            avg_score = (skill_performance.avg_score * skill_performance.use_count + %s) / (skill_performance.use_count + 1),
                            use_count = skill_performance.use_count + 1,
                            last_used_at = NOW()
                    """, (skill_id, agent_role, task_type, score, score))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"update_skill_performance failed: {e}")

    def get_active_strategy(self, agent_role: str, task_type: str) -> dict | None:
        """Get currently active prompt strategy for role+task."""
        try:
            from tools.prompt_strategies import get_prompt_strategy_manager
            return get_prompt_strategy_manager().get_active(agent_role, task_type)
        except Exception as e:
            logger.debug(f"get_active_strategy failed: {e}")
            return None

    def get_skill_leaderboard(self, top_n: int = 20) -> list[dict]:
        """Get skills ranked by overall Skill_Score."""
        self._ensure_table()
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT s.id, s.name, s.category, s.avg_score as avg_rating,
                           s.use_count as global_use_count,
                           COALESCE(SUM(sp.use_count), 0) as total_task_uses,
                           COALESCE(AVG(sp.avg_score), 0) as avg_perf_score
                    FROM skills s
                    LEFT JOIN skill_performance sp ON s.id = sp.skill_id
                    WHERE s.active = TRUE
                    GROUP BY s.id, s.name, s.category, s.avg_score, s.use_count
                    ORDER BY s.avg_score DESC, s.use_count DESC
                    LIMIT %s
                """, (top_n,))
                rows = cur.fetchall()
            conn.close()

            result = []
            for i, row in enumerate(rows, 1):
                avg_rating = float(row["avg_rating"] or 0) / 5.0
                task_uses = int(row["total_task_uses"] or 0)
                norm_use = min(task_uses / 100.0, 1.0)
                perf_score = float(row["avg_perf_score"] or 0) / 5.0
                skill_score = (0.4 * avg_rating) + (0.3 * norm_use) + (0.3 * perf_score)

                result.append({
                    "rank": i,
                    "skill_id": row["id"],
                    "name": row["name"],
                    "category": row["category"],
                    "skill_score": round(skill_score, 3),
                    "avg_rating": round(float(row["avg_rating"] or 0), 2),
                    "total_uses": task_uses,
                    "avg_perf_score": round(float(row["avg_perf_score"] or 0), 2),
                })
            return result
        except Exception as e:
            logger.error(f"get_skill_leaderboard failed: {e}")
            return []


# ── Singleton ────────────────────────────────────────────────────

_instance: OptimizationEngine | None = None


def get_optimization_engine() -> OptimizationEngine:
    global _instance
    if _instance is None:
        _instance = OptimizationEngine()
    return _instance
