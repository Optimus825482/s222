"""
Scheduled Tasks — Generic cron-based task scheduling with PostgreSQL persistence.

Extends Heartbeat system with flexible APScheduler integration.
Supports arbitrary Python callables, workflow triggers, and custom handlers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

_utc = timezone.utc


# ── Enums & Data Classes ─────────────────────────────────────────

class TaskType(str, Enum):
    """Types of scheduled tasks."""
    HEARTBEAT = "heartbeat"       # Built-in heartbeat handler
    WORKFLOW = "workflow"         # Trigger a workflow template
    CALLABLE = "callable"         # Python callable (registered in registry)
    HTTP = "http"                 # HTTP webhook/endpoint call
    SHELL = "shell"               # Shell command execution


class TaskStatus(str, Enum):
    """Task lifecycle status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """Definition of a scheduled task."""
    id: str
    name: str
    task_type: TaskType
    cron_expr: str
    handler_ref: str  # Handler name/identifier
    params: dict = field(default_factory=dict)
    enabled: bool = True
    user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_run: datetime | None = None
    last_status: TaskStatus = TaskStatus.PENDING
    last_result: dict | None = None
    run_count: int = 0
    error_count: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class TaskExecution:
    """Record of a single task execution."""
    id: str
    task_id: str
    status: TaskStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int = 0
    result: dict | None = None
    error: str | None = None
    retry_count: int = 0


# ── Handler Registry ─────────────────────────────────────────────

# Registry for callable handlers (name -> async function)
_handler_registry: dict[str, Callable[..., Awaitable[dict]]] = {}


def register_handler(name: str, handler: Callable[..., Awaitable[dict]]) -> None:
    """Register a callable handler for scheduled tasks."""
    _handler_registry[name] = handler
    logger.debug("[ScheduledTasks] Registered handler: %s", name)


def get_handler(name: str) -> Callable[..., Awaitable[dict]] | None:
    """Get a registered handler by name."""
    return _handler_registry.get(name)


def list_handlers() -> list[str]:
    """List all registered handler names."""
    return list(_handler_registry.keys())


# ── Execution History (in-memory cache + DB persistence) ─────────

_execution_history: list[TaskExecution] = []
_MAX_HISTORY = 500


def _add_execution(execution: TaskExecution) -> None:
    """Add execution to in-memory history."""
    global _execution_history
    _execution_history.append(execution)
    if len(_execution_history) > _MAX_HISTORY:
        _execution_history[:] = _execution_history[-_MAX_HISTORY:]


def get_execution_history(task_id: str | None = None, limit: int = 100) -> list[dict]:
    """Get execution history from memory."""
    if task_id:
        items = [e for e in _execution_history if e.task_id == task_id]
    else:
        items = _execution_history
    return [
        {
            "id": e.id,
            "task_id": e.task_id,
            "status": e.status.value,
            "started_at": e.started_at.isoformat(),
            "finished_at": e.finished_at.isoformat() if e.finished_at else None,
            "duration_ms": e.duration_ms,
            "result": e.result,
            "error": e.error,
            "retry_count": e.retry_count,
        }
        for e in reversed(items[-limit:])
    ]


# ── Scheduled Task Scheduler ─────────────────────────────────────

_scheduler: AsyncIOScheduler | None = None
_running_tasks: dict[str, asyncio.Task] = {}


