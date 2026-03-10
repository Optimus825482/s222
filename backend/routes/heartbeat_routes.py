"""Heartbeat & Scheduled Tasks API — proaktif agent görevleri ve cron tabanlı zamanlama."""

import sys
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit

router = APIRouter()


# ── Pydantic Models ─────────────────────────────────────────────

class CreateScheduledTaskRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    task_type: str = Field(..., pattern="^(heartbeat|workflow|callable|http|shell)$")
    cron_expr: str = Field(..., min_length=9, max_length=100)
    handler_ref: str = Field(..., min_length=1, max_length=200)
    params: dict = Field(default_factory=dict)
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)


class UpdateScheduledTaskRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    cron_expr: str | None = Field(None, min_length=9, max_length=100)
    params: dict | None = None
    enabled: bool | None = None
    tags: list[str] | None = None


# ── Heartbeat Task Routes ────────────────────────────────────────

def _heartbeat():
    from tools.heartbeat import get_heartbeat_scheduler
    return get_heartbeat_scheduler()


@router.get("/api/heartbeat/tasks")
async def list_heartbeat_tasks(user: dict = Depends(get_current_user)):
    """List heartbeat tasks with status."""
    _audit("heartbeat_tasks", user["user_id"])
    return {"tasks": _heartbeat().list_tasks()}


@router.post("/api/heartbeat/tasks/{name}/trigger")
async def trigger_heartbeat_task(name: str, user: dict = Depends(get_current_user)):
    """Manually trigger a heartbeat task."""
    _audit("heartbeat_trigger", user["user_id"], detail=name)
    task = _heartbeat().tasks.get(name)
    if not task:
        raise HTTPException(404, f"Task '{name}' not found")
    result = await task.handler()
    return {"task": name, "result": result}


@router.patch("/api/heartbeat/tasks/{name}")
async def toggle_heartbeat_task(
    name: str,
    enabled: bool,
    user: dict = Depends(get_current_user),
):
    """Enable or disable a heartbeat task."""
    _audit("heartbeat_toggle", user["user_id"], detail=f"{name}={enabled}")
    task = _heartbeat().tasks.get(name)
    if not task:
        raise HTTPException(404, f"Task '{name}' not found")
    task.enabled = enabled
    return {"name": name, "enabled": enabled}


