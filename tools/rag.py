"""
RAG Pipeline — PostgreSQL + pgvector document ingestion and retrieval.
Same public API as SQLite version.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
MAX_CHUNKS_PER_DOC = 200


# ── Embedding ────────────────────────────────────────────────────

def _get_embedding(text: str) -> list[float] | None:
    try:
        from tools.memory import _get_embedding as mem_embed
        return mem_embed(text)
    except Exception as e:
        logger.warning(f"RAG embedding failed: {e}")
        return None


# ── Text Extraction ──────────────────────────────────────────────

def extract_text_from_file(filepath: str) -> tuple[str, str]:
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md", ".csv", ".log", ".json", ".yaml", ".yml"):
        return path.read_text(encoding="utf-8", errors="ignore"), "text"

    if suffix == ".html":
        raw = path.read_text(encoding="utf-8", errors="ignore")
        clean = re.sub(r"<[^>]+>", " ", raw)
        return re.sub(r"\s+", " ", clean).strip(), "html"

    if suffix == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(path))
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text, "pdf"
        except ImportError:
            try:
                import pdfplumber
                with pdfplumber.open(str(path)) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                return text, "pdf"
            except ImportError:
                return "", "pdf_unsupported"

    return path.read_text(encoding="utf-8", errors="ignore"), "unknown"


# ── Chunking ─────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    char_size = chunk_size * 4
    char_overlap = overlap * 4

    if len(text) <= char_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + char_size
        if end < len(text):
            for sep in [". ", ".\n", "\n\n", "\n"]:
                boundary = text.rfind(sep, start + char_size // 2, end + 100)
                if boundary > start:
                    end = boundary + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if len(chunks) >= MAX_CHUNKS_PER_DOC:
            break
        start = end - char_overlap

    return chunks


# ── Public API ───────────────────────────────────────────────────

def ingest_document(
    content: str,
    title: str,
    source: str = "direct_input",
    source_type: str = "text",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Ingest a document: chunk, embed, store in PostgreSQL."""
    if not content.strip():
        return {"success": False, "error": "Empty content"}

    doc_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title FROM documents WHERE doc_hash = %s AND (user_id = %s OR user_id IS NULL)",
                (doc_hash, user_id),
            )
            existing = cur.fetchone()
            if existing:
                return {
                    "success": False,
                    "error": f"Document already exists: '{existing['title']}' (id={existing['id']})",
                }

            chunks = chunk_text(content)

            cur.execute(
                """INSERT INTO documents (title, source, source_type, content, doc_hash, chunk_count, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (title, source, source_type, content[:10000], doc_hash, len(chunks), user_id),
            )
            doc_id = cur.fetchone()["id"]

            embedded_count = 0
            for i, chunk in enumerate(chunks):
                embedding = _get_embedding(chunk)
                emb_str = str(embedding) if embedding else None
                if embedding:
                    embedded_count += 1
                cur.execute(
                    """INSERT INTO chunks (doc_id, chunk_index, content, embedding)
                       VALUES (%s, %s, %s, %s::vector)""",
                    (doc_id, i, chunk, emb_str),
                )

        conn.commit()
        logger.info(f"RAG: Ingested '{title}' — {len(chunks)} chunks, {embedded_count} embedded")
        return {
            "success": True,
            "doc_id": doc_id,
            "title": title,
            "chunks": len(chunks),
            "embedded": embedded_count,
            "source_type": source_type,
        }
    finally:
        release_conn(conn)


def ingest_file(filepath: str, title: str | None = None, user_id: str | None = None) -> dict[str, Any]:
    """Ingest a file from disk."""
    path = Path(filepath)
    if not path.exists():
        return {"success": False, "error": f"File not found: {filepath}"}

    content, source_type = extract_text_from_file(filepath)
    if not content:
        return {"success": False, "error": f"Could not extract text from {filepath}"}

    return ingest_document(
        content=content,
        title=title or path.name,
        source=str(path),
        source_type=source_type,
        user_id=user_id,
    )


def query_documents(
    query: str,
    max_results: int = 5,
    min_similarity: float = 0.3,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """Semantic search across all ingested documents via pgvector."""
    embedding = _get_embedding(query)
    if not embedding:
        return _keyword_search(query, max_results, user_id=user_id)

    emb_str = str(embedding)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            user_filter = "AND (d.user_id = %s OR d.user_id IS NULL)" if user_id else ""
            params: list[Any] = [emb_str, emb_str, min_similarity, emb_str]
            if user_id:
                params.append(user_id)
            params.append(max_results)

            cur.execute(
                f"""SELECT c.id, c.doc_id, c.chunk_index, c.content,
                          1 - (c.embedding <=> %s::vector) AS similarity,
                          d.title, d.source
                   FROM chunks c
                   JOIN documents d ON c.doc_id = d.id
                   WHERE c.embedding IS NOT NULL
                     AND 1 - (c.embedding <=> %s::vector) >= %s
                     {user_filter}
                   ORDER BY c.embedding <=> %s::vector
                   LIMIT %s""",
                params,
            )
            rows = cur.fetchall()

        if not rows:
            return _keyword_search(query, max_results, user_id=user_id)

        return [
            {
                "chunk_id": r["id"],
                "doc_id": r["doc_id"],
                "doc_title": r["title"],
                "source": r["source"],
                "chunk_index": r["chunk_index"],
                "content": r["content"],
                "similarity": round(float(r["similarity"]), 3),
            }
            for r in rows
        ]
    finally:
        release_conn(conn)


def _keyword_search(query: str, max_results: int = 5, user_id: str | None = None) -> list[dict[str, Any]]:
    """Fallback keyword search."""
    words = [w for w in query.lower().split() if len(w) > 2]
    if not words:
        return []

    like_parts = [f"LOWER(c.content) LIKE %s" for _ in words[:8]]
    params: list[Any] = [f"%{w}%" for w in words[:8]]

    user_filter = "AND (d.user_id = %s OR d.user_id IS NULL)" if user_id else ""
    if user_id:
        params.append(user_id)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT c.id, c.doc_id, c.chunk_index, c.content, d.title, d.source
                    FROM chunks c
                    JOIN documents d ON c.doc_id = d.id
                    WHERE {' OR '.join(like_parts)}
                    {user_filter}
                    ORDER BY c.created_at DESC
                    LIMIT %s""",
                params + [max_results],
            )
            rows = cur.fetchall()

        return [
            {
                "chunk_id": r["id"],
                "doc_id": r["doc_id"],
                "doc_title": r["title"],
                "source": r["source"],
                "chunk_index": r["chunk_index"],
                "content": r["content"],
                "similarity": None,
            }
            for r in rows
        ]
    finally:
        release_conn(conn)