class ScheduledTaskScheduler:
    """
    APScheduler-based scheduler for arbitrary tasks.
    Manages CRUD operations, persistence, and execution.
    """

    def __init__(self) -> None:
        self._started = False
        self._task_cache: dict[str, ScheduledTask] = {}

    async def start(self) -> None:
        """Initialize APScheduler and load tasks from DB."""
        global _scheduler

        if self._started:
            return

        # Initialize APScheduler
        _scheduler = AsyncIOScheduler(timezone="UTC")
        _scheduler.start()
        self._started = True
        logger.info("[ScheduledTasks] APScheduler started")

        # Load existing tasks from DB
        await self._load_tasks_from_db()

        # Ensure table exists
        self._ensure_tables()

    async def stop(self) -> None:
        """Stop the scheduler."""
        global _scheduler

        if _scheduler:
            _scheduler.shutdown(wait=False)
            _scheduler = None

        # Cancel running tasks
        for task_id, task in list(_running_tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        _running_tasks.clear()

        self._started = False
        logger.info("[ScheduledTasks] Scheduler stopped")

    def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id           TEXT PRIMARY KEY,
                    name         TEXT NOT NULL,
                    task_type    TEXT NOT NULL,
                    cron_expr    TEXT NOT NULL,
                    handler_ref  TEXT NOT NULL,
                    params       TEXT NOT NULL DEFAULT '{}',
                    enabled      BOOLEAN NOT NULL DEFAULT TRUE,
                    user_id      TEXT,
                    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_run     TIMESTAMPTZ,
                    last_status  TEXT NOT NULL DEFAULT 'pending',
                    last_result  TEXT,
                    run_count    INTEGER NOT NULL DEFAULT 0,
                    error_count  INTEGER NOT NULL DEFAULT 0,
                    tags         TEXT NOT NULL DEFAULT '[]'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    id           TEXT PRIMARY KEY,
                    task_id      TEXT NOT NULL REFERENCES scheduled_tasks(id) ON DELETE CASCADE,
                    status       TEXT NOT NULL,
                    started_at   TIMESTAMPTZ NOT NULL,
                    finished_at  TIMESTAMPTZ,
                    duration_ms  INTEGER DEFAULT 0,
                    result       TEXT,
                    error        TEXT,
                    retry_count  INTEGER DEFAULT 0
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_st_user ON scheduled_tasks(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_st_enabled ON scheduled_tasks(enabled)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_te_task ON task_executions(task_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_te_started ON task_executions(started_at DESC)")
            conn.commit()
        finally:
            release_conn(conn)

    async def _load_tasks_from_db(self) -> None:
        """Load enabled tasks from DB and schedule them."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM scheduled_tasks WHERE enabled = TRUE")
            rows = cur.fetchall()
            for row in rows:
                task = self._row_to_task(row)
                self._task_cache[task.id] = task
                self._schedule_task(task)
            logger.info("[ScheduledTasks] Loaded %d tasks from DB", len(rows))
        finally:
            release_conn(conn)

    def _row_to_task(self, row: dict) -> ScheduledTask:
        """Convert DB row to ScheduledTask."""
        return ScheduledTask(
            id=row["id"],
            name=row["name"],
            task_type=TaskType(row["task_type"]),
            cron_expr=row["cron_expr"],
            handler_ref=row["handler_ref"],
            params=json.loads(row["params"]) if row["params"] else {},
            enabled=bool(row["enabled"]),
            user_id=row["user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_run=row["last_run"],
            last_status=TaskStatus(row["last_status"]),
            last_result=json.loads(row["last_result"]) if row["last_result"] else None,
            run_count=row["run_count"] or 0,
            error_count=row["error_count"] or 0,
            tags=json.loads(row["tags"]) if row["tags"] else [],
        )

    def _task_to_dict(self, task: ScheduledTask) -> dict:
        """Convert ScheduledTask to dict for API."""
        next_run = None
        if _scheduler and task.enabled:
            try:
                job = _scheduler.get_job(task.id)
                if job and job.next_run_time:
                    next_run = job.next_run_time.isoformat()
            except Exception:
                pass

        return {
            "id": task.id,
            "name": task.name,
            "task_type": task.task_type.value,
            "cron_expr": task.cron_expr,
            "handler_ref": task.handler_ref,
            "params": task.params,
            "enabled": task.enabled,
            "user_id": task.user_id,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "last_status": task.last_status.value,
            "last_result": task.last_result,
            "run_count": task.run_count,
            "error_count": task.error_count,
            "tags": task.tags,
            "next_run": next_run,
        }

    def _validate_cron(self, cron_expr: str) -> None:
        """Validate a cron expression."""
        try:
            CronTrigger.from_crontab(cron_expr)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{cron_expr}': {e}")

    def _schedule_task(self, task: ScheduledTask) -> None:
        """Add task to APScheduler."""
        if not _scheduler or not task.enabled:
            return

        try:
            trigger = CronTrigger.from_crontab(task.cron_expr)
            _scheduler.add_job(
                _execute_scheduled_task,
                trigger=trigger,
                args=[task.id],
                id=task.id,
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes
            )
            logger.info("[ScheduledTasks] Scheduled task '%s' with cron '%s'", task.id, task.cron_expr)
        except Exception as e:
            logger.error("[ScheduledTasks] Failed to schedule task '%s': %s", task.id, e)

    def _unschedule_task(self, task_id: str) -> None:
        """Remove task from APScheduler."""
        if not _scheduler:
            return
        try:
            _scheduler.remove_job(task_id)
        except Exception:
            pass

    # ── CRUD Operations ───────────────────────────────────────────

    async def create_task(
        self,
        name: str,
        task_type: TaskType,
        cron_expr: str,
        handler_ref: str,
        params: dict | None = None,
        enabled: bool = True,
        user_id: str | None = None,
        tags: list[str] | None = None,
        task_id: str | None = None,
    ) -> ScheduledTask:
        """Create a new scheduled task."""
        self._validate_cron(cron_expr)

        # Validate handler based on type
        if task_type == TaskType.CALLABLE:
            if not get_handler(handler_ref):
                raise ValueError(f"Handler '{handler_ref}' not registered")

        tid = task_id or f"task-{uuid.uuid4().hex[:8]}"
        now = datetime.now(_utc)

        task = ScheduledTask(
            id=tid,
            name=name,
            task_type=task_type,
            cron_expr=cron_expr,
            handler_ref=handler_ref,
            params=params or {},
            enabled=enabled,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            tags=tags or [],
        )

        # Persist to DB
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO scheduled_tasks
                   (id, name, task_type, cron_expr, handler_ref, params, enabled, user_id, created_at, updated_at, tags)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    task.id, task.name, task.task_type.value, task.cron_expr,
                    task.handler_ref, json.dumps(task.params), task.enabled,
                    task.user_id, now, now, json.dumps(task.tags),
                ),
            )
            conn.commit()
        finally:
            release_conn(conn)

        self._task_cache[task.id] = task

        if task.enabled:
            self._schedule_task(task)

        logger.info("[ScheduledTasks] Created task '%s' (%s)", task.id, task.name)
        return task

    async def get_task(self, task_id: str) -> ScheduledTask | None:
        """Get a task by ID."""
        # Check cache first
        if task_id in self._task_cache:
            return self._task_cache[task_id]

        # Load from DB
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM scheduled_tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
            if row:
                task = self._row_to_task(row)
                self._task_cache[task.id] = task
                return task
            return None
        finally:
            release_conn(conn)

    async def list_tasks(
        self,
        user_id: str | None = None,
        enabled: bool | None = None,
        task_type: TaskType | None = None,
    ) -> list[ScheduledTask]:
        """List tasks with optional filters."""
        query = "SELECT * FROM scheduled_tasks WHERE 1=1"
        params: list[Any] = []

        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)
        if enabled is not None:
            query += " AND enabled = %s"
            params.append(enabled)
        if task_type:
            query += " AND task_type = %s"
            params.append(task_type.value)

        query += " ORDER BY created_at DESC"

        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_task(r) for r in rows]
        finally:
            release_conn(conn)

    async def update_task(
        self,
        task_id: str,
        name: str | None = None,
        cron_expr: str | None = None,
        params: dict | None = None,
        enabled: bool | None = None,
        tags: list[str] | None = None,
    ) -> ScheduledTask:
        """Update a task."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found")

        now = datetime.now(_utc)
        updates: list[str] = []
        values: list[Any] = []

        if name is not None:
            updates.append("name = %s")
            values.append(name)
            task.name = name

        if cron_expr is not None:
            self._validate_cron(cron_expr)
            updates.append("cron_expr = %s")
            values.append(cron_expr)
            task.cron_expr = cron_expr

        if params is not None:
            updates.append("params = %s")
            values.append(json.dumps(params))
            task.params = params

        if enabled is not None:
            updates.append("enabled = %s")
            values.append(enabled)
            task.enabled = enabled

        if tags is not None:
            updates.append("tags = %s")
            values.append(json.dumps(tags))
            task.tags = tags

        if not updates:
            return task

        updates.append("updated_at = %s")
        values.append(now)
        task.updated_at = now
        values.append(task_id)

        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE id = %s",
                values,
            )
            conn.commit()
        finally:
            release_conn(conn)

        # Reschedule if needed
        self._unschedule_task(task_id)
        if task.enabled:
            self._schedule_task(task)

        self._task_cache[task_id] = task
        logger.info("[ScheduledTasks] Updated task '%s'", task_id)
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        self._unschedule_task(task_id)
        self._task_cache.pop(task_id, None)

        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM scheduled_tasks WHERE id = %s", (task_id,))
            conn.commit()
            deleted = cur.rowcount > 0
        finally:
            release_conn(conn)

        if deleted:
            logger.info("[ScheduledTasks] Deleted task '%s'", task_id)
        return deleted

    async def toggle_task(self, task_id: str, enabled: bool | None = None) -> ScheduledTask:
        """Toggle task enabled status."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found")

        new_enabled = not task.enabled if enabled is None else enabled
        return await self.update_task(task_id, enabled=new_enabled)

    async def trigger_task(self, task_id: str) -> dict:
        """Manually trigger a task execution."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found")

        # Execute immediately
        result = await _execute_task_internal(task)
        return result

    # ── Query Methods ─────────────────────────────────────────────

    def get_task_dict(self, task_id: str) -> dict | None:
        """Get task as dict for API (cache-only, fast lookup)."""
        task = self._task_cache.get(task_id)
        if task:
            return self._task_to_dict(task)
        return None

    def list_tasks_dicts(
        self,
        user_id: str | None = None,
        enabled: bool | None = None,
        task_type: TaskType | None = None,
    ) -> list[dict]:
        """
        List tasks as dicts for API.
        For simple cache-only queries, returns from cache.
        For filtered queries, returns empty list (use async list_tasks instead).
        """
        # Cache-only mode: return all cached tasks
        if user_id is None and enabled is None and task_type is None:
            return [self._task_to_dict(t) for t in self._task_cache.values()]
        
        # For filtered queries, filter from cache
        # Note: For full DB query, use await list_tasks() directly
        tasks = list(self._task_cache.values())
        if user_id is not None:
            tasks = [t for t in tasks if t.user_id == user_id]
        if enabled is not None:
            tasks = [t for t in tasks if t.enabled == enabled]
        if task_type is not None:
            tasks = [t for t in tasks if t.task_type == task_type]
        return [self._task_to_dict(t) for t in tasks]

    async def list_tasks_dicts_async(
        self,
        user_id: str | None = None,
        enabled: bool | None = None,
        task_type: TaskType | None = None,
    ) -> list[dict]:
        """Async version of list_tasks_dicts with full DB query support."""
        tasks = await self.list_tasks(user_id, enabled, task_type)
        return [self._task_to_dict(t) for t in tasks]

    async def get_executions_from_db(
        self,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get execution history from DB."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            if task_id:
                cur.execute(
                    "SELECT * FROM task_executions WHERE task_id = %s ORDER BY started_at DESC LIMIT %s",
                    (task_id, limit),
                )
            else:
                cur.execute(
                    "SELECT * FROM task_executions ORDER BY started_at DESC LIMIT %s",
                    (limit,),
                )
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "task_id": r["task_id"],
                    "status": r["status"],
                    "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                    "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
                    "duration_ms": r["duration_ms"],
                    "result": json.loads(r["result"]) if r["result"] else None,
                    "error": r["error"],
                    "retry_count": r["retry_count"] or 0,
                }
                for r in rows
            ]
        finally:
            release_conn(conn)


