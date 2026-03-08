"""Heartbeat API — proaktif agent görevleri (Faz 11.2)."""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit

router = APIRouter()


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
