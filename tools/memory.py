"""
Agent Memory — PostgreSQL + pgvector powered persistent knowledge store.
Layered memory: working (TTL) / episodic (task results) / semantic (permanent).
Uses NVIDIA nv-embedqa-e5-v5 for semantic vector search via pgvector.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from typing import Any

import httpx

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

_EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
_EMBED_DIMENSIONS = 1024


# ── Embedding ────────────────────────────────────────────────────

def _get_embedding(text: str) -> list[float] | None:
    """Get embedding vector from NVIDIA API. Returns None on failure."""
    try:
        from config import NVIDIA_API_KEY, NVIDIA_BASE_URL
        if not NVIDIA_API_KEY:
            return None

        resp = httpx.post(
            f"{NVIDIA_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": _EMBED_MODEL,
                "input": [text[:2048]],
                "encoding_format": "float",
                "input_type": "query",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding API failed: {e}")
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Python fallback cosine similarity (prefer pgvector in queries)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── Helpers ──────────────────────────────────────────────────────

def _row_to_dict(row: dict) -> dict[str, Any]:
    tags = row.get("tags", "[]")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
    return {
        "id": row["id"],
        "content": row["content"],
        "category": row["category"],
        "memory_layer": row.get("memory_layer", "episodic"),
        "tags": tags,
        "source_agent": row.get("source_agent"),
        "access_count": row.get("access_count", 0),
        "created_at": str(row.get("created_at", "")),
        "similarity": row.get("similarity"),
    }


def _insert_memory(
    content: str,
    category: str,
    memory_layer: str,
    tags: list[str],
    source_agent: str | None,
    ttl_hours: int | None = None,
) -> dict[str, Any]:
    """Core insert — shared by all save_* functions."""
    tags_json = json.dumps(tags, ensure_ascii=False)
    embedding = _get_embedding(content)
    emb_str = str(embedding) if embedding else None

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO memories
                   (content, category, memory_layer, tags, source_agent, embedding, ttl_hours)
                   VALUES (%s, %s, %s, %s, %s, %s::vector, %s)
                   RETURNING id, created_at""",
                (content, category, memory_layer, tags_json, source_agent, emb_str, ttl_hours),
            )
            row = cur.fetchone()
        conn.commit()
        backend = "pgvector" if embedding else "keyword-only"
        logger.info(f"Memory saved [{memory_layer}/{backend}]: {content[:50]}")
        return {
            "id": row["id"],
            "content": content,
            "category": category,
            "memory_layer": memory_layer,
            "tags": tags,
            "source_agent": source_agent,
            "created_at": str(row["created_at"]),
        }
    finally:
        release_conn(conn)


# ── Public API — Core ────────────────────────────────────────────

def save_memory(
    content: str,
    category: str = "general",
    tags: list[str] | None = None,
    source_agent: str | None = None,
) -> dict[str, Any]:
    """Save an episodic memory (default layer)."""
    return _insert_memory(content, category, "episodic", tags or [], source_agent)


