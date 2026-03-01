"""
PostgreSQL connection pool — psycopg2 ThreadedConnectionPool.
Single module for all DB access across memory, rag, teachability, skills.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras
import psycopg2.pool

from config import DATABASE_URL

logger = logging.getLogger(__name__)

_pool: psycopg2.pool.ThreadedConnectionPool | None = None

# ── Pool Management ──────────────────────────────────────────────

def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        logger.info("PostgreSQL connection pool initialized")
    return _pool


def get_conn() -> psycopg2.extensions.connection:
    """Get a connection from the pool."""
    try:
        return _get_pool().getconn()
    except psycopg2.pool.PoolError as e:
        logger.error(f"Connection pool exhausted: {e}")
        raise
    except psycopg2.OperationalError as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        raise


def release_conn(conn: psycopg2.extensions.connection) -> None:
    """Return a connection to the pool."""
    try:
        _get_pool().putconn(conn)
    except Exception as e:
        logger.warning(f"Failed to release connection: {e}")


@contextmanager
def db_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context manager for safe connection handling."""
    conn = get_conn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        release_conn(conn)


# ── Schema ───────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memories (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content      TEXT NOT NULL,
    category     TEXT NOT NULL DEFAULT 'general',
    memory_layer TEXT NOT NULL DEFAULT 'episodic',
    tags         TEXT NOT NULL DEFAULT '[]',
    source_agent TEXT,
    embedding    vector(1024),
    access_count INTEGER NOT NULL DEFAULT 0,
    ttl_hours    INTEGER,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_memories_category  ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_layer     ON memories(memory_layer);
