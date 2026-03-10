"""
Workspace & Agent Events API routes — pi-mom inspired features.
"""

from __future__ import annotations

import os
import sys

_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any

from deps import get_current_user

router = APIRouter(tags=["workspace"])


# ── Request Models ───────────────────────────────────────────────

class WorkspaceSkillCreate(BaseModel):
    agent_role: str
    skill_name: str
    description: str
    usage_instructions: str = ""
    scripts: dict[str, str] = {}


class WorkspaceScriptRun(BaseModel):
    agent_role: str
    skill_name: str
    script_name: str
    args: list[str] = []
    stdin_data: str | None = None


class AgentEventCreate(BaseModel):
    event_type: str  # immediate, one-shot, periodic
    target_agent: str
    message: str
    schedule: str | None = None
    trigger_at: str | None = None
    metadata: dict[str, Any] = {}


# ── Workspace Endpoints ──────────────────────────────────────────

@router.get("/api/workspace/stats")
async def api_workspace_stats(user: dict = Depends(get_current_user)):
    """Get workspace statistics across all agents."""
    from tools.self_managing_workspace import get_workspace_manager
    manager = get_workspace_manager()
    return manager.get_workspace_stats()


@router.get("/api/workspace/skills")
async def api_workspace_all_skills(user: dict = Depends(get_current_user)):
    """List all skills across all agent workspaces."""
    from tools.self_managing_workspace import get_workspace_manager
    manager = get_workspace_manager()
    return manager.list_all_skills()


@router.get("/api/workspace/{agent_role}/skills")
async def api_workspace_agent_skills(
    agent_role: str,
    user: dict = Depends(get_current_user),
):
    """List skills for a specific agent."""
    from tools.self_managing_workspace import get_workspace_manager
    ws = get_workspace_manager().get_agent_workspace(agent_role)
    return ws.list_skills()


@router.post("/api/workspace/skills")
async def api_workspace_create_skill(
    req: WorkspaceSkillCreate,
    user: dict = Depends(get_current_user),
):
    """Create an executable skill in an agent's workspace."""
    from tools.self_managing_workspace import get_workspace_manager
    ws = get_workspace_manager().get_agent_workspace(req.agent_role)
    return ws.create_skill(
        skill_name=req.skill_name,
        description=req.description,
        usage_instructions=req.usage_instructions,
        scripts=req.scripts,
    )


@router.post("/api/workspace/run")
async def api_workspace_run_script(
    req: WorkspaceScriptRun,
    user: dict = Depends(get_current_user),
):
    """Execute a script from an agent's workspace skill."""
    from tools.self_managing_workspace import get_workspace_manager
    ws = get_workspace_manager().get_agent_workspace(req.agent_role)
    return ws.execute_skill_script(
        skill_name=req.skill_name,
        script_name=req.script_name,
        args=req.args,
        stdin_data=req.stdin_data,
    )


@router.get("/api/workspace/{agent_role}/memory")
async def api_workspace_memory(
    agent_role: str,
    user: dict = Depends(get_current_user),
):
    """Read an agent's workspace-local memory."""
    from tools.self_managing_workspace import get_workspace_manager
    ws = get_workspace_manager().get_agent_workspace(agent_role)
    return {"agent_role": agent_role, "memory": ws.read_memory()}


# ── Agent Events Endpoints ───────────────────────────────────────

@router.post("/api/events")
async def api_create_event(
    req: AgentEventCreate,
    user: dict = Depends(get_current_user),
):
    """Create an agent event (immediate, one-shot, or periodic)."""
    from tools.agent_events import create_event, AgentEventType
    from datetime import datetime

    evt_type = AgentEventType(req.event_type)
    trigger_at = None
    if req.trigger_at:
        trigger_at = datetime.fromisoformat(req.trigger_at)

    event = create_event(
        event_type=evt_type,
        target_agent=req.target_agent,
        message=req.message,
        schedule=req.schedule,
        trigger_at=trigger_at,
        metadata=req.metadata,
        created_by=user.get("username", "api"),
    )
    return event.to_dict()


@router.get("/api/events")
async def api_list_events(
    target_agent: str | None = None,
    user: dict = Depends(get_current_user),
):
    """List active agent events."""
    from tools.agent_events import list_events
    return list_events(target_agent=target_agent)


@router.delete("/api/events/{event_id}")
async def api_delete_event(
    event_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete an agent event."""
    from tools.agent_events import delete_event
    ok = delete_event(event_id)
    if not ok:
        raise HTTPException(404, f"Event '{event_id}' not found")
    return {"deleted": event_id}


@router.get("/api/events/stats")
async def api_event_stats(user: dict = Depends(get_current_user)):
    """Get event system statistics."""
    from tools.agent_events import get_event_stats
    return get_event_stats()
