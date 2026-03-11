"""
User Feedback System for RLHF (Reinforcement Learning from Human Feedback).
Collects user ratings and uses them to improve agent responses.

Features:
- 👍👎 rating buttons for each response
- Detailed feedback collection
- RLHF data aggregation
- Agent performance scoring based on feedback
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)


def _as_row(row: object) -> Mapping[str, Any] | None:
    if isinstance(row, Mapping):
        return row
    return None


@dataclass
class FeedbackEntry:
    """A single feedback entry from a user."""
    id: Optional[int] = None
    thread_id: str = ""
    message_id: str = ""
    user_id: str = ""
    agent_role: str = ""
    rating: str = ""  # "positive", "negative", "neutral"
    feedback_text: Optional[str] = None
    task_input: str = ""
    task_output: str = ""
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "agent_role": self.agent_role,
            "rating": self.rating,
            "feedback_text": self.feedback_text,
            "task_input": self.task_input[:500],
            "task_output": self.task_output[:1000],
            "created_at": self.created_at,
        }


@dataclass
class AgentFeedbackStats:
    """Aggregated feedback statistics for an agent."""
    agent_role: str
    total_ratings: int = 0
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    satisfaction_rate: float = 0.0
    avg_response_quality: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "agent_role": self.agent_role,
            "total_ratings": self.total_ratings,
            "positive": self.positive,
            "negative": self.negative,
            "neutral": self.neutral,
            "satisfaction_rate": round(self.satisfaction_rate, 2),
            "avg_response_quality": round(self.avg_response_quality, 2),
        }


def _ensure_tables() -> None:
    """Create feedback tables if they don't exist."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Main feedback table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    message_id TEXT,
                    user_id TEXT,
                    agent_role TEXT NOT NULL,
                    rating TEXT NOT NULL CHECK (rating IN ('positive', 'negative', 'neutral')),
                    feedback_text TEXT,
                    task_input TEXT,
                    task_output TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_feedback_thread ON user_feedback(thread_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_agent ON user_feedback(agent_role);
                CREATE INDEX IF NOT EXISTS idx_feedback_rating ON user_feedback(rating);
                CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedback(created_at DESC);
            """)
            
            # Aggregated stats table (for fast queries)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_feedback_stats (
                    agent_role TEXT PRIMARY KEY,
                    total_ratings INT NOT NULL DEFAULT 0,
                    positive INT NOT NULL DEFAULT 0,
                    negative INT NOT NULL DEFAULT 0,
                    neutral INT NOT NULL DEFAULT 0,
                    satisfaction_rate FLOAT NOT NULL DEFAULT 0.0,
                    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to create feedback tables: {e}")
        conn.rollback()
    finally:
        release_conn(conn)


# Run on import
_ensure_tables()


def submit_feedback(
    thread_id: str,
    agent_role: str,
    rating: str,
    message_id: Optional[str] = None,
    user_id: Optional[str] = None,
    feedback_text: Optional[str] = None,
    task_input: Optional[str] = None,
    task_output: Optional[str] = None,
) -> dict:
    """
    Submit user feedback for a response.
    
    Args:
        thread_id: Thread ID
        agent_role: Agent that generated the response
        rating: "positive", "negative", or "neutral"
        message_id: Optional message ID
        user_id: Optional user ID
        feedback_text: Optional detailed feedback
        task_input: The original user input
        task_output: The agent's response
    
    Returns:
        Dict with success status and feedback ID
    """
    if rating not in ("positive", "negative", "neutral"):
        return {"success": False, "error": "Invalid rating. Must be positive, negative, or neutral."}
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Insert feedback
            cur.execute("""
                INSERT INTO user_feedback 
                (thread_id, message_id, user_id, agent_role, rating, feedback_text, task_input, task_output)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                thread_id,
                message_id,
                user_id,
                agent_role,
                rating,
                feedback_text,
                task_input[:500] if task_input else None,
                task_output[:2000] if task_output else None,
            ))

            inserted = _as_row(cur.fetchone())
            if inserted is None:
                raise ValueError("Feedback insert did not return id")
            feedback_id = inserted["id"]
            
            # Update aggregated stats
            _update_agent_stats(cur, agent_role, rating)
            
        conn.commit()
        
        logger.info(f"Feedback submitted: {rating} for {agent_role} in thread {thread_id}")
        
        return {
            "success": True,
            "feedback_id": feedback_id,
            "message": f"Feedback recorded: {rating}",
        }
        
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        release_conn(conn)


