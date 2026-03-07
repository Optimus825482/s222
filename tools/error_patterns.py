"""
Error Pattern Analysis Engine for multi-agent system.

Records, classifies, and analyzes error events across agents.
Detects recurring patterns, provides aggregated stats, timeline
data, and actionable recommendations for improving reliability.

Usage:
    from tools.error_patterns import get_error_analyzer

    analyzer = get_error_analyzer()
    analyzer.record_error("researcher", "Request timed out after 30s", "research")
    patterns = analyzer.detect_patterns(window_hours=24)
    recs = analyzer.get_recommendations()
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
ERROR_DB_PATH = DATA_DIR / "error_patterns.db"

# ── Error Type Classification Rules ─────────────────────────────

_ERROR_TYPE_RULES: list[tuple[str, list[str]]] = [
    ("timeout", [
        "timeout", "timed out", "deadline exceeded", "took too long",
        "request timeout", "response timeout", "asyncio.TimeoutError",
    ]),
    ("token_limit", [
        "token limit", "context window", "max tokens", "context length",
        "too many tokens", "token_limit", "maximum context",
    ]),
    ("api_error", [
        "api error", "api_error", "status code", "http error",
        "rate limit", "429", "500", "502", "503", "504",
        "connection refused", "connection reset", "ssl error",
    ]),
    ("parsing_error", [
        "parse error", "parsing error", "json decode", "invalid json",
        "unexpected token", "syntax error", "malformed", "decode error",
    ]),
    ("tool_error", [
        "tool error", "tool_error", "tool execution", "tool failed",
        "function call", "tool call failed", "tool not found",
    ]),
    ("hallucination", [
        "hallucination", "confidence below", "low confidence",
        "fabricated", "not grounded", "unsupported claim",
    ]),
    ("cascade_failure", [
        "cascade", "multiple agents", "chain failure",
        "dependent failure", "downstream failure",
    ]),
]

# Minimum pattern threshold
_PATTERN_THRESHOLD = 3
# Similarity threshold for message clustering
_SIMILARITY_THRESHOLD = 0.6

# Severity keywords
_SEVERITY_RULES: list[tuple[str, list[str]]] = [
    ("critical", ["cascade", "multiple agents", "system", "fatal", "unrecoverable"]),
    ("high", ["timeout", "api_error", "token_limit", "repeated", "persistent"]),
    ("medium", ["parsing", "tool_error", "hallucination"]),
]


def _classify_error_type(message: str) -> str:
    """Classify an error message into a known error type."""
    msg_lower = message.lower()
    for error_type, keywords in _ERROR_TYPE_RULES:
        if any(kw in msg_lower for kw in keywords):
            return error_type
    return "unknown"


def _classify_severity(error_type: str, message: str) -> str:
    """Determine severity based on error type and message content."""
    msg_lower = message.lower()
    for severity, keywords in _SEVERITY_RULES:
        if any(kw in msg_lower for kw in keywords):
            return severity
    # Default severity by error type
    type_severity: dict[str, str] = {
        "cascade_failure": "critical",
        "timeout": "high",
        "token_limit": "high",
        "api_error": "high",
        "tool_error": "medium",
        "parsing_error": "medium",
        "hallucination": "medium",
        "unknown": "low",
    }
    return type_severity.get(error_type, "low")


# ── Recommendation Templates ─────────────────────────────────────

_RECOMMENDATION_TEMPLATES: dict[str, str] = {
    "timeout": (
        "{agent} has {count} timeout errors in {hours}h "
        "→ increase timeout, add retry with backoff, or switch to a faster model"
    ),
    "token_limit": (
        "{agent} hit token limits {count} times in {hours}h "
        "→ reduce prompt size, implement chunking, or use a model with larger context"
    ),
    "api_error": (
        "{agent} has {count} API errors in {hours}h "
        "→ check API key/quota, add retry logic, or enable fallback provider"
    ),
    "parsing_error": (
        "{agent} has {count} parsing errors in {hours}h "
        "→ tighten output format instructions, add output validation, or use structured output mode"
    ),
    "tool_error": (
        "{agent} has {count} tool errors in {hours}h "
        "→ validate tool inputs, check tool availability, or add graceful degradation"
    ),
    "hallucination": (
        "{agent} has {count} hallucination flags in {hours}h "
        "→ add fact-checking step, lower temperature, or enable RAG grounding"
    ),
    "cascade_failure": (
        "Cascade failure detected: {count} events in {hours}h "
        "→ check circuit breaker thresholds, add isolation between agents, review fallback chain"
    ),
    "unknown": (
        "{agent} has {count} unclassified errors in {hours}h "
        "→ review error logs for new failure modes and add classification rules"
    ),
}


# ── ErrorPatternAnalyzer ─────────────────────────────────────────

class ErrorPatternAnalyzer:
    """Records, classifies, and analyzes error events across agents."""

    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None
        self._ensure_db()

    # ── Database ─────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(ERROR_DB_PATH), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS error_events (
                id            TEXT PRIMARY KEY,
                agent_role    TEXT NOT NULL,
                error_type    TEXT NOT NULL,
                error_message TEXT NOT NULL,
                task_type     TEXT NOT NULL DEFAULT 'general',
                severity      TEXT NOT NULL DEFAULT 'low',
                context_json  TEXT,
                created_at    TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ee_agent
                ON error_events(agent_role);
            CREATE INDEX IF NOT EXISTS idx_ee_type
                ON error_events(error_type);
            CREATE INDEX IF NOT EXISTS idx_ee_created
                ON error_events(created_at);
            CREATE INDEX IF NOT EXISTS idx_ee_severity
                ON error_events(severity);

            CREATE TABLE IF NOT EXISTS error_patterns (
                id               TEXT PRIMARY KEY,
                pattern_name     TEXT NOT NULL,
                description      TEXT,
                error_type       TEXT NOT NULL,
                agent_roles_json TEXT NOT NULL DEFAULT '[]',
                frequency        INTEGER NOT NULL DEFAULT 0,
                first_seen       TEXT NOT NULL,
                last_seen        TEXT NOT NULL,
                status           TEXT NOT NULL DEFAULT 'active',
                resolution_json  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_ep_status
                ON error_patterns(status);
            CREATE INDEX IF NOT EXISTS idx_ep_type
                ON error_patterns(error_type);
        """)
        conn.commit()

    # ── Record ───────────────────────────────────────────────────

    def record_error(
        self,
        agent_role: str,
        error_message: str,
        task_type: str = "general",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Auto-classify and store an error event.

        Returns the created error event dict.
        """
        error_type = _classify_error_type(error_message)
        severity = _classify_severity(error_type, error_message)
        now = datetime.now(timezone.utc).isoformat()
        event_id = uuid.uuid4().hex

        conn = self._get_conn()
        conn.execute(
            """INSERT INTO error_events
               (id, agent_role, error_type, error_message, task_type,
                severity, context_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                agent_role,
                error_type,
                error_message[:2000],
                task_type,
                severity,
                json.dumps(context, ensure_ascii=False) if context else None,
                now,
            ),
        )
        conn.commit()

        logger.info(
            "Error recorded: agent=%s type=%s severity=%s",
            agent_role, error_type, severity,
        )

        return {
            "id": event_id,
            "agent_role": agent_role,
            "error_type": error_type,
            "error_message": error_message[:2000],
            "task_type": task_type,
            "severity": severity,
            "created_at": now,
        }

    # ── Pattern Detection ────────────────────────────────────────

    def detect_patterns(self, window_hours: int = 24) -> list[dict[str, Any]]:
        """Analyze recent errors, group by similarity, create/update patterns.

        Groups errors by (error_type, agent_role) within the time window.
        If the same error_type for the same agent appears >= 3 times,
        a pattern is created or updated.

        Returns list of detected/updated patterns.
        """
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, agent_role, error_type, error_message, created_at
               FROM error_events
               WHERE created_at >= datetime('now', ?)
               ORDER BY created_at ASC""",
            (f"-{window_hours} hours",),
        ).fetchall()

        if not rows:
            return []

        # Group by (error_type, agent_role)
        groups: dict[tuple[str, str], list[dict]] = {}
        for row in rows:
            key = (row["error_type"], row["agent_role"])
            groups.setdefault(key, []).append(dict(row))

        detected: list[dict[str, Any]] = []

        for (error_type, agent_role), events in groups.items():
            if len(events) < _PATTERN_THRESHOLD:
                continue

            # Cluster by message similarity
            clusters = self._cluster_messages(events)

            for cluster in clusters:
                if len(cluster) < _PATTERN_THRESHOLD:
                    continue

                pattern = self._upsert_pattern(
                    error_type=error_type,
                    agent_role=agent_role,
                    cluster=cluster,
                    window_hours=window_hours,
                )
                detected.append(pattern)

        return detected

    def _cluster_messages(
        self, events: list[dict],
    ) -> list[list[dict]]:
        """Cluster error events by message similarity using SequenceMatcher."""
        if not events:
            return []

        clusters: list[list[dict]] = []
        assigned: set[str] = set()

        for i, event in enumerate(events):
            if event["id"] in assigned:
                continue

            cluster = [event]
            assigned.add(event["id"])

            for j in range(i + 1, len(events)):
                other = events[j]
                if other["id"] in assigned:
                    continue

                similarity = SequenceMatcher(
                    None,
                    event["error_message"][:200].lower(),
                    other["error_message"][:200].lower(),
                ).ratio()

                if similarity >= _SIMILARITY_THRESHOLD:
                    cluster.append(other)
                    assigned.add(other["id"])

            clusters.append(cluster)

        return clusters

    def _upsert_pattern(
        self,
        error_type: str,
        agent_role: str,
        cluster: list[dict],
        window_hours: int,
    ) -> dict[str, Any]:
        """Create or update a pattern from a cluster of similar errors."""
        conn = self._get_conn()
        first_seen = cluster[0]["created_at"]
        last_seen = cluster[-1]["created_at"]
        frequency = len(cluster)

        # Check for existing active pattern with same type and agent
        existing = conn.execute(
            """SELECT id, agent_roles_json, frequency
               FROM error_patterns
               WHERE error_type = ? AND status = 'active'
               AND agent_roles_json LIKE ?""",
            (error_type, f'%"{agent_role}"%'),
        ).fetchone()

        if existing:
            # Update existing pattern
            new_freq = existing["frequency"] + frequency
            conn.execute(
                """UPDATE error_patterns
                   SET frequency = ?, last_seen = ?
                   WHERE id = ?""",
                (new_freq, last_seen, existing["id"]),
            )
            conn.commit()

            return {
                "id": existing["id"],
                "pattern_name": f"{error_type}:{agent_role}",
                "error_type": error_type,
                "agent_role": agent_role,
                "frequency": new_freq,
                "status": "updated",
            }

        # Create new pattern
        pattern_id = uuid.uuid4().hex
        sample_msg = cluster[0]["error_message"][:200]
        pattern_name = f"{error_type}:{agent_role}"
        description = (
            f"{agent_role} encountered {frequency} '{error_type}' errors "
            f"in {window_hours}h. Sample: {sample_msg}"
        )

        conn.execute(
            """INSERT INTO error_patterns
               (id, pattern_name, description, error_type, agent_roles_json,
                frequency, first_seen, last_seen, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
            (
                pattern_id,
                pattern_name,
                description,
                error_type,
                json.dumps([agent_role]),
                frequency,
                first_seen,
                last_seen,
            ),
        )
        conn.commit()

        logger.info(
            "New pattern detected: %s (freq=%d)", pattern_name, frequency,
        )

        return {
            "id": pattern_id,
            "pattern_name": pattern_name,
            "description": description,
            "error_type": error_type,
            "agent_role": agent_role,
            "frequency": frequency,
            "status": "new",
        }

    # ── Query: Patterns ──────────────────────────────────────────

    def get_patterns(
        self,
        status: str | None = None,
        agent_role: str | None = None,
    ) -> list[dict[str, Any]]:
        """List error patterns with optional filters.

        Args:
            status: Filter by 'active', 'resolved', or 'suppressed'.
            agent_role: Filter by agent role.
        """
        conn = self._get_conn()
        query = "SELECT * FROM error_patterns WHERE 1=1"
        params: list[Any] = []

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        if agent_role is not None:
            query += " AND agent_roles_json LIKE ?"
            params.append(f'%"{agent_role}"%')

        query += " ORDER BY last_seen DESC"
        rows = conn.execute(query, params).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            for json_field in ("agent_roles_json", "resolution_json"):
                if d.get(json_field) and isinstance(d[json_field], str):
                    try:
                        d[json_field] = json.loads(d[json_field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            results.append(d)

        return results

    # ── Query: Stats ─────────────────────────────────────────────

    def get_error_stats(
        self,
        agent_role: str | None = None,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Aggregated error statistics within a time window.

        Returns counts by error type, by agent, by severity,
        and total count.
        """
        conn = self._get_conn()
        time_filter = f"-{hours} hours"
        base_where = "WHERE created_at >= datetime('now', ?)"
        base_params: list[Any] = [time_filter]

        if agent_role:
            base_where += " AND agent_role = ?"
            base_params.append(agent_role)

        # Total count
        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM error_events {base_where}",
            base_params,
        ).fetchone()["cnt"]

        # By error type
        by_type_rows = conn.execute(
            f"""SELECT error_type, COUNT(*) as cnt
                FROM error_events {base_where}
                GROUP BY error_type ORDER BY cnt DESC""",
            base_params,
        ).fetchall()
        by_type = {row["error_type"]: row["cnt"] for row in by_type_rows}

        # By agent
        by_agent_rows = conn.execute(
            f"""SELECT agent_role, COUNT(*) as cnt
                FROM error_events {base_where}
                GROUP BY agent_role ORDER BY cnt DESC""",
            base_params,
        ).fetchall()
        by_agent = {row["agent_role"]: row["cnt"] for row in by_agent_rows}

        # By severity
        by_severity_rows = conn.execute(
            f"""SELECT severity, COUNT(*) as cnt
                FROM error_events {base_where}
                GROUP BY severity ORDER BY cnt DESC""",
            base_params,
        ).fetchall()
        by_severity = {row["severity"]: row["cnt"] for row in by_severity_rows}

        return {
            "total": total,
            "hours": hours,
            "agent_role": agent_role,
            "by_type": by_type,
            "by_agent": by_agent,
            "by_severity": by_severity,
        }

    # ── Query: Timeline ──────────────────────────────────────────

    def get_error_timeline(self, hours: int = 24) -> list[dict[str, Any]]:
        """Hourly error counts for charting.

        Returns a list of {hour, count, by_type} dicts
        for the last N hours.
        """
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT
                   strftime('%%Y-%%m-%%dT%%H:00:00', created_at) AS hour,
                   error_type,
                   COUNT(*) AS cnt
               FROM error_events
               WHERE created_at >= datetime('now', ?)
               GROUP BY hour, error_type
               ORDER BY hour ASC""",
            (f"-{hours} hours",),
        ).fetchall()

        # Aggregate into hourly buckets
        timeline: dict[str, dict[str, Any]] = {}
        for row in rows:
            h = row["hour"]
            if h not in timeline:
                timeline[h] = {"hour": h, "count": 0, "by_type": {}}
            timeline[h]["count"] += row["cnt"]
            timeline[h]["by_type"][row["error_type"]] = row["cnt"]

        return list(timeline.values())

    # ── Recommendations ──────────────────────────────────────────

    def get_recommendations(self, hours: int = 24) -> list[dict[str, Any]]:
        """Generate actionable recommendations based on active patterns.

        Analyzes recent error stats and active patterns to suggest
        concrete fixes.
        """
        recommendations: list[dict[str, Any]] = []
        stats = self.get_error_stats(hours=hours)
        active_patterns = self.get_patterns(status="active")

        # Recommendations from active patterns
        for pattern in active_patterns:
            error_type = pattern["error_type"]
            roles = pattern.get("agent_roles_json", [])
            if isinstance(roles, str):
                try:
                    roles = json.loads(roles)
                except (json.JSONDecodeError, TypeError):
                    roles = []

            agent_label = ", ".join(roles) if roles else "Unknown agent"
            template = _RECOMMENDATION_TEMPLATES.get(
                error_type,
                _RECOMMENDATION_TEMPLATES["unknown"],
            )

            recommendations.append({
                "pattern_id": pattern["id"],
                "severity": "high" if pattern["frequency"] >= 5 else "medium",
                "error_type": error_type,
                "agents": roles,
                "frequency": pattern["frequency"],
                "recommendation": template.format(
                    agent=agent_label,
                    count=pattern["frequency"],
                    hours=hours,
                ),
            })

        # Additional recommendations from stats (even without patterns)
        for error_type, count in stats.get("by_type", {}).items():
            # Only add if no pattern-based recommendation exists for this type
            already_covered = any(
                r["error_type"] == error_type for r in recommendations
            )
            if not already_covered and count >= 2:
                # Find which agents are affected
                conn = self._get_conn()
                agent_rows = conn.execute(
                    """SELECT DISTINCT agent_role FROM error_events
                       WHERE error_type = ?
                       AND created_at >= datetime('now', ?)""",
                    (error_type, f"-{hours} hours"),
                ).fetchall()
                agents = [r["agent_role"] for r in agent_rows]
                agent_label = ", ".join(agents) if agents else "Unknown agent"

                template = _RECOMMENDATION_TEMPLATES.get(
                    error_type,
                    _RECOMMENDATION_TEMPLATES["unknown"],
                )
                recommendations.append({
                    "pattern_id": None,
                    "severity": "low",
                    "error_type": error_type,
                    "agents": agents,
                    "frequency": count,
                    "recommendation": template.format(
                        agent=agent_label,
                        count=count,
                        hours=hours,
                    ),
                })

        # Sort by severity priority
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: severity_order.get(r["severity"], 99))

        return recommendations

    # ── Pattern Management ───────────────────────────────────────

    def resolve_pattern(
        self,
        pattern_id: str,
        resolution_notes: str = "",
    ) -> dict[str, Any]:
        """Mark a pattern as resolved with optional notes.

        Returns the updated pattern or error dict.
        """
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT * FROM error_patterns WHERE id = ?",
            (pattern_id,),
        ).fetchone()

        if not existing:
            return {"error": f"Pattern {pattern_id} not found"}

        resolution = {
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "notes": resolution_notes,
        }

        conn.execute(
            """UPDATE error_patterns
               SET status = 'resolved', resolution_json = ?
               WHERE id = ?""",
            (json.dumps(resolution, ensure_ascii=False), pattern_id),
        )
        conn.commit()

        logger.info("Pattern resolved: %s", pattern_id)
        return {
            "id": pattern_id,
            "status": "resolved",
            "resolution": resolution,
        }

    def suppress_pattern(self, pattern_id: str) -> dict[str, Any]:
        """Suppress a noisy pattern to hide it from recommendations.

        Returns the updated pattern or error dict.
        """
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT * FROM error_patterns WHERE id = ?",
            (pattern_id,),
        ).fetchone()

        if not existing:
            return {"error": f"Pattern {pattern_id} not found"}

        conn.execute(
            "UPDATE error_patterns SET status = 'suppressed' WHERE id = ?",
            (pattern_id,),
        )
        conn.commit()

        logger.info("Pattern suppressed: %s", pattern_id)
        return {"id": pattern_id, "status": "suppressed"}


# ── Module-level Singleton ───────────────────────────────────────

_analyzer: ErrorPatternAnalyzer | None = None


def get_error_analyzer() -> ErrorPatternAnalyzer:
    """Get the global ErrorPatternAnalyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ErrorPatternAnalyzer()
    return _analyzer
