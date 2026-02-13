"""
Agent Memory — SQLite persistent knowledge store.
Lightweight, same-container, zero-config database for agent memories.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "memory.db"

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    """Lazy singleton connection with WAL mode for concurrent reads."""
    global _conn
    if _conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _init_schema(_conn)
    return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content     TEXT NOT NULL,
            category    TEXT NOT NULL DEFAULT 'general',
            tags        TEXT NOT NULL DEFAULT '[]',
            source_agent TEXT,
            access_count INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
        CREATE INDEX IF NOT EXISTS idx_memories_created  ON memories(created_at DESC);
    """)
    conn.commit()


def save_memory(
    content: str,
    category: str = "general",
    tags: list[str] | None = None,
    source_agent: str | None = None,
) -> dict:
    """Save a memory entry to SQLite."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    tags_json = json.dumps(tags or [], ensure_ascii=False)

    cur = conn.execute(
        """INSERT INTO memories (content, category, tags, source_agent, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (content, category, tags_json, source_agent, now, now),
    )
    conn.commit()

    return {
        "id": cur.lastrowid,
        "content": content,
        "category": category,
        "tags": tags or [],
        "source_agent": source_agent,
        "created_at": now,
    }


def recall_memory(
    query: str,
    category: str | None = None,
    max_results: int = 5,
) -> list[dict]:
    """
    Search memories by keyword scoring.
    Uses SQL LIKE for initial filter, then Python scoring for ranking.
    """
    conn = _get_conn()

    # Build query — fetch candidates that contain at least one keyword
    query_words = [w for w in query.lower().split() if len(w) > 2]
    if not query_words:
        query_words = [query.lower()]

    conditions = ["1=1"]
    params: list[Any] = []

    if category:
        conditions.append("category = ?")
        params.append(category)

    # LIKE filter for any keyword match
    like_parts = []
    for word in query_words[:10]:  # max 10 keywords
        like_parts.append("LOWER(content) LIKE ?")
        params.append(f"%{word}%")

    if like_parts:
        conditions.append(f"({' OR '.join(like_parts)})")

    sql = f"""
        SELECT id, content, category, tags, source_agent, access_count, created_at
        FROM memories
        WHERE {' AND '.join(conditions)}
        ORDER BY created_at DESC
        LIMIT 50
    """

    rows = conn.execute(sql, params).fetchall()
    if not rows:
        return []

    # Score and rank
    scored = []
    query_lower = query.lower()
    for row in rows:
        score = 0.0
        content_lower = row["content"].lower()

        for word in query_words:
            if word in content_lower:
                score += 2.0

        if query_lower in content_lower:
            score += 5.0

        # Tag match
        try:
            row_tags = json.loads(row["tags"])
            for tag in row_tags:
                if tag.lower() in query_lower or query_lower in tag.lower():
                    score += 2.0
        except (json.JSONDecodeError, TypeError):
            row_tags = []

        # Recency bonus
        try:
            created = datetime.fromisoformat(row["created_at"])
            age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
            if age_hours < 24:
                score += 2.0
            elif age_hours < 168:
                score += 1.0
        except (ValueError, KeyError):
            pass

        if score > 0:
            scored.append((score, {
                "id": row["id"],
                "content": row["content"],
                "category": row["category"],
                "tags": row_tags,
                "source_agent": row["source_agent"],
                "access_count": row["access_count"],
                "created_at": row["created_at"],
            }))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [item for _, item in scored[:max_results]]

    # Update access counts
    if results:
        ids = [r["id"] for r in results]
        placeholders = ",".join("?" * len(ids))
        conn.execute(
            f"UPDATE memories SET access_count = access_count + 1 WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()

    return results


def list_memories(category: str | None = None, limit: int = 20) -> list[dict]:
    """List recent memories."""
    conn = _get_conn()
    if category:
        rows = conn.execute(
            "SELECT * FROM memories WHERE category = ? ORDER BY created_at DESC LIMIT ?",
            (category, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return [
        {
            "id": r["id"],
            "content": r["content"],
            "category": r["category"],
            "tags": json.loads(r["tags"]) if r["tags"] else [],
            "source_agent": r["source_agent"],
            "access_count": r["access_count"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def delete_memory(memory_id: int) -> bool:
    """Delete a memory by ID."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    return cur.rowcount > 0


def get_memory_stats() -> dict:
    """Get memory usage statistics."""
    conn = _get_conn()
    row = conn.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT category) as categories,
            SUM(access_count) as total_accesses,
            MAX(created_at) as last_saved
        FROM memories
    """).fetchone()
    return {
        "total_memories": row["total"],
        "categories": row["categories"],
        "total_accesses": row["total_accesses"] or 0,
        "last_saved": row["last_saved"],
    }


def format_recall_results(results: list[dict]) -> str:
    """Format memory results for LLM context injection."""
    if not results:
        return "No relevant memories found."

    parts = [f"Found {len(results)} relevant memories:\n"]
    for i, mem in enumerate(results, 1):
        tags = ", ".join(mem.get("tags", [])) or "none"
        parts.append(
            f"{i}. [{mem.get('category', 'general')}] {mem['content'][:300]}\n"
            f"   Tags: {tags} | Agent: {mem.get('source_agent', 'unknown')} | "
            f"Date: {mem.get('created_at', 'unknown')[:10]}"
        )
    return "\n".join(parts)
