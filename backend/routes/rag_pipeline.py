"""
RAG Pipeline endpoints — bridge between document upload and RAG ingestion.
Provides ingest (direct, file, URL), query, list, delete, and stats.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from routes.documents import _FILE_REGISTRY, _extract_text
from tools.rag import ingest_document, query_documents, list_documents, delete_document
from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


def _row_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {}


# ── Pydantic Models ──────────────────────────────────────────────


class IngestRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500_000)
    title: str = Field(..., min_length=1, max_length=500)
    source: str = Field(default="direct")
    source_type: str = Field(default="text")


class IngestURLRequest(BaseModel):
    url: HttpUrl
    title: str | None = None
    max_chars: int = Field(default=50_000, ge=1000, le=500_000)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    max_results: int = Field(default=5, ge=1, le=50)


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/ingest")
async def ingest_direct(body: IngestRequest, user: dict = Depends(get_current_user)):
    """Ingest text content directly into RAG knowledge base."""
    result = await ingest_document(
        content=body.content,
        title=body.title,
        source=body.source,
        source_type=body.source_type,
        user_id=user["user_id"],
    )
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Ingest failed"))

    _audit("rag_ingest_direct", user["user_id"], detail=f"title={body.title}")
    return result


@router.post("/ingest-file/{file_id}")
async def ingest_file_bridge(file_id: str, user: dict = Depends(get_current_user)):
    """Ingest an already-uploaded file into RAG. Bridges upload → ingest."""
    meta = _FILE_REGISTRY.get(file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="File not found in upload registry")

    saved_path = Path(meta["saved_path"])
    if not saved_path.exists():
        raise HTTPException(status_code=404, detail="File missing from disk")

    ext = meta.get("extension", "")
    extracted = _extract_text(saved_path, ext)
    if extracted.startswith("[") and ("failed" in extracted.lower() or "unsupported" in extracted.lower()):
        raise HTTPException(status_code=422, detail=f"Cannot extract text: {extracted}")

    result = await ingest_document(
        content=extracted,
        title=meta.get("filename", file_id),
        source=f"upload:{file_id}",
        source_type=ext.lstrip(".") or "text",
        user_id=user["user_id"],
    )
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Ingest failed"))

    _audit("rag_ingest_file", user["user_id"], detail=f"file_id={file_id}, name={meta.get('filename')}")
    return result


@router.post("/ingest-url")
async def ingest_url(body: IngestURLRequest, user: dict = Depends(get_current_user)):
    """Fetch URL content and ingest into RAG knowledge base."""
    from tools.web_fetch import web_fetch

    fetched = await web_fetch(str(body.url), max_chars=body.max_chars)
    if fetched.get("status", 0) == 0 or not fetched.get("content"):
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {fetched.get('content', 'Unknown error')}")

    title = body.title or fetched.get("title") or str(body.url)
    content = fetched["content"]

    result = await ingest_document(
        content=content,
        title=title,
        source=str(body.url),
        source_type="url",
        user_id=user["user_id"],
    )
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Ingest failed"))

    _audit("rag_ingest_url", user["user_id"], detail=f"url={body.url}")
    return result


@router.post("/query")
async def rag_query(body: QueryRequest, user: dict = Depends(get_current_user)):
    """Semantic search over ingested RAG documents."""
    results = await query_documents(
        query=body.query,
        max_results=body.max_results,
        user_id=user["user_id"],
    )
    return {"query": body.query, "results": results, "count": len(results)}


@router.get("/documents")
async def rag_list_documents(
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    """List all ingested RAG documents."""
    docs = list_documents(limit=limit, user_id=user["user_id"])
    return {"documents": docs, "count": len(docs)}


@router.delete("/documents/{doc_id}")
async def rag_delete_document(doc_id: int, user: dict = Depends(get_current_user)):
    """Delete a document and its chunks from RAG."""
    deleted = delete_document(doc_id, user_id=user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found or already deleted")

    _audit("rag_delete", user["user_id"], detail=f"doc_id={doc_id}")
    return {"deleted": True, "doc_id": doc_id}


@router.get("/stats")
async def rag_stats(user: dict = Depends(get_current_user)):
    """RAG pipeline statistics: total docs, chunks, embeddings, last ingest."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            uid = user["user_id"]

            cur.execute(
                "SELECT COUNT(*) AS cnt FROM documents WHERE (user_id = %s OR user_id IS NULL)", (uid,)
            )
            total_docs = int(_row_dict(cur.fetchone()).get("cnt", 0) or 0)

            cur.execute(
                """SELECT COUNT(*) AS cnt FROM chunks c
                   JOIN documents d ON c.doc_id = d.id
                   WHERE (d.user_id = %s OR d.user_id IS NULL)""", (uid,)
            )
            total_chunks = int(_row_dict(cur.fetchone()).get("cnt", 0) or 0)

            cur.execute(
                """SELECT COUNT(*) AS cnt FROM chunks c
                   JOIN documents d ON c.doc_id = d.id
                   WHERE c.embedding IS NOT NULL
                     AND (d.user_id = %s OR d.user_id IS NULL)""", (uid,)
            )
            total_embedded = int(_row_dict(cur.fetchone()).get("cnt", 0) or 0)

            cur.execute(
                """SELECT MAX(d.created_at) AS last_at FROM documents d
                   WHERE (d.user_id = %s OR d.user_id IS NULL)""", (uid,)
            )
            row_data = _row_dict(cur.fetchone())
            last_at = row_data.get("last_at")
            last_ingest = str(last_at) if last_at else None

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_with_embeddings": total_embedded,
            "last_ingest_at": last_ingest,
        }
    finally:
        release_conn(conn)
