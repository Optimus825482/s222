"""
Shared Workspace — PostgreSQL backend
Faz 10.6 — Çoklu kullanıcı için ortak çalışma alanı (Qdrant → PG migration)
"""

import hashlib
import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from tools.pg_connection import DBRow

logger = logging.getLogger(__name__)


def _conn():
    from tools.pg_connection import get_conn
    return get_conn()


def _release(conn):
    from tools.pg_connection import release_conn
    release_conn(conn)


def _as_row(row: object) -> DBRow | None:
    if isinstance(row, Mapping):
        return row
    return None


def _ensure_tables():
    """Create tables if they don't exist (idempotent)."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shared_workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    owner_id     TEXT NOT NULL,
                    name         TEXT NOT NULL,
                    members      TEXT[] NOT NULL DEFAULT '{}',
                    metadata     JSONB NOT NULL DEFAULT '{}',
                    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shared_workspace_items (
                    item_id      TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES shared_workspaces(workspace_id) ON DELETE CASCADE,
                    item_type    TEXT NOT NULL,
                    content      TEXT NOT NULL,
                    author_id    TEXT NOT NULL,
                    metadata     JSONB NOT NULL DEFAULT '{}',
                    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _release(conn)


_tables_ok = False


class SharedWorkspace:
    """Çoklu kullanıcı ve agent için ortak çalışma alanı — PostgreSQL backend"""

    def __init__(self):
        global _tables_ok
        if not _tables_ok:
            _ensure_tables()
            _tables_ok = True

    @staticmethod
    def _gen_id(workspace_id: str, item_type: str, content: str) -> str:
        data = f"{workspace_id}:{item_type}:{content}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    # ── Workspace CRUD ───────────────────────────────────────────

    def create_workspace(
        self,
        workspace_id: str,
        owner_id: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO shared_workspaces (workspace_id, owner_id, name, members, metadata)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (workspace_id) DO NOTHING
                       RETURNING workspace_id, owner_id, name, members, metadata, created_at""",
                    (workspace_id, owner_id, name, [owner_id], json.dumps(metadata or {})),
                )
                fetched = cur.fetchone()
                row = _as_row(fetched)
                conn.commit()
                if row:
                    return {
                        "workspace_id": row["workspace_id"],
                        "owner_id": row["owner_id"],
                        "name": row["name"],
                        "members": list(row["members"]),
                        "metadata": row["metadata"],
                        "created_at": str(row["created_at"]),
                    }
                return {"workspace_id": workspace_id, "status": "already_exists"}
        except Exception:
            conn.rollback()
            raise
        finally:
            _release(conn)

    def get_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT workspace_id, owner_id, name, members, metadata, created_at FROM shared_workspaces WHERE workspace_id = %s",
                    (workspace_id,),
                )
                fetched = cur.fetchone()
                row = _as_row(fetched)
                if not row:
                    return None
                return {
                    "workspace_id": row["workspace_id"],
                    "owner_id": row["owner_id"],
                    "name": row["name"],
                    "members": list(row["members"]),
                    "metadata": row["metadata"],
                    "created_at": str(row["created_at"]),
                }
        finally:
            _release(conn)

    def list_workspaces(self, user_id: str) -> list[dict[str, Any]]:
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT workspace_id, owner_id, name, members, metadata, created_at FROM shared_workspaces WHERE %s = ANY(members) ORDER BY created_at DESC",
                    (user_id,),
                )
                return [
                    {
                        "workspace_id": r["workspace_id"],
                        "owner_id": r["owner_id"],
                        "name": r["name"],
                        "members": list(r["members"]),
                        "metadata": r["metadata"],
                        "created_at": str(r["created_at"]),
                    }
                    for fetched in cur.fetchall()
                    if (r := _as_row(fetched)) is not None
                ]
        finally:
            _release(conn)

    def add_member(self, workspace_id: str, user_id: str, role: str = "member") -> bool:
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE shared_workspaces
                       SET members = array_append(members, %s)
                       WHERE workspace_id = %s AND NOT (%s = ANY(members))""",
                    (user_id, workspace_id, user_id),
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            _release(conn)

    def remove_member(self, workspace_id: str, user_id: str) -> bool:
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE shared_workspaces SET members = array_remove(members, %s) WHERE workspace_id = %s",
                    (user_id, workspace_id),
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            _release(conn)

    # ── Item CRUD ────────────────────────────────────────────────

    def add_item(
        self,
        workspace_id: str,
        item_type: str,
        content: str,
        vector=None,
        author_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        item_id = self._gen_id(workspace_id, item_type, content)
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO shared_workspace_items (item_id, workspace_id, item_type, content, author_id, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (item_id, workspace_id, item_type, content, author_id, json.dumps(metadata or {})),
                )
                conn.commit()
            return item_id
        except Exception:
            conn.rollback()
            raise
        finally:
            _release(conn)

    def get_items(
        self,
        workspace_id: str,
        item_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conn = _conn()
        try:
            with conn.cursor() as cur:
                if item_type:
                    cur.execute(
                        """SELECT item_id, workspace_id, item_type, content, author_id, metadata, created_at
                           FROM shared_workspace_items
                           WHERE workspace_id = %s AND item_type = %s
                           ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                        (workspace_id, item_type, limit, offset),
                    )
                else:
                    cur.execute(
                        """SELECT item_id, workspace_id, item_type, content, author_id, metadata, created_at
                           FROM shared_workspace_items
                           WHERE workspace_id = %s
                           ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                        (workspace_id, limit, offset),
                    )
                return [
                    {
                        "item_id": r["item_id"],
                        "workspace_id": r["workspace_id"],
                        "item_type": r["item_type"],
                        "content": r["content"],
                        "author_id": r["author_id"],
                        "metadata": r["metadata"],
                        "created_at": str(r["created_at"]),
                    }
                    for fetched in cur.fetchall()
                    if (r := _as_row(fetched)) is not None
                ]
        finally:
            _release(conn)

    def delete_item(self, item_id: str) -> bool:
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM shared_workspace_items WHERE item_id = %s", (item_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            _release(conn)

    def get_workspace_stats(self, workspace_id: str) -> dict[str, Any]:
        conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT
                         COUNT(*) AS total,
                         MAX(created_at) AS last_activity
                       FROM shared_workspace_items WHERE workspace_id = %s""",
                    (workspace_id,),
                )
                summary = _as_row(cur.fetchone())
                cur.execute(
                    """SELECT item_type, COUNT(*) AS cnt
                       FROM shared_workspace_items WHERE workspace_id = %s
                       GROUP BY item_type""",
                    (workspace_id,),
                )
                item_types = {
                    r["item_type"]: r["cnt"]
                    for fetched in cur.fetchall()
                    if (r := _as_row(fetched)) is not None
                }
                cur.execute(
                    """SELECT author_id, COUNT(*) AS cnt
                       FROM shared_workspace_items WHERE workspace_id = %s
                       GROUP BY author_id""",
                    (workspace_id,),
                )
                contributors = {
                    r["author_id"]: r["cnt"]
                    for fetched in cur.fetchall()
                    if (r := _as_row(fetched)) is not None
                }
                return {
                    "workspace_id": workspace_id,
                    "total_items": summary["total"] if summary else 0,
                    "item_types": item_types,
                    "contributors": contributors,
                    "last_activity": str(summary["last_activity"]) if summary and summary["last_activity"] else None,
                }
        finally:
            _release(conn)

    def sync_to_cli(self, workspace_id: str, cli_memory_path: str) -> bool:
        items = self.get_items(workspace_id, limit=1000)
        try:
            with open(cli_memory_path, "w") as f:
                json.dump({"workspace_id": workspace_id, "synced_at": datetime.now(timezone.utc).isoformat(), "items": items}, f, indent=2)
            return True
        except Exception:
            return False

    def sync_from_cli(self, workspace_id: str, cli_memory_path: str, author_id: str) -> int:
        try:
            with open(cli_memory_path, "r") as f:
                data = json.load(f)
            count = 0
            for item in data.get("items", []):
                self.add_item(workspace_id, item.get("item_type", "note"), item.get("content", ""), author_id=author_id, metadata=item.get("metadata", {}))
                count += 1
            return count
        except Exception:
            return 0


# ── Global singleton ─────────────────────────────────────────────

_workspace: SharedWorkspace | None = None


def get_workspace() -> SharedWorkspace:
    global _workspace
    if _workspace is None:
        _workspace = SharedWorkspace()
    return _workspace
