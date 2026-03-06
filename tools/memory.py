"""
Agent Memory — PostgreSQL + pgvector powered persistent knowledge store.
Layered memory: working (TTL) / episodic (task results) / semantic (permanent).
Uses NVIDIA nv-embedqa-e5-v5 for semantic vector search via pgvector.
"""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Mapping
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

def _as_row_dict(row: Any) -> dict[str, Any]:
    """Normalize DB row values from psycopg into a plain dict."""
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if isinstance(row, Mapping):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {}


def _row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    tags = row.get("tags", "[]")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
    return {
        "id": row.get("id"),
        "content": row.get("content", ""),
        "category": row.get("category", "general"),
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
            row = _as_row_dict(cur.fetchone())
        conn.commit()
        backend = "pgvector" if embedding else "keyword-only"
        logger.info(f"Memory saved [{memory_layer}/{backend}]: {content[:50]}")
        return {
            "id": row.get("id"),
            "content": content,
            "category": category,
            "memory_layer": memory_layer,
            "tags": tags,
            "source_agent": source_agent,
            "created_at": str(row.get("created_at", "")),
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
            return [_row_to_dict(_as_row_dict(r)) for r in cur.fetchall()]
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
            row = _as_row_dict(cur.fetchone())
        return {
            "total_memories": row.get("total", 0),
            "categories": row.get("categories", 0),
            "with_embeddings": row.get("with_embeddings", 0),
            "total_accesses": row.get("total_accesses") or 0,
            "last_saved": str(row.get("last_saved")) if row.get("last_saved") else None,
            "layers": {
                "working": row.get("working_count", 0),
                "episodic": row.get("episodic_count", 0),
                "semantic": row.get("semantic_count", 0),
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
                        result[layer] = [_row_to_dict(_as_row_dict(r)) for r in rows]
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
                result[layer] = [_row_to_dict(_as_row_dict(r)) for r in cur.fetchall()]

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


# ── Advanced Indexing & Correlation ──────────────────────────────

def correlate_memories(
    query: str,
    max_results: int = 10,
    time_window_hours: int | None = None,
) -> dict[str, Any]:
    """
    Find correlated memories across layers and categories.
    Groups by time proximity and semantic similarity.
    Returns clusters of related memories with correlation scores.
    """
    embedding = _get_embedding(query)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            time_filter = ""
            params: list[Any] = []

            if time_window_hours:
                time_filter = "AND created_at > now() - interval '%s hours'"
                params.append(time_window_hours)

            if embedding:
                cur.execute(
                    f"""SELECT id, content, category, memory_layer, tags, source_agent,
                               access_count, created_at,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM memories
                        WHERE embedding IS NOT NULL
                          AND 1 - (embedding <=> %s::vector) > 0.25
                          {time_filter}
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s""",
                    [str(embedding), str(embedding)] + params + [str(embedding), max_results * 2],
                )
            else:
                words = [w for w in query.lower().split() if len(w) > 2][:5]
                like_parts = " OR ".join(f"LOWER(content) LIKE %s" for _ in words) if words else "TRUE"
                word_params = [f"%{w}%" for w in words]
                cur.execute(
                    f"""SELECT id, content, category, memory_layer, tags, source_agent,
                               access_count, created_at
                        FROM memories
                        WHERE ({like_parts}) {time_filter}
                        ORDER BY created_at DESC
                        LIMIT %s""",
                    word_params + params + [max_results * 2],
                )

            rows = [_row_to_dict(_as_row_dict(r)) for r in cur.fetchall()]

        if not rows:
            return {"clusters": [], "total_found": 0}

        # Group by time proximity (within 1 hour = same cluster)
        clusters: list[dict[str, Any]] = []
        used = set()

        for i, mem in enumerate(rows):
            if i in used:
                continue
            cluster_members = [mem]
            used.add(i)
            mem_ts = mem.get("created_at", "")

            for j, other in enumerate(rows):
                if j in used:
                    continue
                other_ts = other.get("created_at", "")
                # Same category or same agent = likely correlated
                same_category = mem.get("category") == other.get("category")
                same_agent = mem.get("source_agent") == other.get("source_agent")
                high_sim = (mem.get("similarity") or 0) > 0.5 and (other.get("similarity") or 0) > 0.5

                if same_category or same_agent or high_sim:
                    cluster_members.append(other)
                    used.add(j)

            if cluster_members:
                avg_sim = sum(m.get("similarity") or 0 for m in cluster_members) / len(cluster_members)
                clusters.append({
                    "members": cluster_members[:max_results],
                    "size": len(cluster_members),
                    "primary_category": mem.get("category"),
                    "primary_agent": mem.get("source_agent"),
                    "avg_similarity": round(avg_sim, 3),
                })

        clusters.sort(key=lambda c: c["avg_similarity"], reverse=True)
        return {
            "clusters": clusters[:5],
            "total_found": len(rows),
        }
    finally:
        release_conn(conn)


def get_memory_timeline(
    hours: int = 24,
    group_by: str = "hour",
) -> list[dict[str, Any]]:
    """
    Get memory creation timeline grouped by time intervals.
    Useful for understanding memory activity patterns.
    group_by: 'hour', 'day', or 'category'
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if group_by == "category":
                cur.execute(
                    """SELECT category,
                              COUNT(*) AS count,
                              MAX(created_at) AS latest,
                              array_agg(DISTINCT memory_layer) AS layers
                       FROM memories
                       WHERE created_at > now() - interval '%s hours'
                       GROUP BY category
                       ORDER BY count DESC""",
                    (hours,),
                )
                return [
                    {
                        "group": _as_row_dict(r).get("category", "unknown"),
                        "count": _as_row_dict(r).get("count", 0),
                        "latest": str(_as_row_dict(r).get("latest", "")),
                        "layers": _as_row_dict(r).get("layers", []),
                    }
                    for r in cur.fetchall()
                ]
            else:
                trunc = "hour" if group_by == "hour" else "day"
                cur.execute(
                    f"""SELECT date_trunc(%s, created_at) AS period,
                               COUNT(*) AS count,
                               COUNT(DISTINCT source_agent) AS agents,
                               COUNT(DISTINCT category) AS categories
                        FROM memories
                        WHERE created_at > now() - interval '%s hours'
                        GROUP BY period
                        ORDER BY period DESC""",
                    (trunc, hours),
                )
                return [
                    {
                        "period": str(_as_row_dict(r).get("period", "")),
                        "count": _as_row_dict(r).get("count", 0),
                        "agents": _as_row_dict(r).get("agents", 0),
                        "categories": _as_row_dict(r).get("categories", 0),
                    }
                    for r in cur.fetchall()
                ]
    finally:
        release_conn(conn)


def find_related_memories(
    memory_id: int,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Find memories related to a specific memory by its ID.
    Uses the source memory's embedding for similarity search,
    falls back to category + tag matching.
    """
    conn = get_conn()
    try:
        # Fetch the source memory
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, content, category, memory_layer, tags, source_agent,
                          embedding
                   FROM memories WHERE id = %s""",
                (memory_id,),
            )
            source_row = cur.fetchone()

        if not source_row:
            return []

        source = _as_row_dict(source_row)
        source_embedding = source.get("embedding")

        with conn.cursor() as cur:
            if source_embedding is not None:
                # pgvector similarity search using source embedding
                cur.execute(
                    """SELECT id, content, category, memory_layer, tags, source_agent,
                              access_count, created_at,
                              1 - (embedding <=> (SELECT embedding FROM memories WHERE id = %s)) AS similarity
                       FROM memories
                       WHERE id != %s AND embedding IS NOT NULL
                       ORDER BY embedding <=> (SELECT embedding FROM memories WHERE id = %s)
                       LIMIT %s""",
                    (memory_id, memory_id, memory_id, max_results),
                )
            else:
                # Fallback: same category + recent
                cur.execute(
                    """SELECT id, content, category, memory_layer, tags, source_agent,
                              access_count, created_at
                       FROM memories
                       WHERE id != %s AND category = %s
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (memory_id, source.get("category", "general"), max_results),
                )

            return [_row_to_dict(_as_row_dict(r)) for r in cur.fetchall()]
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

        results = [_row_to_dict(_as_row_dict(r)) for r in rows]
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
            d = _as_row_dict(row)
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
