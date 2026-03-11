"""
Prompt Strategy Manager — Faz 16: Self-Improvement Loop.
CRUD + version tracking for prompt strategies.
Strategies stored in PostgreSQL with auto-versioning per agent_role+task_type.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("prompt_strategies")


def _db_row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row or {})


class PromptStrategyManager:
    """CRUD + version tracking for prompt strategies."""

    def __init__(self):
        self._initialized = False

    def _get_conn(self):
        from tools.pg_connection import get_conn
        return get_conn()

    def _release(self, conn):
        from tools.pg_connection import release_conn
        release_conn(conn)


    def _ensure_table(self):
        if self._initialized:
            return
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS prompt_strategies (
                        id SERIAL PRIMARY KEY,
                        agent_role VARCHAR(32) NOT NULL,
                        task_type VARCHAR(64) NOT NULL,
                        name VARCHAR(128) NOT NULL,
                        version INTEGER DEFAULT 1,
                        system_prompt TEXT NOT NULL,
                        few_shot_examples JSONB DEFAULT '[]',
                        cot_instructions TEXT DEFAULT '',
                        metadata JSONB DEFAULT '{}',
                        is_active BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_ps_role_task ON prompt_strategies(agent_role, task_type)")
            conn.commit()
            self._release(conn)
            self._initialized = True
        except Exception as e:
            logger.warning(f"prompt_strategies table init failed: {e}")

    def create(
        self,
        agent_role: str,
        task_type: str,
        name: str,
        system_prompt: str,
        few_shot_examples: list | None = None,
        cot_instructions: str = "",
        metadata: dict | None = None,
    ) -> dict:
        """Create new strategy with auto-incremented version."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                # Get next version number
                cur.execute(
                    "SELECT COALESCE(MAX(version), 0) + 1 as next_ver FROM prompt_strategies WHERE agent_role = %s AND task_type = %s",
                    (agent_role, task_type),
                )
                next_ver_row = _db_row_to_dict(cur.fetchone())
                next_ver = int(next_ver_row.get("next_ver", 1) or 1)

                cur.execute(
                    """INSERT INTO prompt_strategies
                       (agent_role, task_type, name, version, system_prompt, few_shot_examples, cot_instructions, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING id, created_at""",
                    (
                        agent_role, task_type, name, next_ver,
                        system_prompt,
                        json.dumps(few_shot_examples or []),
                        cot_instructions,
                        json.dumps(metadata or {}),
                    ),
                )
                row = cur.fetchone()
                row_dict = _db_row_to_dict(row)
                created_at = row_dict.get("created_at")
                created_at_iso = None
                isoformat_fn = getattr(created_at, "isoformat", None)
                if callable(isoformat_fn):
                    created_at_iso = isoformat_fn()
            conn.commit()
            logger.info(f"Prompt strategy created: {name} v{next_ver} for {agent_role}/{task_type}")
            return {
                "id": row_dict.get("id"),
                "agent_role": agent_role,
                "task_type": task_type,
                "name": name,
                "version": next_ver,
                "is_active": False,
                "created_at": created_at_iso,
            }
        finally:
            self._release(conn)

    def list_strategies(
        self,
        agent_role: str | None = None,
        task_type: str | None = None,
    ) -> list[dict]:
        """List strategies with optional filters."""
        self._ensure_table()
        conditions = ["1=1"]
        params: list = []
        if agent_role:
            conditions.append("agent_role = %s")
            params.append(agent_role)
        if task_type:
            conditions.append("task_type = %s")
            params.append(task_type)

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT * FROM prompt_strategies WHERE {' AND '.join(conditions)} ORDER BY created_at DESC",
                    params,
                )
                rows = cur.fetchall()
            return [self._row_to_dict(_db_row_to_dict(r)) for r in rows]
        finally:
            self._release(conn)

    def activate(self, strategy_id: int) -> dict:
        """Set as active. Fails with error if active A/B experiment exists for same role+task."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                # Get strategy details
                cur.execute("SELECT * FROM prompt_strategies WHERE id = %s", (strategy_id,))
                strategy_row = cur.fetchone()
                if not strategy_row:
                    raise ValueError(f"Strategy {strategy_id} not found")
                strategy = _db_row_to_dict(strategy_row)

                role = str(strategy.get("agent_role") or "")
                task = str(strategy.get("task_type") or "")

                # Check for active A/B experiment conflict
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM ab_experiments WHERE agent_role = %s AND task_type = %s AND status = 'active'",
                    (role, task),
                )
                conflict = _db_row_to_dict(cur.fetchone())
                if int(conflict.get("cnt", 0) or 0) > 0:
                    raise ValueError(f"Active A/B experiment exists for {role}/{task}. Conclude it first.")

                # Deactivate all strategies for this role+task
                cur.execute(
                    "UPDATE prompt_strategies SET is_active = FALSE WHERE agent_role = %s AND task_type = %s",
                    (role, task),
                )
                # Activate the selected one
                cur.execute(
                    "UPDATE prompt_strategies SET is_active = TRUE WHERE id = %s",
                    (strategy_id,),
                )
            conn.commit()
            logger.info(f"Activated strategy {strategy_id} for {role}/{task}")
            return self._row_to_dict(strategy | {"is_active": True})
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"activate failed: {e}")
            raise
        finally:
            self._release(conn)

    def get_active(self, agent_role: str, task_type: str) -> dict | None:
        """Get currently active strategy for role+task."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM prompt_strategies WHERE agent_role = %s AND task_type = %s AND is_active = TRUE LIMIT 1",
                    (agent_role, task_type),
                )
                row = cur.fetchone()
            return self._row_to_dict(_db_row_to_dict(row)) if row else None
        finally:
            self._release(conn)

    def get_by_id(self, strategy_id: int) -> dict | None:
        """Get strategy by ID."""
        self._ensure_table()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM prompt_strategies WHERE id = %s", (strategy_id,))
                row = cur.fetchone()
            return self._row_to_dict(_db_row_to_dict(row)) if row else None
        finally:
            self._release(conn)

    @staticmethod
    def _row_to_dict(row: dict) -> dict:
        result = dict(row)
        for key in ("few_shot_examples", "metadata"):
            if key in result and isinstance(result[key], str):
                try:
                    result[key] = json.loads(result[key])
                except Exception:
                    pass
        if "created_at" in result and hasattr(result["created_at"], "isoformat"):
            result["created_at"] = result["created_at"].isoformat()
        return result


# ── Singleton ────────────────────────────────────────────────────

_instance: PromptStrategyManager | None = None


def get_prompt_strategy_manager() -> PromptStrategyManager:
    global _instance
    if _instance is None:
        _instance = PromptStrategyManager()
    return _instance
