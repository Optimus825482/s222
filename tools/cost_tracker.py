"""
Token Usage & Cost Tracking Engine for multi-agent system.

Records per-agent, per-model, per-task token usage events,
calculates costs based on configurable pricing, provides
summaries, timelines, budget management, and cost forecasting.

Usage:
    from tools.cost_tracker import get_cost_tracker

    tracker = get_cost_tracker()
    tracker.record_usage("researcher", "gpt-4o", 1500, 800, "research")
    summary = tracker.get_cost_summary(hours=24)
    forecast = tracker.get_cost_forecast(days=7)
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "cost_tracker.db"

# ── Default Pricing (per 1K tokens) ─────────────────────────────

DEFAULT_PRICING: dict[str, float] = {
    "input": 0.003,
    "output": 0.015,
}


# ── CostTracker ──────────────────────────────────────────────────

class CostTracker:
    """Tracks token usage and costs across agents, models, and task types."""

    def __init__(
        self,
        pricing: dict[str, float] | None = None,
    ) -> None:
        self._conn: sqlite3.Connection | None = None
        self._pricing = pricing or DEFAULT_PRICING.copy()
        self._ensure_db()

    # ── Database ─────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Return a reusable SQLite connection (WAL mode, Row factory)."""
        if self._conn is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_db(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id              TEXT PRIMARY KEY,
                agent_role      TEXT NOT NULL,
                model           TEXT NOT NULL,
                input_tokens    INTEGER NOT NULL,
                output_tokens   INTEGER NOT NULL,
                total_tokens    INTEGER NOT NULL,
                input_cost      REAL NOT NULL,
                output_cost     REAL NOT NULL,
                total_cost      REAL NOT NULL,
                task_type       TEXT NOT NULL DEFAULT 'general',
                metadata        TEXT,
                created_at      TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_usage_created
                ON usage_events(created_at);
            CREATE INDEX IF NOT EXISTS idx_usage_agent
                ON usage_events(agent_role);
            CREATE INDEX IF NOT EXISTS idx_usage_model
                ON usage_events(model);
            CREATE INDEX IF NOT EXISTS idx_usage_task
                ON usage_events(task_type);

            CREATE TABLE IF NOT EXISTS daily_summaries (
                id              TEXT PRIMARY KEY,
                date            TEXT NOT NULL,
                agent_role      TEXT NOT NULL,
                model           TEXT NOT NULL,
                task_type       TEXT NOT NULL,
                total_input     INTEGER NOT NULL DEFAULT 0,
                total_output    INTEGER NOT NULL DEFAULT 0,
                total_cost      REAL NOT NULL DEFAULT 0.0,
                event_count     INTEGER NOT NULL DEFAULT 0,
                updated_at      TEXT NOT NULL,
                UNIQUE(date, agent_role, model, task_type)
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id              TEXT PRIMARY KEY,
                agent_role      TEXT,
                daily_limit     REAL NOT NULL,
                alert_threshold REAL NOT NULL DEFAULT 0.8,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                UNIQUE(agent_role)
            );
        """)
        conn.commit()

    # ── Helpers ───────────────────────────────────────────────────

    def _now_iso(self) -> str:
        """Return current UTC time as ISO-8601 string."""
        return datetime.now(timezone.utc).isoformat()

    def _cutoff_iso(self, hours: int) -> str:
        """Return ISO-8601 string for *hours* ago."""
        dt = datetime.now(timezone.utc) - timedelta(hours=hours)
        return dt.isoformat()

    def _calc_cost(self, input_tokens: int, output_tokens: int) -> tuple[float, float]:
        """Calculate input and output costs from token counts."""
        input_cost = (input_tokens / 1000.0) * self._pricing["input"]
        output_cost = (output_tokens / 1000.0) * self._pricing["output"]
        return round(input_cost, 6), round(output_cost, 6)

    # ── Record Usage ─────────────────────────────────────────────

    def record_usage(
        self,
        agent_role: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        task_type: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a single token-usage event and update daily summary.

        Returns the created event as a dict.
        """
        conn = self._get_conn()
        now = self._now_iso()
        event_id = str(uuid.uuid4())
        total_tokens = input_tokens + output_tokens
        input_cost, output_cost = self._calc_cost(input_tokens, output_tokens)
        total_cost = round(input_cost + output_cost, 6)

        conn.execute(
            """
            INSERT INTO usage_events
                (id, agent_role, model, input_tokens, output_tokens,
                 total_tokens, input_cost, output_cost, total_cost,
                 task_type, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id, agent_role, model, input_tokens, output_tokens,
                total_tokens, input_cost, output_cost, total_cost,
                task_type, json.dumps(metadata) if metadata else None, now,
            ),
        )

        # Upsert daily summary
        today = now[:10]  # YYYY-MM-DD
        summary_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO daily_summaries
                (id, date, agent_role, model, task_type,
                 total_input, total_output, total_cost, event_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(date, agent_role, model, task_type) DO UPDATE SET
                total_input  = total_input  + excluded.total_input,
                total_output = total_output + excluded.total_output,
                total_cost   = total_cost   + excluded.total_cost,
                event_count  = event_count  + 1,
                updated_at   = excluded.updated_at
            """,
            (
                summary_id, today, agent_role, model, task_type,
                input_tokens, output_tokens, total_cost, now,
            ),
        )
        conn.commit()

        return {
            "id": event_id,
            "agent_role": agent_role,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "task_type": task_type,
            "created_at": now,
        }

    # ── Cost Summary ─────────────────────────────────────────────

    def get_cost_summary(self, hours: int = 24) -> dict[str, Any]:
        """Aggregate cost summary for the given time window.

        Returns totals, breakdowns by agent, model, and task type.
        """
        conn = self._get_conn()
        cutoff = self._cutoff_iso(hours)

        # Totals
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(input_tokens), 0)  AS total_input,
                COALESCE(SUM(output_tokens), 0) AS total_output,
                COALESCE(SUM(total_tokens), 0)  AS total_tokens,
                COALESCE(SUM(input_cost), 0)    AS total_input_cost,
                COALESCE(SUM(output_cost), 0)   AS total_output_cost,
                COALESCE(SUM(total_cost), 0)    AS total_cost,
                COUNT(*)                        AS event_count
            FROM usage_events
            WHERE created_at >= ?
            """,
            (cutoff,),
        ).fetchone()

        totals = dict(row)

        # By agent
        by_agent = [
            dict(r) for r in conn.execute(
                """
                SELECT agent_role,
                       SUM(input_tokens)  AS input_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(total_cost)    AS total_cost,
                       COUNT(*)           AS event_count
                FROM usage_events
                WHERE created_at >= ?
                GROUP BY agent_role
                ORDER BY total_cost DESC
                """,
                (cutoff,),
            ).fetchall()
        ]

        # By model
        by_model = [
            dict(r) for r in conn.execute(
                """
                SELECT model,
                       SUM(input_tokens)  AS input_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(total_cost)    AS total_cost,
                       COUNT(*)           AS event_count
                FROM usage_events
                WHERE created_at >= ?
                GROUP BY model
                ORDER BY total_cost DESC
                """,
                (cutoff,),
            ).fetchall()
        ]

        # By task type
        by_task = [
            dict(r) for r in conn.execute(
                """
                SELECT task_type,
                       SUM(input_tokens)  AS input_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(total_cost)    AS total_cost,
                       COUNT(*)           AS event_count
                FROM usage_events
                WHERE created_at >= ?
                GROUP BY task_type
                ORDER BY total_cost DESC
                """,
                (cutoff,),
            ).fetchall()
        ]

        return {
            "hours": hours,
            "totals": totals,
            "by_agent": by_agent,
            "by_model": by_model,
            "by_task_type": by_task,
        }

    # ── Cost Timeline ────────────────────────────────────────────

    def get_cost_timeline(
        self,
        hours: int = 24,
        granularity: str = "hour",
    ) -> list[dict[str, Any]]:
        """Return cost data bucketed by hour or day.

        Args:
            hours: Look-back window.
            granularity: ``"hour"`` or ``"day"``.

        Returns a list of dicts with period, tokens, cost, and event count.
        """
        conn = self._get_conn()
        cutoff = self._cutoff_iso(hours)

        if granularity == "day":
            period_expr = "SUBSTR(created_at, 1, 10)"  # YYYY-MM-DD
        else:
            period_expr = "SUBSTR(created_at, 1, 13)"  # YYYY-MM-DDTHH

        rows = conn.execute(
            f"""
            SELECT
                {period_expr}                   AS period,
                SUM(input_tokens)               AS input_tokens,
                SUM(output_tokens)              AS output_tokens,
                SUM(total_cost)                 AS total_cost,
                COUNT(*)                        AS event_count
            FROM usage_events
            WHERE created_at >= ?
            GROUP BY period
            ORDER BY period
            """,
            (cutoff,),
        ).fetchall()

        return [dict(r) for r in rows]

    # ── Agent Costs ──────────────────────────────────────────────

    def get_agent_costs(
        self,
        agent_role: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Detailed cost breakdown for a single agent.

        Includes totals, per-model split, per-task split, and recent events.
        """
        conn = self._get_conn()
        cutoff = self._cutoff_iso(hours)

        # Totals for agent
        totals_row = conn.execute(
            """
            SELECT
                COALESCE(SUM(input_tokens), 0)  AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                COALESCE(SUM(total_cost), 0)    AS total_cost,
                COUNT(*)                        AS event_count
            FROM usage_events
            WHERE agent_role = ? AND created_at >= ?
            """,
            (agent_role, cutoff),
        ).fetchone()

        # By model
        by_model = [
            dict(r) for r in conn.execute(
                """
                SELECT model,
                       SUM(input_tokens)  AS input_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(total_cost)    AS total_cost,
                       COUNT(*)           AS event_count
                FROM usage_events
                WHERE agent_role = ? AND created_at >= ?
                GROUP BY model
                ORDER BY total_cost DESC
                """,
                (agent_role, cutoff),
            ).fetchall()
        ]

        # By task type
        by_task = [
            dict(r) for r in conn.execute(
                """
                SELECT task_type,
                       SUM(input_tokens)  AS input_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(total_cost)    AS total_cost,
                       COUNT(*)           AS event_count
                FROM usage_events
                WHERE agent_role = ? AND created_at >= ?
                GROUP BY task_type
                ORDER BY total_cost DESC
                """,
                (agent_role, cutoff),
            ).fetchall()
        ]

        # Recent events (last 20)
        recent = [
            dict(r) for r in conn.execute(
                """
                SELECT id, model, input_tokens, output_tokens,
                       total_cost, task_type, created_at
                FROM usage_events
                WHERE agent_role = ? AND created_at >= ?
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (agent_role, cutoff),
            ).fetchall()
        ]

        return {
            "agent_role": agent_role,
            "hours": hours,
            "totals": dict(totals_row),
            "by_model": by_model,
            "by_task_type": by_task,
            "recent_events": recent,
        }

    # ── Top Consumers ────────────────────────────────────────────

    def get_top_consumers(
        self,
        hours: int = 24,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return agents ranked by total cost (descending)."""
        conn = self._get_conn()
        cutoff = self._cutoff_iso(hours)

        rows = conn.execute(
            """
            SELECT agent_role,
                   SUM(input_tokens)  AS input_tokens,
                   SUM(output_tokens) AS output_tokens,
                   SUM(total_tokens)  AS total_tokens,
                   SUM(total_cost)    AS total_cost,
                   COUNT(*)           AS event_count
            FROM usage_events
            WHERE created_at >= ?
            GROUP BY agent_role
            ORDER BY total_cost DESC
            LIMIT ?
            """,
            (cutoff, limit),
        ).fetchall()

        return [dict(r) for r in rows]

    # ── Budget Management ────────────────────────────────────────

    def set_budget(
        self,
        agent_role: str | None,
        daily_limit: float,
        alert_threshold: float = 0.8,
    ) -> dict[str, Any]:
        """Set or update a daily budget for an agent (or global if None).

        Args:
            agent_role: Agent name, or ``None`` for a global budget.
            daily_limit: Maximum daily spend in dollars.
            alert_threshold: Fraction (0-1) at which to trigger an alert.

        Returns the budget record.
        """
        conn = self._get_conn()
        now = self._now_iso()
        budget_id = str(uuid.uuid4())

        conn.execute(
            """
            INSERT INTO budgets
                (id, agent_role, daily_limit, alert_threshold, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_role) DO UPDATE SET
                daily_limit     = excluded.daily_limit,
                alert_threshold = excluded.alert_threshold,
                updated_at      = excluded.updated_at
            """,
            (budget_id, agent_role, daily_limit, alert_threshold, now, now),
        )
        conn.commit()

        return {
            "agent_role": agent_role,
            "daily_limit": daily_limit,
            "alert_threshold": alert_threshold,
            "updated_at": now,
        }

    def check_budget(
        self,
        agent_role: str | None = None,
    ) -> dict[str, Any]:
        """Check budget status for an agent or globally.

        Returns current spend, limit, utilisation percentage,
        and whether alert/exceeded thresholds are hit.
        """
        conn = self._get_conn()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_start = f"{today}T00:00:00+00:00"

        # Fetch budget
        budget_row = conn.execute(
            "SELECT * FROM budgets WHERE agent_role IS ?"
            if agent_role is None else
            "SELECT * FROM budgets WHERE agent_role = ?",
            (agent_role,),
        ).fetchone()

        if budget_row is None:
            return {
                "agent_role": agent_role,
                "has_budget": False,
                "message": "No budget configured",
            }

        budget = dict(budget_row)

        # Today's spend
        if agent_role is None:
            spend_row = conn.execute(
                """
                SELECT COALESCE(SUM(total_cost), 0) AS today_cost
                FROM usage_events
                WHERE created_at >= ?
                """,
                (today_start,),
            ).fetchone()
        else:
            spend_row = conn.execute(
                """
                SELECT COALESCE(SUM(total_cost), 0) AS today_cost
                FROM usage_events
                WHERE agent_role = ? AND created_at >= ?
                """,
                (agent_role, today_start),
            ).fetchone()

        today_cost = spend_row["today_cost"]
        daily_limit = budget["daily_limit"]
        alert_threshold = budget["alert_threshold"]
        utilisation = today_cost / daily_limit if daily_limit > 0 else 0.0

        return {
            "agent_role": agent_role,
            "has_budget": True,
            "daily_limit": daily_limit,
            "today_cost": round(today_cost, 6),
            "remaining": round(max(daily_limit - today_cost, 0), 6),
            "utilisation": round(utilisation, 4),
            "alert_triggered": utilisation >= alert_threshold,
            "budget_exceeded": today_cost >= daily_limit,
            "alert_threshold": alert_threshold,
        }

    # ── Cost Forecast ────────────────────────────────────────────

    def get_cost_forecast(self, days: int = 7) -> dict[str, Any]:
        """Predict future costs based on recent daily trends.

        Uses the last 7 days of actual data to compute a daily average
        and projects forward for *days* days.
        """
        conn = self._get_conn()
        cutoff = self._cutoff_iso(hours=7 * 24)

        rows = conn.execute(
            """
            SELECT
                SUBSTR(created_at, 1, 10) AS day,
                SUM(total_cost)           AS daily_cost,
                SUM(input_tokens)         AS daily_input,
                SUM(output_tokens)        AS daily_output,
                COUNT(*)                  AS event_count
            FROM usage_events
            WHERE created_at >= ?
            GROUP BY day
            ORDER BY day
            """,
            (cutoff,),
        ).fetchall()

        history = [dict(r) for r in rows]

        if not history:
            return {
                "forecast_days": days,
                "history_days": 0,
                "avg_daily_cost": 0.0,
                "projected_total": 0.0,
                "daily_forecast": [],
                "confidence": "none",
            }

        costs = [h["daily_cost"] for h in history]
        avg_daily = sum(costs) / len(costs)

        # Simple trend: linear slope over available days
        n = len(costs)
        if n >= 2:
            x_mean = (n - 1) / 2.0
            y_mean = avg_daily
            numerator = sum((i - x_mean) * (c - y_mean) for i, c in enumerate(costs))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            slope = numerator / denominator if denominator != 0 else 0.0
        else:
            slope = 0.0

        # Project forward
        daily_forecast: list[dict[str, Any]] = []
        base_date = datetime.now(timezone.utc)
        projected_total = 0.0

        for d in range(1, days + 1):
            forecast_date = (base_date + timedelta(days=d)).strftime("%Y-%m-%d")
            projected_cost = max(avg_daily + slope * (n + d - 1), 0.0)
            projected_total += projected_cost
            daily_forecast.append({
                "date": forecast_date,
                "projected_cost": round(projected_cost, 6),
            })

        # Confidence based on data availability
        if n >= 7:
            confidence = "high"
        elif n >= 3:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "forecast_days": days,
            "history_days": n,
            "avg_daily_cost": round(avg_daily, 6),
            "trend_slope": round(slope, 6),
            "projected_total": round(projected_total, 6),
            "daily_forecast": daily_forecast,
            "confidence": confidence,
        }

    # ── Usage Stats ──────────────────────────────────────────────

    def get_usage_stats(self) -> dict[str, Any]:
        """Return overall usage statistics across all time.

        Includes total events, unique agents/models, lifetime cost,
        average tokens per event, and first/last event timestamps.
        """
        conn = self._get_conn()

        totals = conn.execute(
            """
            SELECT
                COUNT(*)                        AS total_events,
                COALESCE(SUM(input_tokens), 0)  AS total_input_tokens,
                COALESCE(SUM(output_tokens), 0) AS total_output_tokens,
                COALESCE(SUM(total_tokens), 0)  AS total_tokens,
                COALESCE(SUM(total_cost), 0)    AS total_cost,
                MIN(created_at)                 AS first_event,
                MAX(created_at)                 AS last_event
            FROM usage_events
            """
        ).fetchone()

        stats = dict(totals)

        event_count = stats["total_events"]
        if event_count > 0:
            stats["avg_input_tokens"] = round(stats["total_input_tokens"] / event_count, 1)
            stats["avg_output_tokens"] = round(stats["total_output_tokens"] / event_count, 1)
            stats["avg_cost_per_event"] = round(stats["total_cost"] / event_count, 6)
        else:
            stats["avg_input_tokens"] = 0.0
            stats["avg_output_tokens"] = 0.0
            stats["avg_cost_per_event"] = 0.0

        # Unique counts
        agents = conn.execute(
            "SELECT COUNT(DISTINCT agent_role) AS n FROM usage_events"
        ).fetchone()
        models = conn.execute(
            "SELECT COUNT(DISTINCT model) AS n FROM usage_events"
        ).fetchone()
        tasks = conn.execute(
            "SELECT COUNT(DISTINCT task_type) AS n FROM usage_events"
        ).fetchone()

        stats["unique_agents"] = agents["n"]
        stats["unique_models"] = models["n"]
        stats["unique_task_types"] = tasks["n"]

        return stats


# ── Singleton ────────────────────────────────────────────────────

_tracker_instance: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    """Return a module-level singleton CostTracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = CostTracker()
    return _tracker_instance
