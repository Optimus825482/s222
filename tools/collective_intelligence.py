"""
Collective Intelligence System

Enables agents to share knowledge, learn from each other,
and build a collective consciousness for Nexus AI Team.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)


def _scalar_from_row(row: Any, default: int = 0) -> int:
    if row is None:
        return default
    if isinstance(row, tuple):
        value = row[0] if row else default
        return int(value) if value is not None else default
    return default


# ── Knowledge Sharing ───────────────────────────────────────────

def share_knowledge(
    source_agent: str,
    knowledge_type: str,
    content: str,
    context: str | None = None,
    confidence: float = 1.0,
) -> dict[str, Any]:
    """
    Share knowledge from one agent to the collective.
    
    Knowledge types:
    - insight: A discovery or realization
    - pattern: A recurring behavior or structure
    - skill: A learned capability
    - correction: An error fix or improvement
    - preference: User preference learned
    - fact: Verified information
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO collective_knowledge 
                   (source_agent, knowledge_type, content, context, confidence)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING id, created_at""",
                (source_agent, knowledge_type, content[:2000], context, confidence),
            )
            row = cur.fetchone()
        conn.commit()
        logger.info(f"Knowledge shared by {source_agent}: [{knowledge_type}] {content[:50]}")
        return {
            "id": row[0] if row else None,
            "source_agent": source_agent,
            "knowledge_type": knowledge_type,
            "content": content,
            "confidence": confidence,
        }
    finally:
        release_conn(conn)


def get_relevant_knowledge(
    query: str,
    knowledge_types: list[str] | None = None,
    min_confidence: float = 0.5,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Retrieve knowledge relevant to current context."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            base_query = """
                SELECT * FROM collective_knowledge 
                WHERE confidence >= %s AND active = TRUE
            """
            params: list[object] = [min_confidence]
            
            if knowledge_types:
                base_query += " AND knowledge_type = ANY(%s)"
                params.append(knowledge_types)
            
            base_query += " ORDER BY use_count DESC, confidence DESC, created_at DESC LIMIT %s"
            params.append(max_results)
            
            cur.execute(base_query, params)
            rows = cur.fetchall()
            
            results = [_row_to_knowledge(r) for r in rows]
            
            # Update use count
            if results:
                ids = [r["id"] for r in results]
                cur.execute(
                    "UPDATE collective_knowledge SET use_count = use_count + 1 WHERE id = ANY(%s)",
                    (ids,),
                )
            conn.commit()
            
            return results
    finally:
        release_conn(conn)


def get_knowledge_by_agent(agent: str) -> list[dict[str, Any]]:
    """Get all knowledge contributed by a specific agent."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM collective_knowledge 
                   WHERE source_agent = %s AND active = TRUE
                   ORDER BY created_at DESC""",
                (agent,),
            )
            return [_row_to_knowledge(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


# ── Experience Sharing ──────────────────────────────────────────

def record_experience(
    task_id: str,
    agent: str,
    experience_type: str,
    description: str,
    outcome: str,
    lessons_learned: list[str] | None = None,
) -> dict[str, Any]:
    """
    Record an experience from a task execution.
    
    Experience types:
    - success: Task completed successfully
    - failure: Task failed, but learned something
    - challenge: Encountered difficulty, overcame it
    - discovery: Found something unexpected
    - optimization: Improved a process
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO agent_experiences
                   (task_id, agent, experience_type, description, outcome, lessons_learned)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id, created_at""",
                (
                    task_id,
                    agent,
                    experience_type,
                    description[:1000],
                    outcome[:500],
                    json.dumps(lessons_learned or []),
                ),
            )
            row = cur.fetchone()
        conn.commit()
        
        # Extract knowledge from lessons learned
        if lessons_learned:
            for lesson in lessons_learned:
                share_knowledge(
                    source_agent=agent,
                    knowledge_type="insight",
                    content=lesson,
                    context=f"Task: {task_id}",
                    confidence=0.8,
                )
        
        return {
            "id": row[0] if row else None,
            "task_id": task_id,
            "agent": agent,
            "experience_type": experience_type,
        }
    finally:
        release_conn(conn)


def get_relevant_experiences(
    context: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Find experiences relevant to current context."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Simple keyword matching for now
            cur.execute(
                """SELECT * FROM agent_experiences 
                   ORDER BY created_at DESC LIMIT 50"""
            )
            rows = cur.fetchall()
            
            # Score by relevance
            context_words = set(context.lower().split())
            scored = []
            for row in rows:
                exp = _row_to_experience(row)
                desc_words = set(exp.get("description", "").lower().split())
                score = len(context_words & desc_words)
                if score > 0:
                    scored.append((score, exp))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            return [exp for _, exp in scored[:max_results]]
    finally:
        release_conn(conn)


# ── Cross-Agent Learning ────────────────────────────────────────

def distill_knowledge_to_agent(target_agent: str) -> str:
    """
    Prepare relevant collective knowledge for injection into agent context.
    """
    knowledge = get_relevant_knowledge(
        query=target_agent,  # Use agent name as context
        max_results=15,
    )
    
    if not knowledge:
        return ""
    
    lines = ["### KOLEKTİF BİLGİ ###"]
    lines.append("Diğer agent'lardan öğrenilenler:\n")
    
    # Group by type
    by_type: dict[str, list] = {}
    for k in knowledge:
        kt = k.get("knowledge_type", "other")
        if kt not in by_type:
            by_type[kt] = []
        by_type[kt].append(k)
    
    for ktype, items in by_type.items():
        lines.append(f"**{ktype.upper()}:**")
        for item in items[:5]:
            source = item.get("source_agent", "unknown")
            content = item.get("content", "")[:200]
            confidence = item.get("confidence", 0)
            lines.append(f"  • [{source}] {content} (güven: {confidence:.0%})")
        lines.append("")
    
    lines.append("### BİLGİ SONU ###")
    return "\n".join(lines)


def get_agent_strengths() -> dict[str, dict[str, Any]]:
    """
    Analyze each agent's strengths based on collective knowledge.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source_agent, knowledge_type, COUNT(*) as count, AVG(confidence) as avg_conf
                FROM collective_knowledge
                WHERE active = TRUE
                GROUP BY source_agent, knowledge_type
                ORDER BY source_agent, count DESC
            """)
            rows = cur.fetchall()
            
            strengths: dict[str, dict[str, Any]] = {}
            for row in rows:
                agent = row[0]
                ktype = row[1]
                count = row[2]
                avg_conf = row[3]
                
                if agent not in strengths:
                    strengths[agent] = {
                        "total_contributions": 0,
                        "areas": {},
                    }
                
                strengths[agent]["total_contributions"] += count
                strengths[agent]["areas"][ktype] = {
                    "contributions": count,
                    "avg_confidence": float(avg_conf) if avg_conf else 0,
                }
            
            return strengths
    finally:
        release_conn(conn)


# ── Collective Status ───────────────────────────────────────────

def get_collective_status() -> dict[str, Any]:
    """Get overall collective intelligence status."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Total knowledge
            cur.execute("SELECT COUNT(*) FROM collective_knowledge WHERE active = TRUE")
            total_knowledge = _scalar_from_row(cur.fetchone())
            
            # Knowledge by type
            cur.execute("""
                SELECT knowledge_type, COUNT(*) 
                FROM collective_knowledge 
                WHERE active = TRUE 
                GROUP BY knowledge_type
            """)
            by_type = {row[0]: row[1] for row in cur.fetchall()}
            
            # Knowledge by agent
            cur.execute("""
                SELECT source_agent, COUNT(*) 
                FROM collective_knowledge 
                WHERE active = TRUE 
                GROUP BY source_agent
            """)
            by_agent = {row[0]: row[1] for row in cur.fetchall()}
            
            # Recent activity
            cur.execute("""
                SELECT COUNT(*) FROM collective_knowledge 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            recent = _scalar_from_row(cur.fetchone())
            
            return {
                "total_knowledge_items": total_knowledge,
                "knowledge_by_type": by_type,
                "knowledge_by_agent": by_agent,
                "recent_24h": recent,
                "active_agents": list(by_agent.keys()),
            }
    finally:
        release_conn(conn)


# ── Database Tables ─────────────────────────────────────────────

def ensure_collective_tables() -> None:
    """Create collective intelligence tables if not exist."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS collective_knowledge (
                    id SERIAL PRIMARY KEY,
                    source_agent VARCHAR(100) NOT NULL,
                    knowledge_type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    context TEXT,
                    confidence FLOAT DEFAULT 1.0,
                    use_count INT DEFAULT 0,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_experiences (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(100),
                    agent VARCHAR(100) NOT NULL,
                    experience_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    outcome TEXT,
                    lessons_learned JSONB DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_type 
                ON collective_knowledge(knowledge_type)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_agent 
                ON collective_knowledge(source_agent)
            """)
            
        conn.commit()
        logger.info("Collective intelligence tables ensured")
    except Exception as e:
        logger.error(f"Failed to create collective tables: {e}")
    finally:
        release_conn(conn)


# ── Helpers ─────────────────────────────────────────────────────

def _row_to_knowledge(row: Any) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "id": row[0] if len(row) > 0 else None,
        "source_agent": row[1] if len(row) > 1 else None,
        "knowledge_type": row[2] if len(row) > 2 else None,
        "content": row[3] if len(row) > 3 else None,
        "context": row[4] if len(row) > 4 else None,
        "confidence": float(row[5]) if len(row) > 5 and row[5] else 0,
        "use_count": row[6] if len(row) > 6 else 0,
        "active": row[7] if len(row) > 7 else True,
        "created_at": str(row[8]) if len(row) > 8 else None,
    }


def _row_to_experience(row: Any) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "id": row[0] if len(row) > 0 else None,
        "task_id": row[1] if len(row) > 1 else None,
        "agent": row[2] if len(row) > 2 else None,
        "experience_type": row[3] if len(row) > 3 else None,
        "description": row[4] if len(row) > 4 else None,
        "outcome": row[5] if len(row) > 5 else None,
        "lessons_learned": row[6] if len(row) > 6 else [],
        "created_at": str(row[7]) if len(row) > 7 else None,
    }