@router.get("/api/heartbeat/events")
async def get_heartbeat_events(
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Get recent heartbeat events (for dashboard)."""
    from tools.heartbeat import get_heartbeat_events
    limit = max(1, min(limit, 100))
    return {"events": get_heartbeat_events(limit=limit)}


@router.get("/api/heartbeat/status")
async def get_combined_status(user: dict = Depends(get_current_user)):
    """Get combined status of heartbeat and scheduled tasks."""
    from tools.heartbeat import get_combined_task_status
    _audit("heartbeat_status", user["user_id"])
    return await get_combined_task_status()


# ── Scheduled Tasks CRUD ─────────────────────────────────────────

@router.get("/api/scheduled-tasks")
async def list_scheduled_tasks(
    enabled: bool | None = None,
    task_type: str | None = None,
    user: dict = Depends(get_current_user),
):
    """List all scheduled tasks with optional filters."""
    from tools.scheduled_tasks import get_scheduled_task_scheduler, TaskType

    _audit("scheduled_tasks_list", user["user_id"])

    scheduler = get_scheduled_task_scheduler()
    type_filter = TaskType(task_type) if task_type else None

    tasks = await scheduler.list_tasks(
        user_id=user["user_id"],
        enabled=enabled,
        task_type=type_filter,
    )

    return {
        "tasks": [scheduler._task_to_dict(t) for t in tasks],
        "total": len(tasks),
    }


@router.post("/api/scheduled-tasks")
async def create_scheduled_task(
    req: CreateScheduledTaskRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new scheduled task."""
    from tools.scheduled_tasks import get_scheduled_task_scheduler, TaskType

    _audit("scheduled_tasks_create", user["user_id"], detail=req.name)

    try:
        task_type = TaskType(req.task_type)
    except ValueError:
        raise HTTPException(400, f"Invalid task_type: {req.task_type}")

    scheduler = get_scheduled_task_scheduler()

    try:
        task = await scheduler.create_task(
            name=req.name,
            task_type=task_type,
            cron_expr=req.cron_expr,
            handler_ref=req.handler_ref,
            params=req.params,
            enabled=req.enabled,
            user_id=user["user_id"],
            tags=req.tags,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return scheduler._task_to_dict(task)


@router.get("/api/scheduled-tasks/{task_id}")
async def get_scheduled_task(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a single scheduled task."""
    from tools.scheduled_tasks import get_scheduled_task_scheduler

    scheduler = get_scheduled_task_scheduler()
    task = await scheduler.get_task(task_id)

    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")

    # Check ownership (unless admin)
    if task.user_id and task.user_id != user["user_id"]:
        raise HTTPException(403, "Access denied")

    return scheduler._task_to_dict(task)


@router.patch("/api/scheduled-tasks/{task_id}")
async def update_scheduled_task(
    task_id: str,
    req: UpdateScheduledTaskRequest,
    user: dict = Depends(get_current_user),
):
    """Update a scheduled task."""
    from tools.scheduled_tasks import get_scheduled_task_scheduler

    scheduler = get_scheduled_task_scheduler()
    task = await scheduler.get_task(task_id)

    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")

    # Check ownership (unless admin)
    if task.user_id and task.user_id != user["user_id"]:
        raise HTTPException(403, "Access denied")

    _audit("scheduled_tasks_update", user["user_id"], detail=task_id)

    try:
        updated = await scheduler.update_task(
            task_id,
            name=req.name,
            cron_expr=req.cron_expr,
            params=req.params,
            enabled=req.enabled,
            tags=req.tags,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return scheduler._task_to_dict(updated)


@router.delete("/api/scheduled-tasks/{task_id}")
async def delete_scheduled_task(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a scheduled task."""
    from tools.scheduled_tasks import get_scheduled_task_scheduler

    scheduler = get_scheduled_task_scheduler()
    task = await scheduler.get_task(task_id)

    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")

    # Check ownership (unless admin)
    if task.user_id and task.user_id != user["user_id"]:
        raise HTTPException(403, "Access denied")

    _audit("scheduled_tasks_delete", user["user_id"], detail=task_id)

    deleted = await scheduler.delete_task(task_id)
    return {"deleted": deleted, "task_id": task_id}


@router.post("/api/scheduled-tasks/{task_id}/toggle")
async def toggle_scheduled_task(
    task_id: str,
    enabled: bool | None = None,
    user: dict = Depends(get_current_user),
):
    """Toggle a scheduled task on/off."""
    from tools.scheduled_tasks import get_scheduled_task_scheduler

    scheduler = get_scheduled_task_scheduler()
    task = await scheduler.get_task(task_id)

    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")

    # Check ownership (unless admin)
    if task.user_id and task.user_id != user["user_id"]:
        raise HTTPException(403, "Access denied")

    _audit("scheduled_tasks_toggle", user["user_id"], detail=f"{task_id}={enabled}")

    updated = await scheduler.toggle_task(task_id, enabled)
    return scheduler._task_to_dict(updated)


@router.post("/api/scheduled-tasks/{task_id}/trigger")
async def trigger_scheduled_task(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    """Manually trigger a scheduled task execution."""
    from tools.scheduled_tasks import get_scheduled_task_scheduler

    scheduler = get_scheduled_task_scheduler()
    task = await scheduler.get_task(task_id)

    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")

    # Check ownership (unless admin)
    if task.user_id and task.user_id != user["user_id"]:
        raise HTTPException(403, "Access denied")

    _audit("scheduled_tasks_trigger", user["user_id"], detail=task_id)

    try:
        result = await scheduler.trigger_task(task_id)
        return result
    except Exception as e:
        raise HTTPException(500, f"Task execution failed: {e}")


# ── Task Execution History ───────────────────────────────────────

@router.get("/api/scheduled-tasks/{task_id}/executions")
async def get_task_executions(
    task_id: str,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Get execution history for a specific task."""
    from tools.scheduled_tasks import get_scheduled_task_scheduler

    scheduler = get_scheduled_task_scheduler()
    task = await scheduler.get_task(task_id)

    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")

    # Check ownership (unless admin)
    if task.user_id and task.user_id != user["user_id"]:
        raise HTTPException(403, "Access denied")

    executions = await scheduler.get_executions_from_db(task_id, limit)
    return {"executions": executions, "total": len(executions)}


@router.get("/api/scheduled-tasks/executions")
async def list_all_executions(
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    """Get all recent task executions."""
    from tools.scheduled_tasks import get_scheduled_task_scheduler, get_execution_history

    _audit("scheduled_tasks_executions", user["user_id"])

    # Get from memory cache first
    mem_executions = get_execution_history(limit=limit // 2)

    # Also get from DB for completeness
    scheduler = get_scheduled_task_scheduler()
    db_executions = await scheduler.get_executions_from_db(limit=limit // 2)

    # Merge and dedupe
    seen = set()
    all_executions = []
    for e in mem_executions + db_executions:
        if e["id"] not in seen:
            seen.add(e["id"])
            all_executions.append(e)

    return {"executions": all_executions[:limit], "total": len(all_executions)}


# ── Handler Registry ────────────────────────────────────────────

@router.get("/api/scheduled-tasks/handlers")
async def list_handlers(user: dict = Depends(get_current_user)):
    """List all registered callable handlers."""
    from tools.scheduled_tasks import list_handlers

    return {
        "handlers": list_handlers(),
        "total": len(list_handlers()),
    }


@router.post("/api/scheduled-tasks/handlers/{name}")
async def register_custom_handler(
    name: str,
    code: str,
    user: dict = Depends(get_current_user),
):
    """Register a custom Python handler (admin only)."""
    # Security: This should be restricted to admins in production
    # For now, we just validate the name format
    if not name.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Handler name must be alphanumeric with underscores or hyphens")

    _audit("scheduled_tasks_register_handler", user["user_id"], detail=name)

    # Note: Dynamic code execution is dangerous in production
    # This is a placeholder for a more secure implementation
    raise HTTPException(501, "Dynamic handler registration not implemented for security reasons")


# ── Utility Endpoints ───────────────────────────────────────────

@router.post("/api/scheduled-tasks/validate-cron")
async def validate_cron_expression(
    cron_expr: str,
    user: dict = Depends(get_current_user),
):
    """Validate a cron expression and return next run times."""
    from apscheduler.triggers.cron import CronTrigger

    try:
        trigger = CronTrigger.from_crontab(cron_expr)
        now = datetime.now(timezone.utc)
        next_runs = []
        for i in range(5):
            next_run = trigger.get_next_fire_time(None, now)
            if next_run:
                next_runs.append(next_run.isoformat())
                now = next_run
        return {
            "valid": True,
            "cron_expr": cron_expr,
            "next_runs": next_runs,
        }
    except Exception as e:
        return {
            "valid": False,
            "cron_expr": cron_expr,
            "error": str(e),
        }


@router.get("/api/scheduled-tasks/types")
async def list_task_types(user: dict = Depends(get_current_user)):
    """List available task types."""
    from tools.scheduled_tasks import TaskType

    return {
        "types": [
            {
                "value": t.value,
                "description": {
                    "heartbeat": "Built-in heartbeat task handler",
                    "workflow": "Trigger a workflow template",
                    "callable": "Python callable from registry",
                    "http": "HTTP webhook/endpoint call",
                    "shell": "Shell command execution",
                }.get(t.value, t.value),
            }
            for t in TaskType
        ]
    }