"""
Agent Evaluation — Quality scoring and benchmarking for agent outputs.
Inspired by Autogen AgentEval.

Tracks per-agent quality over time, identifies strengths/weaknesses,
and provides data for agent selection optimization.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

# Dummy object whose .exists() always returns True.
# Callers (auto_optimizer.py, adaptive_tool_selector.py) check
# EVAL_DB_PATH.exists() before querying — this keeps them happy
# without a real file on disk.
EVAL_DB_PATH = type("_", (), {"exists": staticmethod(lambda: True)})()


# ── Task Type Detection ──────────────────────────────────────────

def detect_task_type(query: str) -> str:
    """Classify task type from user query."""
    query_lower = query.lower()

    patterns = {
        "research": ["araştır", "research", "investigate", "analiz", "analyze"],
        "coding": ["kod", "code", "implement", "function", "class", "bug", "fix"],
        "math": ["hesapla", "calculate", "math", "equation", "formula"],
        "creative": ["yaz", "write", "essay", "article", "story", "blog"],
        "comparison": ["karşılaştır", "compare", "vs", "versus", "fark"],
        "planning": ["planla", "plan", "strateji", "strategy", "mimari", "architect"],
        "translation": ["çevir", "translate", "tercüme"],
        "summarization": ["özetle", "summarize", "özet", "summary"],
    }

    for task_type, keywords in patterns.items():
        if any(kw in query_lower for kw in keywords):
            return task_type

    return "general"


# ── Scoring ──────────────────────────────────────────────────────

def score_agent_output(
    agent_role: str,
    task_type: str,
    output: str,
    tokens_used: int = 0,
    latency_ms: float = 0,
    task_preview: str = "",
) -> dict[str, Any]:
    """
    Score an agent's output based on heuristic quality metrics.
    Returns score (0-5) with dimension breakdown.
    """
    dimensions = {}

    # Length quality — too short or too long is bad
    length = len(output)
    if length < 50:
        dimensions["substance"] = 1.0
    elif length < 200:
        dimensions["substance"] = 2.5
    elif length < 2000:
        dimensions["substance"] = 4.0
    elif length < 5000:
        dimensions["substance"] = 4.5
    else:
        dimensions["substance"] = 3.5  # Might be verbose

    # Structure — has formatting, sections, lists
    structure_score = 2.0
    if "\n" in output:
        structure_score += 0.5
    if any(marker in output for marker in ["- ", "* ", "1.", "•"]):
        structure_score += 0.5
    if any(marker in output for marker in ["##", "**", "###"]):
        structure_score += 0.5
    if "```" in output:
        structure_score += 0.5
    dimensions["structure"] = min(structure_score, 5.0)

    # Error indicators
    error_score = 5.0
    error_markers = ["[Error]", "[Warning]", "failed", "exception", "timeout"]
    for marker in error_markers:
        if marker.lower() in output.lower():
            error_score -= 1.0
    dimensions["reliability"] = max(error_score, 1.0)

    # Efficiency — tokens per useful content char
    if tokens_used > 0 and length > 0:
        efficiency = length / tokens_used
        if efficiency > 2.0:
            dimensions["efficiency"] = 4.5
        elif efficiency > 1.0:
            dimensions["efficiency"] = 4.0
        elif efficiency > 0.5:
            dimensions["efficiency"] = 3.0
        else:
            dimensions["efficiency"] = 2.0
    else:
        dimensions["efficiency"] = 3.0

    # Speed
    if latency_ms > 0:
        if latency_ms < 2000:
            dimensions["speed"] = 5.0
        elif latency_ms < 5000:
            dimensions["speed"] = 4.0
        elif latency_ms < 10000:
            dimensions["speed"] = 3.0
        elif latency_ms < 20000:
            dimensions["speed"] = 2.0
        else:
            dimensions["speed"] = 1.0
    else:
        dimensions["speed"] = 3.0

    # Overall score
    weights = {
        "substance": 0.3,
        "structure": 0.2,
        "reliability": 0.25,
        "efficiency": 0.1,
        "speed": 0.15,
    }
    total = sum(dimensions[k] * weights[k] for k in weights)

    # Save to DB
    _save_evaluation(agent_role, task_type, total, dimensions, tokens_used, latency_ms, task_preview)

    return {
        "agent_role": agent_role,
        "task_type": task_type,
        "score": round(total, 2),
        "dimensions": {k: round(v, 1) for k, v in dimensions.items()},
    }


# ── DB Persistence ───────────────────────────────────────────────

def _save_evaluation(
    agent_role: str,
    task_type: str,
    score: float,
    dimensions: dict,
    tokens_used: int,
    latency_ms: float,
    task_preview: str,
) -> None:
    """Persist evaluation to PostgreSQL."""
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO evaluations
               (agent_role, task_type, score, dimensions, task_preview, tokens_used, latency_ms, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                agent_role, task_type, score,
                json.dumps(dimensions), task_preview[:200],
                tokens_used, latency_ms,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to save evaluation: {e}")
    finally:
        if conn is not None:
            release_conn(conn)


def get_agent_stats(agent_role: str | None = None) -> list[dict]:
    """Get aggregated stats per agent (optionally filtered)."""
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        if agent_role:
            cur.execute("""
                SELECT agent_role, task_type,
                       COUNT(*) as total_tasks,
                       ROUND(AVG(score)::numeric, 2) as avg_score,
                       ROUND(AVG(latency_ms)::numeric, 0) as avg_latency,
                       SUM(tokens_used) as total_tokens
                FROM evaluations
                WHERE agent_role = %s
                GROUP BY agent_role, task_type
                ORDER BY avg_score DESC
            """, (agent_role,))
        else:
            cur.execute("""
                SELECT agent_role,
                       COUNT(*) as total_tasks,
                       ROUND(AVG(score)::numeric, 2) as avg_score,
                       ROUND(AVG(latency_ms)::numeric, 0) as avg_latency,
                       SUM(tokens_used) as total_tokens
                FROM evaluations
                GROUP BY agent_role
                ORDER BY avg_score DESC
            """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"Failed to get agent stats: {e}")
        return []
    finally:
        if conn is not None:
            release_conn(conn)


def get_best_agent_for_task(task_type: str) -> str | None:
    """Recommend the best agent for a given task type based on historical scores."""
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT agent_role, AVG(score) as avg_score
            FROM evaluations
            WHERE task_type = %s
            GROUP BY agent_role
            HAVING COUNT(*) >= 3
            ORDER BY avg_score DESC
            LIMIT 1
        """, (task_type,))
        row = cur.fetchone()
        return row["agent_role"] if row else None
    except Exception as e:
        logger.warning(f"Failed to get best agent for task: {e}")
        return None
    finally:
        if conn is not None:
            release_conn(conn)