def list_documents(limit: int = 20, user_id: str | None = None) -> list[dict[str, Any]]:
    """List all ingested documents."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    """SELECT id, title, source, source_type, chunk_count, created_at
                       FROM documents
                       WHERE (user_id = %s OR user_id IS NULL)
                       ORDER BY created_at DESC LIMIT %s""",
                    (user_id, limit),
                )
            else:
                cur.execute(
                    """SELECT id, title, source, source_type, chunk_count, created_at
                       FROM documents ORDER BY created_at DESC LIMIT %s""",
                    (limit,),
                )
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def delete_document(doc_id: int, user_id: str | None = None) -> bool:
    """Delete a document and its chunks (CASCADE handles chunks)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    "DELETE FROM documents WHERE id = %s AND (user_id = %s OR user_id IS NULL)",
                    (doc_id, user_id),
                )
            else:
                cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        release_conn(conn)


def format_rag_results(results: list[dict]) -> str:
    """Format RAG results for LLM context injection."""
    if not results:
        return "No relevant documents found."

    parts = [f"Found {len(results)} relevant document chunks:\n"]
    for i, r in enumerate(results, 1):
        sim = f" (similarity: {r['similarity']})" if r.get("similarity") is not None else ""
        parts.append(
            f"{i}. [{r['doc_title']}] (chunk {r['chunk_index']}){sim}\n"
            f"   {r['content'][:400]}\n"
        )
    return "\n".join(parts)
