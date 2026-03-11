"""Agent identity management routes — SOUL.md, user.md, memory.md, bootstrap.md."""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from shared_state import _AGENT_ROLES

router = APIRouter()

# ── Identity Manager ─────────────────────────────────────────────

try:
    from tools.agent_identity import IdentityManager as _IdentityManager
    _identity_mgr = _IdentityManager()
except Exception as _e:
    print(f"[Backend] WARNING: agent_identity import failed: {_e}")
    _identity_mgr = None


class IdentityFileUpdate(BaseModel):
    content: str


class MemoryEntryRequest(BaseModel):
    entry: str


def _require_identity_manager() -> _IdentityManager:
    if _identity_mgr is None:
        raise HTTPException(status_code=503, detail="Identity manager unavailable")
    return _identity_mgr


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/api/agents/{role}/identity")
async def get_agent_identity(role: str, user: dict = Depends(get_current_user)):
    """Get all identity files for an agent."""
    _audit("get_agent_identity", user["user_id"], detail=f"role={role}")
    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")
    identity_mgr = _require_identity_manager()
    identity = identity_mgr.load(role)
    return {
        "role": identity.role,
        "soul": identity.soul,
        "user": identity.user,
        "memory": identity.memory,
        "bootstrap": identity.bootstrap,
    }


@router.put("/api/agents/{role}/identity/{file_type}")
async def update_identity_file(
    role: str, file_type: str, body: IdentityFileUpdate,
    user: dict = Depends(get_current_user),
):
    """Update a specific identity file (soul, user, memory, bootstrap)."""
    _audit("update_identity_file", user["user_id"], detail=f"role={role}, file={file_type}")
    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")
    identity_mgr = _require_identity_manager()
    try:
        identity_mgr.save_file(role, file_type, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "ok", "role": role, "file_type": file_type}


@router.post("/api/agents/{role}/memory")
async def add_agent_memory_entry(
    role: str, body: MemoryEntryRequest,
    user: dict = Depends(get_current_user),
):
    """Add a new memory entry for an agent."""
    _audit("add_agent_memory", user["user_id"], detail=f"role={role}")
    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")
    identity_mgr = _require_identity_manager()
    identity_mgr.update_memory(role, body.entry)
    return {"status": "ok", "role": role}


@router.post("/api/agents/identity/initialize")
async def initialize_all_identities(user: dict = Depends(get_current_user)):
    """Initialize identity files for all agents."""
    _audit("initialize_identities", user["user_id"])
    from config import MODELS as _MODELS_CFG

    identity_mgr = _require_identity_manager()
    count = identity_mgr.initialize_all(_MODELS_CFG)
    agents = identity_mgr.list_agents()
    return {"initialized": count, "agents": agents}


@router.get("/api/agents/identity/list")
async def list_identity_agents(user: dict = Depends(get_current_user)):
    """List agents that have identity files."""
    identity_mgr = _require_identity_manager()
    agents = identity_mgr.list_agents()
    return {"agents": agents}