# ── Task Execution ───────────────────────────────────────────────

async def _execute_scheduled_task(task_id: str) -> None:
    """Job callback for APScheduler."""
    scheduler = get_scheduled_task_scheduler()
    task = await scheduler.get_task(task_id)
    if not task:
        logger.warning("[ScheduledTasks] Task '%s' not found, skipping", task_id)
        return

    await _execute_task_internal(task)


async def _execute_task_internal(task: ScheduledTask) -> dict:
    """Execute a task and record the result."""
    execution_id = f"exec-{uuid.uuid4().hex[:8]}"
    started_at = datetime.now(_utc)
    status = TaskStatus.RUNNING
    result: dict | None = None
    error: str | None = None

    # Record execution start
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO task_executions (id, task_id, status, started_at)
               VALUES (%s, %s, %s, %s)""",
            (execution_id, task.id, status.value, started_at),
        )
        conn.commit()
    finally:
        release_conn(conn)

    try:
        # Execute based on task type
        if task.task_type == TaskType.HEARTBEAT:
            from tools.heartbeat import get_heartbeat_scheduler
            hb = get_heartbeat_scheduler()
            hb_task = hb.tasks.get(task.handler_ref)
            if hb_task and hb_task.handler:
                result = await hb_task.handler()
            else:
                raise ValueError(f"Heartbeat task '{task.handler_ref}' not found")

        elif task.task_type == TaskType.WORKFLOW:
            from tools.workflow_engine import get_template, execute_workflow
            from core.models import Thread as ThreadModel
            workflow = get_template(task.handler_ref, task.params)
            thread = ThreadModel()
            exec_result = await execute_workflow(workflow, thread)
            result = {
                "status": exec_result.status,
                "duration_ms": exec_result.duration_ms,
            }

        elif task.task_type == TaskType.CALLABLE:
            handler = get_handler(task.handler_ref)
            if not handler:
                raise ValueError(f"Handler '{task.handler_ref}' not registered")
            result = await handler(**task.params)

        elif task.task_type == TaskType.HTTP:
            import aiohttp
            url = task.params.get("url")
            method = task.params.get("method", "GET").upper()
            headers = task.params.get("headers", {})
            body = task.params.get("body")
            timeout = task.params.get("timeout", 30)

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, headers=headers, data=body, timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    result = {
                        "status_code": resp.status,
                        "headers": dict(resp.headers),
                        "body": await resp.text() if resp.content_type.startswith("text") else None,
                    }

        elif task.task_type == TaskType.SHELL:
            cmd = task.params.get("command")
            if not cmd:
                raise ValueError("Shell task requires 'command' parameter")

            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=task.params.get("timeout", 60),
            )
            result = {
                "return_code": proc.returncode,
                "stdout": stdout.decode() if stdout else None,
                "stderr": stderr.decode() if stderr else None,
            }

        else:
            raise ValueError(f"Unknown task type: {task.task_type}")

        status = TaskStatus.COMPLETED

    except asyncio.CancelledError:
        status = TaskStatus.CANCELLED
        error = "Task cancelled"
        raise

    except Exception as e:
        status = TaskStatus.FAILED
        error = str(e)
        logger.error("[ScheduledTasks] Task '%s' failed: %s", task.id, e, exc_info=True)

    finally:
        finished_at = datetime.now(_utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        # Update task stats
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE scheduled_tasks
                   SET last_run = %s, last_status = %s, last_result = %s,
                       run_count = run_count + 1, error_count = error_count + %s
                   WHERE id = %s""",
                (
                    finished_at, status.value,
                    json.dumps(result) if result else None,
                    1 if status == TaskStatus.FAILED else 0,
                    task.id,
                ),
            )

            # Update execution record
            cur.execute(
                """UPDATE task_executions
                   SET finished_at = %s, status = %s, duration_ms = %s, result = %s, error = %s
                   WHERE id = %s""",
                (
                    finished_at, status.value, duration_ms,
                    json.dumps(result) if result else None,
                    error, execution_id,
                ),
            )
            conn.commit()
        finally:
            release_conn(conn)

        # Add to in-memory history
        execution = TaskExecution(
            id=execution_id,
            task_id=task.id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            result=result,
            error=error,
        )
        _add_execution(execution)

        logger.info(
            "[ScheduledTasks] Task '%s' %s (duration=%dms)",
            task.id, status.value, duration_ms,
        )

    return {
        "execution_id": execution_id,
        "task_id": task.id,
        "status": status.value,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_ms": duration_ms,
        "result": result,
        "error": error,
    }


