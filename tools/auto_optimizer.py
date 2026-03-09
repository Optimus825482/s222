"""
Automatic Optimization Recommendation Engine for multi-agent system.

Analyzes agent performance metrics, error patterns, and benchmark
results to generate actionable optimization recommendations.
Recommendations are categorized by type (performance, reliability,
cost, quality) and prioritized (critical, high, medium, low).

Usage:
    from tools.auto_optimizer import get_auto_optimizer

    optimizer = get_auto_optimizer()
    recs = optimizer.analyze_and_recommend()
    pending = optimizer.get_recommendations(status="pending")
    stats = optimizer.get_optimization_stats()
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

# ── Thresholds ───────────────────────────────────────────────────

_SUCCESS_RATE_THRESHOLD = 70.0       # % — below this → reliability rec
_LATENCY_THRESHOLD_MS = 5000.0       # ms — above this → performance rec
_ERROR_FREQUENCY_THRESHOLD = 10      # count — above this → critical rec
_INACTIVE_DAYS_THRESHOLD = 7         # days — unused agents → cost rec
_BENCHMARK_BASELINE_SCORE = 3.0      # 0-5 — below this → performance rec

# ── Priority & Category Constants ────────────────────────────────

CATEGORIES = ("performance", "reliability", "cost", "quality")
PRIORITIES = ("critical", "high", "medium", "low")
STATUSES = ("pending", "applied", "dismissed")

_PRIORITY_ORDER = {p: i for i, p in enumerate(PRIORITIES)}


# ── AutoOptimizer ────────────────────────────────────────────────

class AutoOptimizer:
    """Analyzes cross-system metrics and generates optimization recommendations."""

    def __init__(self) -> None:
        self._ensure_db()

    # ── Database ─────────────────────────────────────────────────

    def _ensure_db(self) -> None:
        """No-op — tables are created by migration SQL (006)."""
        pass

    # ── Analysis & Recommendation Generation ─────────────────────

    def analyze_and_recommend(self) -> list[dict[str, Any]]:
        """Run all analysis checks and generate new recommendations.

        Checks:
          1. Low success rate agents → reliability
          2. High latency agents → performance
          3. High error count agents → quality
          4. Inactive agents (7+ days) → cost
          5. Frequent error patterns → critical
          6. Low benchmark scores → performance

        Returns list of newly created recommendation dicts.
        """
        new_recs: list[dict[str, Any]] = []

        new_recs.extend(self._check_success_rates())
        new_recs.extend(self._check_latency())
        new_recs.extend(self._check_error_counts())
        new_recs.extend(self._check_inactive_agents())
        new_recs.extend(self._check_error_patterns())
        new_recs.extend(self._check_benchmark_scores())

        logger.info("Auto-optimizer generated %d new recommendations", len(new_recs))
        return new_recs

    def _check_success_rates(self) -> list[dict[str, Any]]:
        """Check agents with success rate below threshold → reliability."""
        results: list[dict[str, Any]] = []
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT agent_role,
                           COUNT(*) AS total,
                           SUM(CASE WHEN score >= 3.5 THEN 1 ELSE 0 END) AS success
                    FROM evaluations
                    GROUP BY agent_role
                    HAVING COUNT(*) >= 5
                """)
                rows = cur.fetchall()

            for row in rows:
                rate = (row["success"] / row["total"]) * 100 if row["total"] else 100
                if rate < _SUCCESS_RATE_THRESHOLD:
                    rec = self._create_recommendation(
                        category="reliability",
                        priority="high",
                        title=f"Low success rate: {row['agent_role']} ({rate:.0f}%)",
                        description=(
                            f"Agent '{row['agent_role']}' has a success rate of {rate:.1f}% "
                            f"({row['success']}/{row['total']} tasks). "
                            f"Threshold is {_SUCCESS_RATE_THRESHOLD}%."
                        ),
                        affected_agents=[row["agent_role"]],
                        suggested_actions=[
                            "Review agent system prompt for clarity",
                            "Check if task types match agent capabilities",
                            "Consider adding retry logic or fallback agents",
                            "Analyze failed tasks for common failure patterns",
                        ],
                        estimated_impact=f"Improve success rate from {rate:.0f}% to >{_SUCCESS_RATE_THRESHOLD:.0f}%",
                    )
                    results.append(rec)
        except Exception as exc:
            logger.warning("Success rate check failed: %s", exc)
        finally:
            release_conn(conn)

        return results

    def _check_latency(self) -> list[dict[str, Any]]:
        """Check agents with average latency above threshold → performance."""
        results: list[dict[str, Any]] = []
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT agent_role,
                           ROUND(AVG(latency_ms), 0) AS avg_latency,
                           COUNT(*) AS total
                    FROM evaluations
                    WHERE latency_ms > 0
                    GROUP BY agent_role
                    HAVING COUNT(*) >= 3
                """)
                rows = cur.fetchall()

            for row in rows:
                avg_lat = float(row["avg_latency"])
                if avg_lat > _LATENCY_THRESHOLD_MS:
                    rec = self._create_recommendation(
                        category="performance",
                        priority="high" if avg_lat > _LATENCY_THRESHOLD_MS * 2 else "medium",
                        title=f"High latency: {row['agent_role']} ({avg_lat:.0f}ms avg)",
                        description=(
                            f"Agent '{row['agent_role']}' averages {avg_lat:.0f}ms response time "
                            f"across {row['total']} tasks. Threshold is {_LATENCY_THRESHOLD_MS:.0f}ms."
                        ),
                        affected_agents=[row["agent_role"]],
                        suggested_actions=[
                            "Switch to a faster model variant",
                            "Reduce prompt/context size",
                            "Enable response streaming",
                            "Add caching for repeated queries",
                            "Consider async execution for non-blocking tasks",
                        ],
                        estimated_impact=f"Reduce avg latency from {avg_lat:.0f}ms to <{_LATENCY_THRESHOLD_MS:.0f}ms",
                    )
                    results.append(rec)
        except Exception as exc:
            logger.warning("Latency check failed: %s", exc)
        finally:
            release_conn(conn)

        return results

    def _check_error_counts(self) -> list[dict[str, Any]]:
        """Check agents with high error counts → quality."""
        results: list[dict[str, Any]] = []
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT agent_role,
                           COUNT(*) AS error_count,
                           COUNT(DISTINCT error_type) AS unique_types
                    FROM error_events
                    WHERE created_at >= NOW() - INTERVAL '7 days'
                    GROUP BY agent_role
                    HAVING COUNT(*) >= 5
                    ORDER BY COUNT(*) DESC
                """)
                rows = cur.fetchall()

            for row in rows:
                count = row["error_count"]
                priority = "critical" if count >= 20 else ("high" if count >= 10 else "medium")
                rec = self._create_recommendation(
                    category="quality",
                    priority=priority,
                    title=f"High error count: {row['agent_role']} ({count} errors/7d)",
                    description=(
                        f"Agent '{row['agent_role']}' generated {count} errors "
                        f"({row['unique_types']} unique types) in the last 7 days."
                    ),
                    affected_agents=[row["agent_role"]],
                    suggested_actions=[
                        "Review error logs for root cause analysis",
                        "Add input validation and output parsing guards",
                        "Implement circuit breaker for cascading failures",
                        "Consider agent retraining or prompt refinement",
                    ],
                    estimated_impact=f"Reduce error count from {count} to <5 per week",
                )
                results.append(rec)
        except Exception as exc:
            logger.warning("Error count check failed: %s", exc)
        finally:
            release_conn(conn)

        return results

    def _check_inactive_agents(self) -> list[dict[str, Any]]:
        """Check agents not used in 7+ days → cost."""
        results: list[dict[str, Any]] = []
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT agent_role,
                           MAX(created_at) AS last_used,
                           COUNT(*) AS total_tasks
                    FROM evaluations
                    GROUP BY agent_role
                """)
                rows = cur.fetchall()

            now = datetime.now(timezone.utc)
            for row in rows:
                try:
                    last_used = row["last_used"]
                    if isinstance(last_used, str):
                        last_used = datetime.fromisoformat(last_used)
                    if last_used.tzinfo is None:
                        last_used = last_used.replace(tzinfo=timezone.utc)
                    days_inactive = (now - last_used).days
                except (ValueError, TypeError):
                    continue

                if days_inactive >= _INACTIVE_DAYS_THRESHOLD:
                    rec = self._create_recommendation(
                        category="cost",
                        priority="low" if days_inactive < 14 else "medium",
                        title=f"Inactive agent: {row['agent_role']} ({days_inactive}d idle)",
                        description=(
                            f"Agent '{row['agent_role']}' has not been used for {days_inactive} days. "
                            f"Last activity: {row['last_used']}. Total historical tasks: {row['total_tasks']}."
                        ),
                        affected_agents=[row["agent_role"]],
                        suggested_actions=[
                            "Evaluate if agent role is still needed",
                            "Consider merging capabilities into another agent",
                            "Disable agent to reduce resource overhead",
                            "Reassign agent's tasks to more active agents",
                        ],
                        estimated_impact="Reduce idle resource consumption and simplify agent pool",
                    )
                    results.append(rec)
        except Exception as exc:
            logger.warning("Inactive agent check failed: %s", exc)
        finally:
            release_conn(conn)

        return results

    def _check_error_patterns(self) -> list[dict[str, Any]]:
        """Check error patterns with high frequency → critical."""
        results: list[dict[str, Any]] = []
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, pattern_name, description, error_type,
                           agent_roles_json, frequency
                    FROM error_patterns
                    WHERE status = 'active' AND frequency >= %s
                    ORDER BY frequency DESC
                """, (_ERROR_FREQUENCY_THRESHOLD,))
                rows = cur.fetchall()

            for row in rows:
                agents = []
                try:
                    agents = json.loads(row["agent_roles_json"]) if row["agent_roles_json"] else []
                except (json.JSONDecodeError, TypeError):
                    pass

                rec = self._create_recommendation(
                    category="reliability",
                    priority="critical",
                    title=f"Recurring error pattern: {row['pattern_name']} (freq={row['frequency']})",
                    description=(
                        f"Error pattern '{row['pattern_name']}' has occurred {row['frequency']} times. "
                        f"Type: {row['error_type']}. {row['description'] or ''}"
                    ),
                    affected_agents=agents,
                    suggested_actions=[
                        "Investigate root cause of the recurring pattern",
                        "Implement targeted fix for this error type",
                        "Add monitoring alert for this pattern",
                        "Consider circuit breaker or fallback mechanism",
                        "Review and update error handling logic",
                    ],
                    estimated_impact=f"Eliminate {row['frequency']} recurring errors",
                )
                results.append(rec)
        except Exception as exc:
            logger.warning("Error pattern check failed: %s", exc)
        finally:
            release_conn(conn)

        return results

    def _check_benchmark_scores(self) -> list[dict[str, Any]]:
        """Check benchmark scores below baseline → performance."""
        results: list[dict[str, Any]] = []
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT agent_role,
                           ROUND(AVG(score)::numeric, 2) AS avg_score,
                           COUNT(*) AS total_runs,
                           ROUND(AVG(latency_ms)::numeric, 0) AS avg_latency
                    FROM benchmark_results
                    GROUP BY agent_role
                    HAVING COUNT(*) >= 3
                """)
                rows = cur.fetchall()

            for row in rows:
                avg = float(row["avg_score"])
                if avg < _BENCHMARK_BASELINE_SCORE:
                    rec = self._create_recommendation(
                        category="performance",
                        priority="high" if avg < 2.0 else "medium",
                        title=f"Below benchmark baseline: {row['agent_role']} (score={avg:.2f}/5)",
                        description=(
                            f"Agent '{row['agent_role']}' scored {avg:.2f}/5.0 across "
                            f"{row['total_runs']} benchmark runs. "
                            f"Baseline threshold is {_BENCHMARK_BASELINE_SCORE}/5.0. "
                            f"Avg latency: {row['avg_latency']}ms."
                        ),
                        affected_agents=[row["agent_role"]],
                        suggested_actions=[
                            "Review agent prompt and system instructions",
                            "Test with alternative model providers",
                            "Analyze weak benchmark categories for targeted improvement",
                            "Consider specialized agents for low-scoring task types",
                        ],
                        estimated_impact=f"Improve benchmark score from {avg:.2f} to >{_BENCHMARK_BASELINE_SCORE}",
                    )
                    results.append(rec)
        except Exception as exc:
            logger.warning("Benchmark score check failed: %s", exc)
        finally:
            release_conn(conn)

        return results

    # ── Recommendation CRUD ──────────────────────────────────────

    def _create_recommendation(
        self,
        category: str,
        priority: str,
        title: str,
        description: str,
        affected_agents: list[str],
        suggested_actions: list[str],
        estimated_impact: str,
    ) -> dict[str, Any]:
        """Insert a new recommendation and return it as a dict."""
        now = datetime.now(timezone.utc).isoformat()
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                # Dedup: skip if a pending recommendation with same title exists
                cur.execute(
                    "SELECT id FROM recommendations WHERE title = %s AND status = 'pending'",
                    (title,),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute("SELECT * FROM recommendations WHERE id = %s", (existing["id"],))
                    row = cur.fetchone()
                    return self._row_to_dict(row)

                cur.execute(
                    """INSERT INTO recommendations
                       (category, priority, title, description, affected_agents,
                        suggested_actions, estimated_impact, status, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
                       RETURNING id""",
                    (
                        category,
                        priority,
                        title,
                        description,
                        json.dumps(affected_agents, ensure_ascii=False),
                        json.dumps(suggested_actions, ensure_ascii=False),
                        estimated_impact,
                        now,
                    ),
                )
                result = cur.fetchone()
                rec_id = result["id"]
                conn.commit()
        finally:
            release_conn(conn)

        logger.info("Recommendation created: [%s/%s] %s", category, priority, title)

        return {
            "id": rec_id,
            "category": category,
            "priority": priority,
            "title": title,
            "description": description,
            "affected_agents": affected_agents,
            "suggested_actions": suggested_actions,
            "estimated_impact": estimated_impact,
            "status": "pending",
            "notes": None,
            "created_at": now,
            "updated_at": None,
        }

    def get_recommendations(
        self,
        category: str | None = None,
        priority: str | None = None,
        status: str = "pending",
    ) -> list[dict[str, Any]]:
        """Fetch recommendations with optional filters.

        Args:
            category: Filter by 'performance', 'reliability', 'cost', 'quality'.
            priority: Filter by 'critical', 'high', 'medium', 'low'.
            status: Filter by 'pending', 'applied', 'dismissed'. Default 'pending'.
        """
        conn = get_conn()
        try:
            query = "SELECT * FROM recommendations WHERE 1=1"
            params: list[Any] = []

            if status is not None:
                query += " AND status = %s"
                params.append(status)
            if category is not None:
                query += " AND category = %s"
                params.append(category)
            if priority is not None:
                query += " AND priority = %s"
                params.append(priority)

            query += " ORDER BY created_at DESC"

            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        finally:
            release_conn(conn)

        results = [self._row_to_dict(row) for row in rows]
        # Sort by priority
        results.sort(key=lambda r: _PRIORITY_ORDER.get(r.get("priority", "low"), 99))
        return results

    def get_optimization_stats(self) -> dict[str, Any]:
        """Summary statistics across all recommendations."""
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM recommendations")
                total = cur.fetchone()["cnt"]

                cur.execute(
                    "SELECT status, COUNT(*) AS cnt FROM recommendations GROUP BY status"
                )
                by_status = {row["status"]: row["cnt"] for row in cur.fetchall()}

                cur.execute(
                    "SELECT category, COUNT(*) AS cnt FROM recommendations GROUP BY category"
                )
                by_category = {row["category"]: row["cnt"] for row in cur.fetchall()}

                cur.execute(
                    "SELECT priority, COUNT(*) AS cnt FROM recommendations GROUP BY priority"
                )
                by_priority = {row["priority"]: row["cnt"] for row in cur.fetchall()}

                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM recommendations "
                    "WHERE status = 'pending' AND priority = 'critical'"
                )
                pending_critical = cur.fetchone()["cnt"]
        finally:
            release_conn(conn)

        applied_count = by_status.get("applied", 0)
        apply_rate = round((applied_count / total) * 100, 1) if total else 0.0

        return {
            "total_recommendations": total,
            "by_status": by_status,
            "by_category": by_category,
            "by_priority": by_priority,
            "pending_critical": pending_critical,
            "apply_rate_pct": apply_rate,
        }

    def apply_recommendation(self, rec_id: int, notes: str = "") -> dict[str, Any]:
        """Mark a recommendation as applied.

        Args:
            rec_id: Recommendation ID.
            notes: Optional notes about how it was applied.

        Returns the updated recommendation or error dict.
        """
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM recommendations WHERE id = %s", (rec_id,)
                )
                existing = cur.fetchone()

                if not existing:
                    return {"error": f"Recommendation {rec_id} not found"}

                if existing["status"] != "pending":
                    return {"error": f"Recommendation {rec_id} is already '{existing['status']}'"}

                now = datetime.now(timezone.utc).isoformat()
                cur.execute(
                    "UPDATE recommendations SET status = 'applied', notes = %s, updated_at = %s WHERE id = %s",
                    (notes, now, rec_id),
                )
                cur.execute(
                    "INSERT INTO optimization_history (recommendation_id, action, notes, performed_at) "
                    "VALUES (%s, %s, %s, %s)",
                    (rec_id, "applied", notes, now),
                )
                conn.commit()

                logger.info("Recommendation %d applied: %s", rec_id, notes or "(no notes)")

                cur.execute("SELECT * FROM recommendations WHERE id = %s", (rec_id,))
                updated = cur.fetchone()
        finally:
            release_conn(conn)

        return self._row_to_dict(updated)

    def dismiss_recommendation(self, rec_id: int, reason: str = "") -> dict[str, Any]:
        """Dismiss a recommendation with an optional reason.

        Args:
            rec_id: Recommendation ID.
            reason: Why it was dismissed.

        Returns the updated recommendation or error dict.
        """
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM recommendations WHERE id = %s", (rec_id,)
                )
                existing = cur.fetchone()

                if not existing:
                    return {"error": f"Recommendation {rec_id} not found"}

                if existing["status"] != "pending":
                    return {"error": f"Recommendation {rec_id} is already '{existing['status']}'"}

                now = datetime.now(timezone.utc).isoformat()
                cur.execute(
                    "UPDATE recommendations SET status = 'dismissed', notes = %s, updated_at = %s WHERE id = %s",
                    (reason, now, rec_id),
                )
                cur.execute(
                    "INSERT INTO optimization_history (recommendation_id, action, notes, performed_at) "
                    "VALUES (%s, %s, %s, %s)",
                    (rec_id, "dismissed", reason, now),
                )
                conn.commit()

                logger.info("Recommendation %d dismissed: %s", rec_id, reason or "(no reason)")

                cur.execute("SELECT * FROM recommendations WHERE id = %s", (rec_id,))
                updated = cur.fetchone()
        finally:
            release_conn(conn)

        return self._row_to_dict(updated)

    def get_agent_optimization_profile(self, agent_role: str) -> dict[str, Any]:
        """Build a per-agent optimization profile.

        Aggregates all recommendations, eval stats, error stats,
        and benchmark data for a single agent.

        Args:
            agent_role: The agent role identifier.

        Returns a comprehensive optimization profile dict.
        """
        # Recommendations for this agent
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM recommendations WHERE affected_agents LIKE %s",
                    (f'%"{agent_role}"%',),
                )
                rows = cur.fetchall()
        finally:
            release_conn(conn)

        recs = [self._row_to_dict(r) for r in rows]
        pending = [r for r in recs if r["status"] == "pending"]
        applied = [r for r in recs if r["status"] == "applied"]

        # Eval stats
        eval_stats: dict[str, Any] = {}
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) AS total,
                           ROUND(AVG(score)::numeric, 2) AS avg_score,
                           ROUND(AVG(latency_ms)::numeric, 0) AS avg_latency,
                           SUM(CASE WHEN score >= 3.5 THEN 1 ELSE 0 END) AS success_count
                    FROM evaluations WHERE agent_role = %s
                """, (agent_role,))
                row = cur.fetchone()
                if row and row["total"]:
                    eval_stats = {
                        "total_tasks": row["total"],
                        "avg_score": float(row["avg_score"] or 0),
                        "avg_latency_ms": float(row["avg_latency"] or 0),
                        "success_rate_pct": round(
                            (row["success_count"] / row["total"]) * 100, 1
                        ) if row["total"] else 0,
                    }
        except Exception:
            pass
        finally:
            release_conn(conn)

        # Error stats
        error_stats: dict[str, Any] = {}
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) AS total_errors,
                           COUNT(DISTINCT error_type) AS unique_types
                    FROM error_events
                    WHERE agent_role = %s
                    AND created_at >= NOW() - INTERVAL '7 days'
                """, (agent_role,))
                row = cur.fetchone()
                if row:
                    error_stats = {
                        "errors_last_7d": row["total_errors"],
                        "unique_error_types": row["unique_types"],
                    }
        except Exception:
            pass
        finally:
            release_conn(conn)

        # Benchmark stats
        bench_stats: dict[str, Any] = {}
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ROUND(AVG(score)::numeric, 2) AS avg_score,
                           COUNT(*) AS total_runs
                    FROM benchmark_results WHERE agent_role = %s
                """, (agent_role,))
                row = cur.fetchone()
                if row and row["total_runs"]:
                    bench_stats = {
                        "avg_benchmark_score": float(row["avg_score"] or 0),
                        "total_benchmark_runs": row["total_runs"],
                    }
        except Exception:
            pass
        finally:
            release_conn(conn)

        # Health score (0-100)
        health = 100.0
        if eval_stats.get("success_rate_pct", 100) < _SUCCESS_RATE_THRESHOLD:
            health -= 25
        if eval_stats.get("avg_latency_ms", 0) > _LATENCY_THRESHOLD_MS:
            health -= 15
        if error_stats.get("errors_last_7d", 0) > 10:
            health -= 20
        if bench_stats.get("avg_benchmark_score", 5) < _BENCHMARK_BASELINE_SCORE:
            health -= 15
        health -= len(pending) * 5
        health = max(0, min(100, health))

        return {
            "agent_role": agent_role,
            "health_score": round(health, 1),
            "eval_stats": eval_stats,
            "error_stats": error_stats,
            "benchmark_stats": bench_stats,
            "pending_recommendations": len(pending),
            "applied_recommendations": len(applied),
            "total_recommendations": len(recs),
            "recommendations": recs,
        }

    def get_optimization_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch recent optimization actions (applied/dismissed).

        Args:
            limit: Maximum number of history entries to return.

        Returns list of history entry dicts with recommendation details.
        """
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT oh.id, oh.recommendation_id, oh.action, oh.notes, oh.performed_at,
                           r.category, r.priority, r.title
                    FROM optimization_history oh
                    JOIN recommendations r ON r.id = oh.recommendation_id
                    ORDER BY oh.performed_at DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
        finally:
            release_conn(conn)

        return [dict(row) for row in rows]

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: dict) -> dict[str, Any]:
        """Convert a PG RealDictRow to a dict, parsing JSON fields."""
        d = dict(row)
        for json_field in ("affected_agents", "suggested_actions"):
            if d.get(json_field) and isinstance(d[json_field], str):
                try:
                    d[json_field] = json.loads(d[json_field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d


# ── Module-level Singleton ───────────────────────────────────────

_optimizer: AutoOptimizer | None = None


def get_auto_optimizer() -> AutoOptimizer:
    """Get the global AutoOptimizer singleton."""
    global _optimizer
    if _optimizer is None:
        _optimizer = AutoOptimizer()
    return _optimizer