CREATE INDEX IF NOT EXISTS idx_memories_created   ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS teachings (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category     TEXT NOT NULL DEFAULT 'preference',
    trigger_text TEXT NOT NULL,
    instruction  TEXT NOT NULL,
    context      TEXT,
    use_count    INTEGER NOT NULL DEFAULT 0,
    active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_teach_cat    ON teachings(category);
CREATE INDEX IF NOT EXISTS idx_teach_active ON teachings(active);

CREATE TABLE IF NOT EXISTS documents (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       TEXT NOT NULL,
    source      TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'text',
    content     TEXT NOT NULL,
    doc_hash    TEXT NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    user_id     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_docs_hash_user ON documents(doc_hash, COALESCE(user_id, ''));
CREATE INDEX IF NOT EXISTS idx_docs_hash ON documents(doc_hash);
CREATE INDEX IF NOT EXISTS idx_docs_user ON documents(user_id);

CREATE TABLE IF NOT EXISTS chunks (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doc_id      BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(1024),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc       ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS skills (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    description TEXT NOT NULL,
    keywords    TEXT NOT NULL DEFAULT '[]',
    knowledge   TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'builtin',
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    use_count   INTEGER NOT NULL DEFAULT 0,
    avg_score   REAL NOT NULL DEFAULT 0.0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_skills_cat    ON skills(category);
CREATE INDEX IF NOT EXISTS idx_skills_active ON skills(active);
"""


def init_database() -> None:
    """Create all tables and extensions. Safe to call multiple times."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
            # Migration: add user_id to documents if missing
            cur.execute("""
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id TEXT
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_docs_user ON documents(user_id)
            """)
        conn.commit()
    logger.info("Database schema initialized")


# ── SQLite Migration ─────────────────────────────────────────────

def migrate_from_sqlite() -> dict[str, int]:
    """
    Read existing SQLite databases and copy data to PostgreSQL.
    Idempotent — skips rows that already exist where possible.
    """
    import json
    import sqlite3
    from pathlib import Path

    data_dir = Path(__file__).parent.parent / "data"
    counts: dict[str, int] = {"memories": 0, "teachings": 0, "documents": 0, "chunks": 0, "skills": 0}

    # ── memories ────────────────────────────────────────────────
    mem_db = data_dir / "memory.db"
    if mem_db.exists():
        src = sqlite3.connect(str(mem_db))
        src.row_factory = sqlite3.Row
        rows = src.execute("SELECT * FROM memories").fetchall()
        with db_conn() as conn:
            with conn.cursor() as cur:
                for r in rows:
                    try:
                        emb = json.loads(r["embedding"]) if r["embedding"] else None
                        emb_str = str(emb) if emb else None
                        cur.execute(
                            """INSERT INTO memories
                               (content, category, memory_layer, tags, source_agent, embedding,
                                access_count, created_at, updated_at)
                               VALUES (%s, %s, 'episodic', %s, %s, %s::vector, %s, %s, %s)
                               ON CONFLICT DO NOTHING""",
                            (
                                r["content"], r["category"],
                                r["tags"] or "[]", r["source_agent"],
                                emb_str, r["access_count"],
                                r["created_at"], r["updated_at"],
                            ),
                        )
                        counts["memories"] += 1
                    except Exception as e:
                        logger.warning(f"Memory migration row skipped: {e}")
            conn.commit()
        src.close()
        logger.info(f"Migrated {counts['memories']} memories from SQLite")

    # ── teachings ────────────────────────────────────────────────
    teach_db = data_dir / "teachings.db"
    if teach_db.exists():
        src = sqlite3.connect(str(teach_db))
        src.row_factory = sqlite3.Row
        rows = src.execute("SELECT * FROM teachings").fetchall()
        with db_conn() as conn:
            with conn.cursor() as cur:
                for r in rows:
                    try:
                        cur.execute(
                            """INSERT INTO teachings
                               (category, trigger_text, instruction, context,
                                use_count, active, created_at, updated_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                               ON CONFLICT DO NOTHING""",
                            (
                                r["category"], r["trigger_text"], r["instruction"],
                                r["context"], r["use_count"], bool(r["active"]),
                                r["created_at"], r["updated_at"],
                            ),
                        )
                        counts["teachings"] += 1
                    except Exception as e:
                        logger.warning(f"Teaching migration row skipped: {e}")
            conn.commit()
        src.close()
        logger.info(f"Migrated {counts['teachings']} teachings from SQLite")

    # ── documents + chunks ───────────────────────────────────────
    rag_db = data_dir / "rag.db"
    if rag_db.exists():
        src = sqlite3.connect(str(rag_db))
        src.row_factory = sqlite3.Row
        docs = src.execute("SELECT * FROM documents").fetchall()
        with db_conn() as conn:
            with conn.cursor() as cur:
                for doc in docs:
                    try:
                        cur.execute(
                            """INSERT INTO documents
                               (title, source, source_type, content, doc_hash, chunk_count, created_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s)
                               ON CONFLICT (doc_hash) DO NOTHING
                               RETURNING id""",
                            (
                                doc["title"], doc["source"], doc["source_type"],
                                doc["content"], doc["doc_hash"], doc["chunk_count"],
                                doc["created_at"],
                            ),
                        )
                        result = cur.fetchone()
                        if not result:
                            continue
                        new_doc_id = result["id"]
                        counts["documents"] += 1

                        chunk_rows = src.execute(
                            "SELECT * FROM chunks WHERE doc_id = ?", (doc["id"],)
                        ).fetchall()
                        for ch in chunk_rows:
                            emb = json.loads(ch["embedding"]) if ch["embedding"] else None
                            emb_str = str(emb) if emb else None
                            cur.execute(
                                """INSERT INTO chunks
                                   (doc_id, chunk_index, content, embedding, created_at)
                                   VALUES (%s, %s, %s, %s::vector, %s)""",
                                (new_doc_id, ch["chunk_index"], ch["content"],
                                 emb_str, ch["created_at"]),
                            )
                            counts["chunks"] += 1
                    except Exception as e:
                        logger.warning(f"Document migration row skipped: {e}")
            conn.commit()
        src.close()
        logger.info(f"Migrated {counts['documents']} docs, {counts['chunks']} chunks from SQLite")

    # ── skills ───────────────────────────────────────────────────
    skills_db = data_dir / "dynamic_skills.db"
    if skills_db.exists():
        src = sqlite3.connect(str(skills_db))
        src.row_factory = sqlite3.Row
        rows = src.execute("SELECT * FROM skills").fetchall()
        with db_conn() as conn:
            with conn.cursor() as cur:
                for r in rows:
                    try:
                        cur.execute(
                            """INSERT INTO skills
                               (id, name, category, description, keywords, knowledge,
                                source, active, use_count, avg_score, created_at, updated_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                               ON CONFLICT (id) DO NOTHING""",
                            (
                                r["id"], r["name"], r["category"], r["description"],
                                r["keywords"] or "[]", r["knowledge"], r["source"],
                                bool(r["active"]), r["use_count"], r["avg_score"],
                                r["created_at"], r["updated_at"],
                            ),
                        )
                        counts["skills"] += 1
                    except Exception as e:
                        logger.warning(f"Skill migration row skipped: {e}")
            conn.commit()
        src.close()
        logger.info(f"Migrated {counts['skills']} skills from SQLite")

    return counts