def get_performance_baseline(agent_role: str | None = None) -> dict[str, Any]:
    """Return aggregated performance baseline for an agent (or all agents).

    Returns dict with keys: agent_role, total_tasks, success_count,
    task_success_rate_pct, avg_score, avg_latency.
    """
    empty: dict[str, Any] = {
        "agent_role": agent_role,
        "total_tasks": 0,
        "success_count": 0,
        "task_success_rate_pct": 0.0,
        "avg_score": 0.0,
        "avg_latency": 0.0,
    }
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        if agent_role:
            cur.execute("""
                SELECT
                    COUNT(*)                              AS total_tasks,
                    COUNT(*) FILTER (WHERE score >= 3.0)  AS success_count,
                    ROUND(AVG(score)::numeric, 2)         AS avg_score,
                    ROUND(AVG(latency_ms)::numeric, 0)    AS avg_latency
                FROM evaluations
                WHERE agent_role = %s
            """, (agent_role,))
        else:
            cur.execute("""
                SELECT
                    COUNT(*)                              AS total_tasks,
                    COUNT(*) FILTER (WHERE score >= 3.0)  AS success_count,
                    ROUND(AVG(score)::numeric, 2)         AS avg_score,
                    ROUND(AVG(latency_ms)::numeric, 0)    AS avg_latency
                FROM evaluations
            """)
        row = cur.fetchone()
        if not row or not row["total_tasks"]:
            return empty
        total = int(row["total_tasks"])
        success = int(row["success_count"])
        return {
            "agent_role": agent_role,
            "total_tasks": total,
            "success_count": success,
            "task_success_rate_pct": round(success / total * 100, 1) if total else 0.0,
            "avg_score": float(row["avg_score"] or 0),
            "avg_latency": float(row["avg_latency"] or 0),
        }
    except Exception as e:
        logger.warning(f"Failed to get performance baseline: {e}")
        return empty
    finally:
        if conn is not None:
            release_conn(conn)