# ── Singleton Instance ───────────────────────────────────────────

_scheduler_instance: ScheduledTaskScheduler | None = None


def get_scheduled_task_scheduler() -> ScheduledTaskScheduler:
    """Get the singleton scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ScheduledTaskScheduler()
    return _scheduler_instance


async def init_scheduled_tasks() -> None:
    """Initialize the scheduled tasks system."""
    scheduler = get_scheduled_task_scheduler()
    await scheduler.start()
    logger.info("[ScheduledTasks] System initialized")


async def shutdown_scheduled_tasks() -> None:
    """Shutdown the scheduled tasks system."""
    global _scheduler_instance
    if _scheduler_instance:
        await _scheduler_instance.stop()
        _scheduler_instance = None


# ── Built-in Handlers ────────────────────────────────────────────

async def _cleanup_old_executions() -> dict:
    """Clean up old task execution records (keep last 30 days)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM task_executions WHERE started_at < NOW() - INTERVAL '30 days'"
        )
        deleted = cur.rowcount
        conn.commit()
        return {"deleted_executions": deleted}
    finally:
        release_conn(conn)


async def _health_check() -> dict:
    """System health check for scheduled tasks."""
    scheduler = get_scheduled_task_scheduler()
    tasks = await scheduler.list_tasks()
    return {
        "total_tasks": len(tasks),
        "enabled_tasks": sum(1 for t in tasks if t.enabled),
        "scheduler_running": _scheduler is not None and _scheduler.running,
    }


# Register built-in handlers
register_handler("cleanup_old_executions", _cleanup_old_executions)
register_handler("scheduled_tasks_health", _health_check)