"""
Agent Evaluation — Quality scoring and benchmarking for agent outputs.
Inspired by Autogen AgentEval.

Tracks per-agent quality over time, identifies strengths/weaknesses,
and provides data for agent selection optimization.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
EVAL_DB_PATH = DATA_DIR / "evaluations.db"

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(EVAL_DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _init_schema(_conn)
    return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_role   TEXT NOT NULL,
            task_type    TEXT NOT NULL DEFAULT 'general',
            score        REAL NOT NULL,
            dimensions   TEXT,
            task_preview TEXT,
            tokens_used  INTEGER DEFAULT 0,
            latency_ms   REAL DEFAULT 0,
            created_at   TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_eval_agent ON evaluations(agent_role);
        CREATE INDEX IF NOT EXISTS idx_eval_type ON evaluations(task_type);
    """)


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


def _save_evaluation(
    agent_role: str,
    task_type: str,
    score: float,
    dimensions: dict,
    tokens_used: int,
    latency_ms: float,
    task_preview: str,
) -> None:
    """Persist evaluation to SQLite."""
    try:
        conn = _get_conn()
        conn.execute(
            """INSERT INTO evaluations
               (agent_role, task_type, score, dimensions, task_preview, tokens_used, latency_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
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


def get_agent_stats(agent_role: str | None = None) -> list[dict]:
    """Get aggregated stats per agent (optionally filtered)."""
    conn = _get_conn()
    if agent_role:
        rows = conn.execute("""
            SELECT agent_role, task_type,
                   COUNT(*) as total_tasks,
                   ROUND(AVG(score), 2) as avg_score,
                   ROUND(AVG(latency_ms), 0) as avg_latency,
                   SUM(tokens_used) as total_tokens
            FROM evaluations
            WHERE agent_role = ?
            GROUP BY agent_role, task_type
            ORDER BY avg_score DESC
        """, (agent_role,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT agent_role,
                   COUNT(*) as total_tasks,
                   ROUND(AVG(score), 2) as avg_score,
                   ROUND(AVG(latency_ms), 0) as avg_latency,
                   SUM(tokens_used) as total_tokens
            FROM evaluations
            GROUP BY agent_role
            ORDER BY avg_score DESC
        """).fetchall()

    return [dict(r) for r in rows]


def get_performance_baseline(agent_role: str | None = None) -> dict[str, Any]:
    """
    Build a Performance Baseline report (agent-orchestration-improve-agent skill).
    Aggregates eval data into: task_success_rate, avg_corrections, tool_efficiency,
    user_satisfaction_score, avg_latency_ms, token_efficiency_ratio.
    """
    conn = _get_conn()
    # Success = score >= 3.5
    if agent_role:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN score >= 3.5 THEN 1 ELSE 0 END) as success_count,
                ROUND(AVG(score), 2) as avg_score,
                ROUND(AVG(latency_ms), 0) as avg_latency,
                COALESCE(SUM(tokens_used), 0) as total_tokens
            FROM evaluations
            WHERE agent_role = ?
        """, (agent_role,)).fetchone()
    else:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN score >= 3.5 THEN 1 ELSE 0 END) as success_count,
                ROUND(AVG(score), 2) as avg_score,
                ROUND(AVG(latency_ms), 0) as avg_latency,
                COALESCE(SUM(tokens_used), 0) as total_tokens
            FROM evaluations
        """).fetchone()

    total = row["total_tasks"] or 0
    success = row["success_count"] or 0
    avg_score = float(row["avg_score"] or 0)
    avg_latency = float(row["avg_latency"] or 0)
    total_tokens = int(row["total_tokens"] or 0)

    task_success_rate = (success / total * 100) if total else 0
    # Map avg_score 1-5 to satisfaction 1-10
    user_satisfaction = round((avg_score / 5.0) * 10, 1) if avg_score else 0
    token_per_task = (total_tokens / total) if total else 0

    return {
        "task_success_rate_pct": round(task_success_rate, 1),
        "total_tasks": total,
        "success_count": success,
        "avg_score": avg_score,
        "user_satisfaction_score": min(10, max(1, user_satisfaction)),
        "avg_latency_ms": round(avg_latency, 0),
        "total_tokens": total_tokens,
        "token_efficiency_ratio": f"{total_tokens}:{total}" if total else "0:0",
        "agent_role": agent_role,
    }


def get_best_agent_for_task(task_type: str) -> str | None:
    """Recommend the best agent for a given task type based on historical scores."""
    conn = _get_conn()
    row = conn.execute("""
        SELECT agent_role, AVG(score) as avg_score
        FROM evaluations
        WHERE task_type = ?
        GROUP BY agent_role
        HAVING COUNT(*) >= 3
        ORDER BY avg_score DESC
        LIMIT 1
    """, (task_type,)).fetchone()

    return row["agent_role"] if row else None