def recall_memory(
    query: str,
    category: str | None = None,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Recall memories across all layers — pgvector semantic search with keyword fallback."""
    embedding = _get_embedding(query)
    if embedding:
        results = _pgvector_recall(embedding, category, max_results)
        if results:
            return results
    return _keyword_recall(query, category, max_results)


def list_memories(
    category: str | None = None,
    layer: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List recent memories, optionally filtered by category and/or memory layer."""
    conn = get_conn()
    try:
        conditions = []
        params: list[Any] = []

        if category:
            conditions.append("category = %s")
            params.append(category)
        if layer:
            conditions.append("memory_layer = %s")
            params.append(layer)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, content, category, memory_layer, tags, source_agent,
                          access_count, created_at
                   FROM memories {where}
                   ORDER BY created_at DESC LIMIT %s""",
                params + [limit],
            )
            return [_row_to_dict(dict(r)) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def delete_memory(memory_id: int) -> bool:
    """Delete a memory by ID."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        release_conn(conn)


def get_memory_stats() -> dict[str, Any]:
    """Get memory usage statistics."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(DISTINCT category) AS categories,
                    COUNT(embedding) AS with_embeddings,
                    SUM(access_count) AS total_accesses,
                    MAX(created_at) AS last_saved,
                    COUNT(*) FILTER (WHERE memory_layer = 'working')  AS working_count,
                    COUNT(*) FILTER (WHERE memory_layer = 'episodic') AS episodic_count,
                    COUNT(*) FILTER (WHERE memory_layer = 'semantic') AS semantic_count
                FROM memories
            """)
            row = dict(cur.fetchone())
        return {
            "total_memories": row["total"],
            "categories": row["categories"],
            "with_embeddings": row["with_embeddings"],
            "total_accesses": row["total_accesses"] or 0,
            "last_saved": str(row["last_saved"]) if row["last_saved"] else None,
            "layers": {
                "working": row["working_count"],
                "episodic": row["episodic_count"],
                "semantic": row["semantic_count"],
            },
            "backend": "PostgreSQL + pgvector",
        }
    finally:
        release_conn(conn)


def format_recall_results(results: list[dict]) -> str:
    """Format memory results for LLM context injection."""
    if not results:
        return "No relevant memories found."

    parts = [f"Found {len(results)} relevant memories:\n"]
    for i, mem in enumerate(results, 1):
        tags = ", ".join(mem.get("tags") or []) or "none"
        sim = mem.get("similarity")
        sim_str = f" | Similarity: {sim:.3f}" if sim is not None else ""
        layer = mem.get("memory_layer", "episodic")
        parts.append(
            f"{i}. [{mem.get('category', 'general')}|{layer}] {mem['content'][:300]}\n"
            f"   Tags: {tags} | Agent: {mem.get('source_agent', 'unknown')} | "
            f"Date: {str(mem.get('created_at', ''))[:10]}{sim_str}"
        )
    return "\n".join(parts)


# ── Layered Memory API ───────────────────────────────────────────

def save_working_memory(
    content: str,
    source_agent: str | None = None,
    ttl_hours: int = 24,
) -> dict[str, Any]:
    """Short-term working memory with TTL (auto-expires)."""
    return _insert_memory(content, "working", "working", [], source_agent, ttl_hours)


def save_episodic_memory(
    content: str,
    category: str = "general",
    tags: list[str] | None = None,
    source_agent: str | None = None,
) -> dict[str, Any]:
    """Episodic memory — task results, interactions."""
    return _insert_memory(content, category, "episodic", tags or [], source_agent)


def save_semantic_memory(
    content: str,
    category: str = "knowledge",
    tags: list[str] | None = None,
    source_agent: str | None = None,
) -> dict[str, Any]:
    """Semantic memory — permanent knowledge, facts."""
    return _insert_memory(content, category, "semantic", tags or [], source_agent)


def recall_layered(
    query: str,
    layers: list[str] | None = None,
    max_results: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    """
    Recall memories grouped by layer.
    Returns dict with keys: working, episodic, semantic.
    """
    target_layers = layers or ["working", "episodic", "semantic"]
    embedding = _get_embedding(query)

    result: dict[str, list[dict]] = {layer: [] for layer in target_layers}

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for layer in target_layers:
                if embedding:
                    cur.execute(
                        """SELECT id, content, category, memory_layer, tags, source_agent,
                                  access_count, created_at,
                                  1 - (embedding <=> %s::vector) AS similarity
                           FROM memories
                           WHERE memory_layer = %s AND embedding IS NOT NULL
                           ORDER BY embedding <=> %s::vector
                           LIMIT %s""",
                        (str(embedding), layer, str(embedding), max_results),
                    )
                    rows = cur.fetchall()
                    if rows:
                        result[layer] = [_row_to_dict(dict(r)) for r in rows]
                        continue

                # keyword fallback per layer
                cur.execute(
                    """SELECT id, content, category, memory_layer, tags, source_agent,
                              access_count, created_at
                       FROM memories
                       WHERE memory_layer = %s AND LOWER(content) LIKE %s
                       ORDER BY created_at DESC LIMIT %s""",
                    (layer, f"%{query.lower()[:50]}%", max_results),
                )
                result[layer] = [_row_to_dict(dict(r)) for r in cur.fetchall()]

        # Update access counts for all returned memories
        all_ids = [m["id"] for layer_mems in result.values() for m in layer_mems]
        if all_ids:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE memories SET access_count = access_count + 1 WHERE id = ANY(%s)",
                    (all_ids,),
                )
            conn.commit()
    finally:
        release_conn(conn)

    return result