def _update_agent_stats(cur, agent_role: str, rating: str) -> None:
    """Update aggregated stats for an agent."""
    # Upsert agent stats
    cur.execute("""
        INSERT INTO agent_feedback_stats (agent_role, total_ratings, positive, negative, neutral)
        VALUES (%s, 1, %s, %s, %s)
        ON CONFLICT (agent_role) DO UPDATE SET
            total_ratings = agent_feedback_stats.total_ratings + 1,
            positive = agent_feedback_stats.positive + CASE WHEN %s = 'positive' THEN 1 ELSE 0 END,
            negative = agent_feedback_stats.negative + CASE WHEN %s = 'negative' THEN 1 ELSE 0 END,
            neutral = agent_feedback_stats.neutral + CASE WHEN %s = 'neutral' THEN 1 ELSE 0 END,
            satisfaction_rate = 
                (agent_feedback_stats.positive + CASE WHEN %s = 'positive' THEN 1 ELSE 0 END)::FLOAT 
                / NULLIF(agent_feedback_stats.total_ratings + 1, 0) * 100,
            last_updated = NOW()
    """, (
        agent_role,
        1 if rating == "positive" else 0,
        1 if rating == "negative" else 0,
        1 if rating == "neutral" else 0,
        rating, rating, rating, rating,
    ))


def get_feedback_for_thread(thread_id: str) -> list[dict]:
    """Get all feedback for a thread."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM user_feedback 
                WHERE thread_id = %s 
                ORDER BY created_at DESC
            """, (thread_id,))
            rows = cur.fetchall()
            return [dict(r) for fetched in rows if (r := _as_row(fetched)) is not None]
    finally:
        release_conn(conn)


def get_agent_feedback_stats(agent_role: Optional[str] = None) -> list[dict]:
    """Get aggregated feedback stats for agents."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if agent_role:
                cur.execute("""
                    SELECT * FROM agent_feedback_stats WHERE agent_role = %s
                """, (agent_role,))
            else:
                cur.execute("""
                    SELECT * FROM agent_feedback_stats ORDER BY total_ratings DESC
                """)
            rows = cur.fetchall()
            return [dict(r) for fetched in rows if (r := _as_row(fetched)) is not None]
    finally:
        release_conn(conn)


def get_feedback_leaderboard(limit: int = 10) -> list[dict]:
    """Get agents ranked by satisfaction rate."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    agent_role,
                    total_ratings,
                    positive,
                    negative,
                    neutral,
                    satisfaction_rate
                FROM agent_feedback_stats
                WHERE total_ratings >= 5
                ORDER BY satisfaction_rate DESC, total_ratings DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            return [dict(r) for fetched in rows if (r := _as_row(fetched)) is not None]
    finally:
        release_conn(conn)


def get_feedback_trends(days: int = 7) -> dict:
    """Get feedback trends over time."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    DATE(created_at) as date,
                    agent_role,
                    COUNT(*) as total,
                    SUM(CASE WHEN rating = 'positive' THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN rating = 'negative' THEN 1 ELSE 0 END) as negative
                FROM user_feedback
                WHERE created_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(created_at), agent_role
                ORDER BY date DESC, agent_role
            """, (days,))
            rows = cur.fetchall()
            
            # Organize by date
            trends = {}
            for fetched in rows:
                r = _as_row(fetched)
                if r is None:
                    continue
                date_str = str(r["date"])
                if date_str not in trends:
                    trends[date_str] = {}
                trends[date_str][r["agent_role"]] = {
                    "total": r["total"],
                    "positive": r["positive"],
                    "negative": r["negative"],
                    "satisfaction": round(r["positive"] / r["total"] * 100, 1) if r["total"] > 0 else 0,
                }
            
            return {
                "period_days": days,
                "trends": trends,
            }
    finally:
        release_conn(conn)


def get_rlhf_training_data(limit: int = 100) -> dict[str, Any]:
    """
    Get training data for RLHF.
    Returns pairs of positive/negative feedback for the same task type.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Get positive feedback with context
            cur.execute("""
                SELECT 
                    task_input,
                    task_output,
                    agent_role,
                    rating,
                    feedback_text
                FROM user_feedback
                WHERE rating = 'positive' AND task_input IS NOT NULL
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            positive = [
                dict(r)
                for fetched in cur.fetchall()
                if (r := _as_row(fetched)) is not None
            ]
            
            # Get negative feedback with context
            cur.execute("""
                SELECT 
                    task_input,
                    task_output,
                    agent_role,
                    rating,
                    feedback_text
                FROM user_feedback
                WHERE rating = 'negative' AND task_input IS NOT NULL
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            negative = [
                dict(r)
                for fetched in cur.fetchall()
                if (r := _as_row(fetched)) is not None
            ]
            
            return {
                "positive_examples": positive,
                "negative_examples": negative,
                "total_positive": len(positive),
                "total_negative": len(negative),
            }
    finally:
        release_conn(conn)


# ── API Response Helpers ────────────────────────────────────────

def format_feedback_for_display(feedback: dict) -> str:
    """Format feedback for display in UI."""
    rating_emoji = {
        "positive": "👍",
        "negative": "👎",
        "neutral": "😐",
    }
    
    emoji = rating_emoji.get(feedback.get("rating", ""), "❓")
    agent = feedback.get("agent_role", "unknown")
    text = feedback.get("feedback_text", "")
    
    result = f"{emoji} {agent}"
    if text:
        result += f": {text[:100]}"
    
    return result