def cleanup_expired_working_memory() -> int:
    """Delete working memory rows past their TTL."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM memories
                   WHERE ttl_hours IS NOT NULL
                     AND created_at < now() - (ttl_hours || ' hours')::interval"""
            )
            deleted = cur.rowcount
        conn.commit()
        if deleted:
            logger.info(f"Cleaned up {deleted} expired working memory rows")
        return deleted
    finally:
        release_conn(conn)


# ── Internal Search ──────────────────────────────────────────────

def _pgvector_recall(
    embedding: list[float],
    category: str | None,
    max_results: int,
) -> list[dict[str, Any]]:
    """pgvector cosine similarity search."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if category:
                cur.execute(
                    """SELECT id, content, category, memory_layer, tags, source_agent,
                              access_count, created_at,
                              1 - (embedding <=> %s::vector) AS similarity
                       FROM memories
                       WHERE embedding IS NOT NULL AND category = %s
                         AND 1 - (embedding <=> %s::vector) > 0.3
                       ORDER BY embedding <=> %s::vector
                       LIMIT %s""",
                    (str(embedding), category, str(embedding), str(embedding), max_results),
                )
            else:
                cur.execute(
                    """SELECT id, content, category, memory_layer, tags, source_agent,
                              access_count, created_at,
                              1 - (embedding <=> %s::vector) AS similarity
                       FROM memories
                       WHERE embedding IS NOT NULL
                         AND 1 - (embedding <=> %s::vector) > 0.3
                       ORDER BY embedding <=> %s::vector
                       LIMIT %s""",
                    (str(embedding), str(embedding), str(embedding), max_results),
                )
            rows = cur.fetchall()

        if not rows:
            return []

        results = [_row_to_dict(dict(r)) for r in rows]
        ids = [r["id"] for r in results]
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE memories SET access_count = access_count + 1 WHERE id = ANY(%s)",
                (ids,),
            )
        conn.commit()
        return results
    finally:
        release_conn(conn)


def _keyword_recall(
    query: str,
    category: str | None,
    max_results: int,
) -> list[dict[str, Any]]:
    """Keyword fallback search."""
    words = [w for w in query.lower().split() if len(w) > 2]
    if not words:
        words = [query.lower()]

    conn = get_conn()
    try:
        conditions = ["1=1"]
        params: list[Any] = []

        if category:
            conditions.append("category = %s")
            params.append(category)

        like_parts = [f"LOWER(content) LIKE %s" for _ in words[:10]]
        params.extend(f"%{w}%" for w in words[:10])
        conditions.append(f"({' OR '.join(like_parts)})")

        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, content, category, memory_layer, tags, source_agent,
                           access_count, created_at
                    FROM memories
                    WHERE {' AND '.join(conditions)}
                    ORDER BY created_at DESC LIMIT %s""",
                params + [max_results * 5],
            )
            rows = cur.fetchall()

        if not rows:
            return []

        query_lower = query.lower()
        scored = []
        for row in rows:
            d = dict(row)
            score = sum(2.0 for w in words if w in d["content"].lower())
            if query_lower in d["content"].lower():
                score += 5.0
            if score > 0:
                scored.append((score, _row_to_dict(d)))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item for _, item in scored[:max_results]]

        if results:
            ids = [r["id"] for r in results]
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE memories SET access_count = access_count + 1 WHERE id = ANY(%s)",
                    (ids,),
                )
            conn.commit()

        return results
    finally:
        release_conn(conn)
