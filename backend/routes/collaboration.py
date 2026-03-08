"""Collaboration routes: Charts, Progress, Workspace, Context Board, Roles, Collab Docs."""

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from config import MODELS
from deps import get_current_user, _audit
from shared_state import _AGENT_ROLES, _utcnow

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
# Section 14 · Chart Generation
# ══════════════════════════════════════════════════════════════════


class ChartGenerateRequest(BaseModel):
    chart_type: str = "bar"
    data: dict = {}
    title: str = "Chart"
    width: int = 800
    height: int = 450


@router.post("/api/charts/generate")
async def api_generate_chart(req: ChartGenerateRequest, user: dict = Depends(get_current_user)):
    from tools.chart_generator import generate_chart
    result = generate_chart(
        chart_type=req.chart_type,
        data=req.data,
        title=req.title,
        width=req.width,
        height=req.height,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    _audit("chart_generate", user["user_id"], f"type={req.chart_type} title={req.title}")
    return result


@router.get("/api/charts")
async def api_list_charts(limit: int = 30, user: dict = Depends(get_current_user)):
    from tools.chart_generator import list_charts
    return list_charts(limit=limit)


@router.get("/api/charts/{chart_id}")
async def api_get_chart(chart_id: str, user: dict = Depends(get_current_user)):
    from tools.chart_generator import get_chart_base64
    b64 = get_chart_base64(chart_id)
    if b64 is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    return {"chart_id": chart_id, "image_base64": b64}


@router.delete("/api/charts/{chart_id}")
async def api_delete_chart(chart_id: str, user: dict = Depends(get_current_user)):
    from tools.chart_generator import CHART_DIR
    path = os.path.join(CHART_DIR, f"{chart_id}.png")
    if os.path.exists(path):
        os.remove(path)
        _audit("chart_delete", user["user_id"], f"chart_id={chart_id}")
        return {"status": "deleted", "chart_id": chart_id}
    raise HTTPException(status_code=404, detail="Chart not found")


@router.get("/api/charts/{chart_id}/download")
async def api_download_chart(chart_id: str, user: dict = Depends(get_current_user)):
    from tools.chart_generator import CHART_DIR
    path = os.path.join(CHART_DIR, f"{chart_id}.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(path, media_type="image/png", filename=f"{chart_id}.png")


# ══════════════════════════════════════════════════════════════════
# Section 15 · Agent Progress Tracking (Faz 10.5)
# ══════════════════════════════════════════════════════════════════

from tools.agent_progress_tracker import get_tracker, AgentStatus


@router.get("/api/progress")
async def api_get_all_progress(user: dict = Depends(get_current_user)):
    """Tüm agent ilerlemelerini al"""
    tracker = get_tracker()
    return {"progress": tracker.get_all_progress()}


@router.get("/api/progress/{agent_id}")
async def api_get_agent_progress(agent_id: str, user: dict = Depends(get_current_user)):
    """Belirli bir agent'ın ilerlemesini al"""
    tracker = get_tracker()
    progress = tracker.get_progress(agent_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Agent progress not found")
    return progress


@router.websocket("/ws/progress")
async def ws_progress_stream(websocket: WebSocket):
    """Gerçek zamanlı ilerleme güncellemeleri"""
    await websocket.accept()
    tracker = get_tracker()
    queue = await tracker.subscribe()

    try:
        while True:
            progress = await queue.get()
            await websocket.send_json(progress)
    except WebSocketDisconnect:
        tracker.unsubscribe(queue)
    except Exception as e:
        print(f"[Progress WS] Error: {e}")
        tracker.unsubscribe(queue)


@router.post("/api/progress/clear")
async def api_clear_completed_progress(max_age_minutes: int = 60, user: dict = Depends(get_current_user)):
    """Tamamlanmış görevleri temizle"""
    tracker = get_tracker()
    tracker.clear_completed(max_age_minutes)
    return {"status": "cleared"}


def _progress_to_live_item(p: dict) -> dict:
    """Backend progress dict → panel live format (agent-progress-tracker-panel)."""
    step = p.get("current_step") or {}
    steps = p.get("steps") or []

    def _map_status(s: str) -> str:
        if s in ("idle", "thinking", "executing", "waiting", "error"):
            return s
        if s == "completed":
            return "completed"
        return "in_progress" if s in ("thinking", "executing") else "pending"

    sub_tasks = [
        {
            "id": st.get("step_id", str(i)),
            "description": st.get("description", ""),
            "status": _map_status(st.get("status", "pending")),
        }
        for i, st in enumerate(steps)
    ]
    return {
        "agent_id": p.get("agent_id", ""),
        "agent_role": p.get("agent_name", p.get("agent_id", "")),
        "current_task": step.get("description", p.get("task_id", "")),
        "status": p.get("status", "idle"),
        "progress_percentage": p.get("overall_progress", 0),
        "started_at": p.get("started_at", ""),
        "estimated_completion": p.get("updated_at", ""),
        "sub_tasks": sub_tasks,
    }


@router.get("/api/agent-progress/live")
async def api_agent_progress_live(user: dict = Depends(get_current_user)):
    """Tüm agent ilerlemelerini canlı panel formatında (Faz 10.5 — Canlı İlerleme)."""
    tracker = get_tracker()
    all_p = tracker.get_all_progress()
    return [_progress_to_live_item(x) for x in all_p if x]


# ══════════════════════════════════════════════════════════════════
# Section 16 · Shared Workspace (Faz 10.6)
# ══════════════════════════════════════════════════════════════════

from tools.shared_workspace import get_workspace


class WorkspaceCreateRequest(BaseModel):
    workspace_id: str
    name: str
    metadata: dict = {}


class WorkspaceMemberRequest(BaseModel):
    user_id: str
    role: str = "member"


class WorkspaceItemRequest(BaseModel):
    item_type: str
    content: str
    metadata: dict = {}


import logging as _ws_logging
_ws_logger = _ws_logging.getLogger("workspace")


def _safe_get_workspace():
    """get_workspace() wrapper — Qdrant erişilemezse None döner."""
    try:
        return get_workspace()
    except Exception as exc:
        _ws_logger.warning("Workspace backend unavailable: %s", exc)
        return None


@router.post("/api/workspaces")
async def api_create_workspace(req: WorkspaceCreateRequest, user: dict = Depends(get_current_user)):
    """Yeni workspace oluştur"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"error": "workspace backend unavailable"}
        result = workspace.create_workspace(
            workspace_id=req.workspace_id,
            owner_id=user["user_id"],
            name=req.name,
            metadata=req.metadata
        )
        _audit("workspace_create", user["user_id"], f"workspace_id={req.workspace_id}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        _ws_logger.exception("api_create_workspace error")
        return {"error": str(exc)}


@router.get("/api/workspaces")
async def api_list_workspaces(user: dict = Depends(get_current_user)):
    """Kullanıcının workspace'lerini listele"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"workspaces": []}
        return {"workspaces": workspace.list_workspaces(user["user_id"])}
    except Exception as exc:
        _ws_logger.exception("api_list_workspaces error")
        return {"workspaces": []}


@router.get("/api/workspaces/{workspace_id}")
async def api_get_workspace(workspace_id: str, user: dict = Depends(get_current_user)):
    """Workspace detaylarını al"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"error": "workspace backend unavailable"}
        result = workspace.get_workspace(workspace_id)
        if not result:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if user["user_id"] not in result.get("members", []):
            raise HTTPException(status_code=403, detail="Access denied")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        _ws_logger.exception("api_get_workspace error")
        return {"error": str(exc)}


@router.post("/api/workspaces/{workspace_id}/members")
async def api_add_workspace_member(
    workspace_id: str,
    req: WorkspaceMemberRequest,
    user: dict = Depends(get_current_user)
):
    """Workspace'e üye ekle"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"error": "workspace backend unavailable"}
        ws = workspace.get_workspace(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws.get("owner_id") != user["user_id"]:
            raise HTTPException(status_code=403, detail="Only owner can add members")
        success = workspace.add_member(workspace_id, req.user_id, req.role)
        if success:
            _audit("workspace_add_member", user["user_id"], f"workspace={workspace_id} member={req.user_id}")
            return {"status": "added", "user_id": req.user_id}
        raise HTTPException(status_code=400, detail="Failed to add member")
    except HTTPException:
        raise
    except Exception as exc:
        _ws_logger.exception("api_add_workspace_member error")
        return {"error": str(exc)}


@router.delete("/api/workspaces/{workspace_id}/members/{user_id}")
async def api_remove_workspace_member(
    workspace_id: str,
    user_id: str,
    user: dict = Depends(get_current_user)
):
    """Workspace'den üye çıkar"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"error": "workspace backend unavailable"}
        ws = workspace.get_workspace(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws.get("owner_id") != user["user_id"]:
            raise HTTPException(status_code=403, detail="Only owner can remove members")
        success = workspace.remove_member(workspace_id, user_id)
        if success:
            _audit("workspace_remove_member", user["user_id"], f"workspace={workspace_id} member={user_id}")
            return {"status": "removed", "user_id": user_id}
        raise HTTPException(status_code=400, detail="Failed to remove member")
    except HTTPException:
        raise
    except Exception as exc:
        _ws_logger.exception("api_remove_workspace_member error")
        return {"error": str(exc)}


@router.post("/api/workspaces/{workspace_id}/items")
async def api_add_workspace_item(
    workspace_id: str,
    req: WorkspaceItemRequest,
    user: dict = Depends(get_current_user)
):
    """Workspace'e item ekle"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"error": "workspace backend unavailable"}
        ws = workspace.get_workspace(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if user["user_id"] not in ws.get("members", []):
            raise HTTPException(status_code=403, detail="Access denied")
        vector = [0.0] * 1536
        item_id = workspace.add_item(
            workspace_id=workspace_id,
            item_type=req.item_type,
            content=req.content,
            vector=vector,
            author_id=user["user_id"],
            metadata=req.metadata
        )
        _audit("workspace_add_item", user["user_id"], f"workspace={workspace_id} type={req.item_type}")
        return {"status": "added", "item_id": item_id}
    except HTTPException:
        raise
    except Exception as exc:
        _ws_logger.exception("api_add_workspace_item error")
        return {"error": str(exc)}


@router.get("/api/workspaces/{workspace_id}/items")
async def api_get_workspace_items(
    workspace_id: str,
    item_type: str = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user)
):
    """Workspace item'larını al"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"items": [], "count": 0}
        ws = workspace.get_workspace(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if user["user_id"] not in ws.get("members", []):
            raise HTTPException(status_code=403, detail="Access denied")
        items = workspace.get_items(workspace_id, item_type, limit, offset)
        return {"items": items, "count": len(items)}
    except HTTPException:
        raise
    except Exception as exc:
        _ws_logger.exception("api_get_workspace_items error")
        return {"items": [], "count": 0}


@router.delete("/api/workspaces/{workspace_id}/items/{item_id}")
async def api_delete_workspace_item(
    workspace_id: str,
    item_id: str,
    user: dict = Depends(get_current_user)
):
    """Workspace item'ı sil"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"error": "workspace backend unavailable"}
        ws = workspace.get_workspace(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if user["user_id"] not in ws.get("members", []):
            raise HTTPException(status_code=403, detail="Access denied")
        success = workspace.delete_item(item_id)
        if success:
            _audit("workspace_delete_item", user["user_id"], f"workspace={workspace_id} item={item_id}")
            return {"status": "deleted", "item_id": item_id}
        raise HTTPException(status_code=400, detail="Failed to delete item")
    except HTTPException:
        raise
    except Exception as exc:
        _ws_logger.exception("api_delete_workspace_item error")
        return {"error": str(exc)}


@router.get("/api/workspaces/{workspace_id}/stats")
async def api_get_workspace_stats(workspace_id: str, user: dict = Depends(get_current_user)):
    """Workspace istatistikleri"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"error": "workspace backend unavailable"}
        ws = workspace.get_workspace(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if user["user_id"] not in ws.get("members", []):
            raise HTTPException(status_code=403, detail="Access denied")
        return workspace.get_workspace_stats(workspace_id)
    except HTTPException:
        raise
    except Exception as exc:
        _ws_logger.exception("api_get_workspace_stats error")
        return {"error": str(exc)}


@router.post("/api/workspaces/{workspace_id}/sync/cli")
async def api_sync_workspace_to_cli(
    workspace_id: str,
    cli_memory_path: str,
    user: dict = Depends(get_current_user)
):
    """CLI hafızasına senkronize et"""
    try:
        workspace = _safe_get_workspace()
        if workspace is None:
            return {"error": "workspace backend unavailable"}
        ws = workspace.get_workspace(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if user["user_id"] not in ws.get("members", []):
            raise HTTPException(status_code=403, detail="Access denied")
        success = workspace.sync_to_cli(workspace_id, cli_memory_path)
        if success:
            _audit("workspace_sync_cli", user["user_id"], f"workspace={workspace_id}")
            return {"status": "synced", "path": cli_memory_path}
        raise HTTPException(status_code=400, detail="Sync failed")
    except HTTPException:
        raise
    except Exception as exc:
        _ws_logger.exception("api_sync_workspace_to_cli error")
        return {"error": str(exc)}


# ══════════════════════════════════════════════════════════════════
# §15  Shared Context Board  (Paylaşımlı Çalışma Alanı)
# ══════════════════════════════════════════════════════════════════

_CONTEXT_BOARD: list[dict[str, Any]] = []
_CONTEXT_BOARD_MAX = 200

_VALID_CONTEXT_TYPES = {"note", "finding", "link", "code_snippet", "metric"}


class ContextBoardItemCreate(BaseModel):
    type: str  # note / finding / link / code_snippet / metric
    title: str
    content: str
    created_by: str  # agent role
    tags: list[str] = []
    pinned: bool = False


class ContextBoardItemUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    pinned: bool | None = None


@router.post("/api/context-board/items")
async def api_context_board_add(
    req: ContextBoardItemCreate,
    user: dict = Depends(get_current_user),
):
    """Add a new item to the shared context board."""
    _audit("context_board_add", user["user_id"], f"type={req.type} by={req.created_by}")

    if req.type not in _VALID_CONTEXT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {sorted(_VALID_CONTEXT_TYPES)}")
    if req.created_by not in _AGENT_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid created_by. Must be one of: {_AGENT_ROLES}")
    if not req.title.strip() or not req.content.strip():
        raise HTTPException(status_code=400, detail="title and content are required")

    now = _utcnow()
    item: dict[str, Any] = {
        "id": f"ctx-{uuid.uuid4().hex[:8]}",
        "type": req.type,
        "title": req.title.strip()[:200],
        "content": req.content.strip()[:5000],
        "created_by": req.created_by,
        "tags": [t.strip()[:50] for t in req.tags[:20]],
        "pinned": req.pinned,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _CONTEXT_BOARD.append(item)

    # Cap at max - remove oldest non-pinned first
    while len(_CONTEXT_BOARD) > _CONTEXT_BOARD_MAX:
        idx_to_remove: int | None = None
        for i, it in enumerate(_CONTEXT_BOARD):
            if not it["pinned"]:
                idx_to_remove = i
                break
        if idx_to_remove is not None:
            _CONTEXT_BOARD.pop(idx_to_remove)
        else:
            # all pinned - remove oldest anyway
            _CONTEXT_BOARD.pop(0)

    return {"item": item, "total_items": len(_CONTEXT_BOARD)}


@router.get("/api/context-board/items")
async def api_context_board_list(
    type: str | None = None,
    created_by: str | None = None,
    pinned: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """List context board items with optional filters."""
    _audit("context_board_list", user["user_id"])

    items = _CONTEXT_BOARD.copy()

    if type:
        items = [i for i in items if i["type"] == type]
    if created_by:
        items = [i for i in items if i["created_by"] == created_by]
    if pinned is not None:
        items = [i for i in items if i["pinned"] is pinned]
    if search:
        q = search.lower()
        items = [i for i in items if q in i["title"].lower() or q in i["content"].lower()]

    # Sort: pinned first, then by created_at desc
    pinned_items = sorted([i for i in items if i["pinned"]], key=lambda x: x["created_at"], reverse=True)
    unpinned_items = sorted([i for i in items if not i["pinned"]], key=lambda x: x["created_at"], reverse=True)
    items = pinned_items + unpinned_items

    limit = max(1, min(limit, 200))
    return {
        "total": len(items),
        "items": items[:limit],
        "timestamp": _utcnow().isoformat(),
    }


@router.put("/api/context-board/items/{item_id}")
async def api_context_board_update(
    item_id: str,
    req: ContextBoardItemUpdate,
    user: dict = Depends(get_current_user),
):
    """Update an existing context board item."""
    _audit("context_board_update", user["user_id"], f"item_id={item_id}")

    target: dict[str, Any] | None = None
    for it in _CONTEXT_BOARD:
        if it["id"] == item_id:
            target = it
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Context board item not found")

    if req.title is not None:
        target["title"] = req.title.strip()[:200]
    if req.content is not None:
        target["content"] = req.content.strip()[:5000]
    if req.tags is not None:
        target["tags"] = [t.strip()[:50] for t in req.tags[:20]]
    if req.pinned is not None:
        target["pinned"] = req.pinned
    target["updated_at"] = _utcnow().isoformat()

    return {"item": target}


@router.delete("/api/context-board/items/{item_id}")
async def api_context_board_delete(
    item_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a context board item."""
    _audit("context_board_delete", user["user_id"], f"item_id={item_id}")

    for i, it in enumerate(_CONTEXT_BOARD):
        if it["id"] == item_id:
            _CONTEXT_BOARD.pop(i)
            return {"status": "deleted", "item_id": item_id}
    raise HTTPException(status_code=404, detail="Context board item not found")


@router.post("/api/context-board/items/{item_id}/pin")
async def api_context_board_toggle_pin(
    item_id: str,
    user: dict = Depends(get_current_user),
):
    """Toggle pin status of a context board item."""
    _audit("context_board_pin", user["user_id"], f"item_id={item_id}")

    for it in _CONTEXT_BOARD:
        if it["id"] == item_id:
            it["pinned"] = not it["pinned"]
            it["updated_at"] = _utcnow().isoformat()
            return {"item_id": item_id, "pinned": it["pinned"]}
    raise HTTPException(status_code=404, detail="Context board item not found")


@router.get("/api/context-board/stats")
async def api_context_board_stats(user: dict = Depends(get_current_user)):
    """Get context board statistics."""
    _audit("context_board_stats", user["user_id"])

    by_type: dict[str, int] = {}
    by_agent: dict[str, int] = {}
    pinned_count = 0

    for it in _CONTEXT_BOARD:
        by_type[it["type"]] = by_type.get(it["type"], 0) + 1
        by_agent[it["created_by"]] = by_agent.get(it["created_by"], 0) + 1
        if it["pinned"]:
            pinned_count += 1

    return {
        "total_items": len(_CONTEXT_BOARD),
        "by_type": by_type,
        "by_agent": by_agent,
        "pinned_count": pinned_count,
        "timestamp": _utcnow().isoformat(),
    }


# ══════════════════════════════════════════════════════════════════
# §16  Dynamic Role Assignment  (Dinamik Rol Atama)
# ══════════════════════════════════════════════════════════════════

_ROLE_ASSIGNMENTS: list[dict[str, Any]] = []
_ROLE_ASSIGNMENT_HISTORY: list[dict[str, Any]] = []


class RoleAssignRequest(BaseModel):
    agent_id: str       # e.g. "thinker"
    new_role: str       # e.g. "researcher" — the role behavior to adopt
    reason: str
    task_context: str = ""
    duration_minutes: int | None = None  # None = permanent until reverted


def _expire_role_assignments() -> None:
    """Auto-expire assignments past their expires_at."""
    now = _utcnow()
    for a in _ROLE_ASSIGNMENTS:
        if a["status"] == "active" and a["expires_at"]:
            if now.isoformat() >= a["expires_at"]:
                a["status"] = "expired"
                a["reverted_at"] = now.isoformat()


def _revert_active_assignment(agent_id: str) -> None:
    """Revert any active assignment for the given agent."""
    now = _utcnow()
    for a in _ROLE_ASSIGNMENTS:
        if a["agent_id"] == agent_id and a["status"] == "active":
            a["status"] = "auto-reverted"
            a["reverted_at"] = now.isoformat()


@router.post("/api/agents/role-assign")
async def api_role_assign(
    req: RoleAssignRequest,
    user: dict = Depends(get_current_user),
):
    """Assign a new dynamic role to an agent."""
    _audit("role_assign", user["user_id"], f"{req.agent_id}->{req.new_role}")

    if req.agent_id not in _AGENT_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid agent_id. Must be one of: {_AGENT_ROLES}")
    if req.new_role not in _AGENT_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid new_role. Must be one of: {_AGENT_ROLES}")
    if req.agent_id == req.new_role:
        raise HTTPException(status_code=400, detail="Cannot assign same role — agent already has this role")
    if not req.reason.strip():
        raise HTTPException(status_code=400, detail="reason is required")

    # Auto-revert existing active assignment for this agent
    _revert_active_assignment(req.agent_id)

    now = _utcnow()
    expires_at: str | None = None
    if req.duration_minutes is not None:
        if req.duration_minutes < 1:
            raise HTTPException(status_code=400, detail="duration_minutes must be >= 1")
        expires_at = (now + timedelta(minutes=req.duration_minutes)).isoformat()

    assignment: dict[str, Any] = {
        "id": f"ra-{uuid.uuid4().hex[:8]}",
        "agent_id": req.agent_id,
        "original_role": req.agent_id,
        "new_role": req.new_role,
        "reason": req.reason.strip()[:500],
        "task_context": req.task_context.strip()[:1000],
        "assigned_at": now.isoformat(),
        "expires_at": expires_at,
        "status": "active",
        "reverted_at": None,
    }
    _ROLE_ASSIGNMENTS.append(assignment)
    _ROLE_ASSIGNMENT_HISTORY.append(assignment)

    # Enrich with model metadata
    model_meta = MODELS.get(req.new_role, {})
    enriched = {
        **assignment,
        "new_role_name": model_meta.get("name", req.new_role),
        "new_role_icon": model_meta.get("icon", "⚙️"),
        "new_role_color": model_meta.get("color", "#888"),
    }

    return {"assignment": enriched, "total_active": sum(1 for a in _ROLE_ASSIGNMENTS if a["status"] == "active")}


@router.get("/api/agents/role-assignments")
async def api_role_assignments_list(user: dict = Depends(get_current_user)):
    """List current active role assignments."""
    _audit("role_assignments_list", user["user_id"])

    _expire_role_assignments()

    active = []
    for a in _ROLE_ASSIGNMENTS:
        if a["status"] == "active":
            meta = MODELS.get(a["new_role"], {})
            active.append({
                **a,
                "new_role_name": meta.get("name", a["new_role"]),
                "new_role_icon": meta.get("icon", "⚙️"),
                "new_role_color": meta.get("color", "#888"),
                "original_role_name": MODELS.get(a["original_role"], {}).get("name", a["original_role"]),
                "original_role_icon": MODELS.get(a["original_role"], {}).get("icon", "⚙️"),
            })

    return {
        "active_assignments": active,
        "total": len(active),
        "timestamp": _utcnow().isoformat(),
    }


@router.post("/api/agents/role-revert/{assignment_id}")
async def api_role_revert(
    assignment_id: str,
    user: dict = Depends(get_current_user),
):
    """Revert a role assignment back to original."""
    _audit("role_revert", user["user_id"], f"assignment_id={assignment_id}")

    for a in _ROLE_ASSIGNMENTS:
        if a["id"] == assignment_id:
            if a["status"] != "active":
                raise HTTPException(status_code=400, detail=f"Assignment is already {a['status']}")
            a["status"] = "reverted"
            a["reverted_at"] = _utcnow().isoformat()
            return {"status": "reverted", "assignment": a}
    raise HTTPException(status_code=404, detail="Assignment not found")


@router.get("/api/agents/role-history")
async def api_role_history(
    agent_id: str | None = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Full role assignment history."""
    _audit("role_history", user["user_id"])

    history = _ROLE_ASSIGNMENT_HISTORY.copy()
    if agent_id:
        history = [h for h in history if h["agent_id"] == agent_id]

    history.sort(key=lambda x: x["assigned_at"], reverse=True)
    limit = max(1, min(limit, 200))

    return {
        "total": len(history),
        "history": history[:limit],
        "timestamp": _utcnow().isoformat(),
    }


@router.get("/api/agents/role-capabilities")
async def api_role_capabilities(user: dict = Depends(get_current_user)):
    """Role capability matrix — strengths and best-for per role."""
    _audit("role_capabilities", user["user_id"])

    _CAPABILITIES: dict[str, dict[str, Any]] = {
        "orchestrator": {
            "strengths": ["task decomposition", "routing", "synthesis", "coordination"],
            "best_for": ["complex multi-step tasks", "task planning", "agent coordination"],
        },
        "thinker": {
            "strengths": ["deep reasoning", "analysis", "planning", "complex problem solving"],
            "best_for": ["architecture decisions", "complex analysis", "strategic planning"],
        },
        "speed": {
            "strengths": ["fast responses", "code generation", "formatting", "quick tasks"],
            "best_for": ["code snippets", "quick answers", "formatting", "simple tasks"],
        },
        "researcher": {
            "strengths": ["web search", "data gathering", "summarization", "fact-finding"],
            "best_for": ["research tasks", "information gathering", "literature review"],
        },
        "reasoner": {
            "strengths": ["chain-of-thought", "math", "logic", "verification"],
            "best_for": ["mathematical problems", "logical reasoning", "proof verification"],
        },
        "critic": {
            "strengths": ["quality review", "fact-checking", "weakness detection", "improvement suggestions"],
            "best_for": ["code review", "quality assurance", "fact verification"],
        },
    }

    result: list[dict[str, Any]] = []
    for role in _AGENT_ROLES:
        meta = MODELS.get(role, {})
        caps = _CAPABILITIES.get(role, {"strengths": [], "best_for": []})
        result.append({
            "role": role,
            "name": meta.get("name", role),
            "icon": meta.get("icon", "⚙️"),
            "color": meta.get("color", "#888"),
            "description": meta.get("description", ""),
            "model_id": meta.get("id", ""),
            "max_tokens": meta.get("max_tokens", 0),
            "has_thinking": meta.get("has_thinking", False),
            "strengths": caps["strengths"],
            "best_for": caps["best_for"],
        })

    return {"roles": result, "timestamp": _utcnow().isoformat()}


@router.get("/api/agents/effective-roles")
async def api_effective_roles(user: dict = Depends(get_current_user)):
    """Current effective role for each agent (with active overrides)."""
    _audit("effective_roles", user["user_id"])

    _expire_role_assignments()

    # Build override map: agent_id -> active assignment
    overrides: dict[str, dict[str, Any]] = {}
    for a in _ROLE_ASSIGNMENTS:
        if a["status"] == "active":
            overrides[a["agent_id"]] = a

    result: dict[str, dict[str, Any]] = {}
    for role in _AGENT_ROLES:
        meta = MODELS.get(role, {})
        override = overrides.get(role)
        effective = override["new_role"] if override else role
        effective_meta = MODELS.get(effective, {})

        result[role] = {
            "original_role": role,
            "effective_role": effective,
            "is_overridden": override is not None,
            "assignment_id": override["id"] if override else None,
            "expires_at": override["expires_at"] if override else None,
            "name": meta.get("name", role),
            "icon": meta.get("icon", "⚙️"),
            "color": meta.get("color", "#888"),
            "effective_name": effective_meta.get("name", effective),
            "effective_icon": effective_meta.get("icon", "⚙️"),
            "effective_color": effective_meta.get("color", "#888"),
        }

    return {"agents": result, "timestamp": _utcnow().isoformat()}


# ══════════════════════════════════════════════════════════════════
# §17  Collaborative Document Editing  (Ortak Doküman Düzenleme)
# ══════════════════════════════════════════════════════════════════

from tools.collaborative_doc import (
    get_doc_manager,
    CollaborativeDocument,
    DocumentOp,
    OperationType,
    tokenize_code,
    get_syntax_style,
    AgentCollabProtocol,
)


class CollabDocBroadcaster:
    """In-memory pub/sub for real-time collab doc updates (edit_applied, user_joined, user_left)."""

    def __init__(self):
        self._subs: dict[str, list[tuple[WebSocket, str]]] = {}  # doc_id -> [(ws, user_id), ...]

    def subscribe(self, doc_id: str, websocket: WebSocket, user_id: str) -> None:
        if doc_id not in self._subs:
            self._subs[doc_id] = []
        self._subs[doc_id].append((websocket, user_id))

    def unsubscribe(self, doc_id: str, websocket: WebSocket) -> None:
        if doc_id not in self._subs:
            return
        self._subs[doc_id] = [(ws, uid) for ws, uid in self._subs[doc_id] if ws != websocket]
        if not self._subs[doc_id]:
            del self._subs[doc_id]

    def get_active_users(self, doc_id: str) -> list[str]:
        return [uid for _, uid in self._subs.get(doc_id, [])]

    async def broadcast(self, doc_id: str, payload: dict) -> None:
        for ws, _ in self._subs.get(doc_id, []):
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    async def broadcast_edit(self, doc_id: str, content: str, new_version: int) -> None:
        await self.broadcast(
            doc_id,
            {"type": "edit_applied", "content": content, "new_version": new_version},
        )

    async def broadcast_presence(self, doc_id: str) -> None:
        active = self.get_active_users(doc_id)
        await self.broadcast(doc_id, {"type": "user_joined", "active_users": active})


_collab_broadcaster = CollabDocBroadcaster()


class DocCreateRequest(BaseModel):
    title: str
    content: str = ""
    language: str = "python"


class DocUpdateRequest(BaseModel):
    op_type: str  # insert, delete, move
    position: int
    text: str = ""
    length: int = 0
    metadata: dict = None


class DocCollaboratorRequest(BaseModel):
    agent_id: str


@router.post("/api/collab-docs")
async def api_collab_doc_create(
    req: DocCreateRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new collaborative document."""
    _audit("collab_doc_create", user["user_id"], req.title)

    manager = get_doc_manager()
    doc = manager.create_document(
        title=req.title,
        content=req.content,
        creator_id=user["user_id"],
        language=req.language,
    )

    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "content": doc.content,
        "collaborators": doc.collaborators,
        "created_at": doc.created_at,
        "language": doc.language,
    }


@router.get("/api/collab-docs")
async def api_collab_doc_list(user: dict = Depends(get_current_user)):
    """List all accessible collaborative documents."""
    _audit("collab_doc_list", user["user_id"])

    manager = get_doc_manager()
    docs = manager.list_documents(agent_id=user["user_id"])

    return {
        "documents": [
            {
                "doc_id": d.doc_id,
                "title": d.title,
                "collaborators": d.collaborators,
                "created_at": d.created_at,
                "updated_at": d.updated_at,
                "language": d.language,
            }
            for d in docs
        ],
        "total": len(docs),
        "timestamp": _utcnow().isoformat(),
    }


@router.get("/api/collab-docs/{doc_id}")
async def api_collab_doc_get(doc_id: str, user: dict = Depends(get_current_user)):
    """Get a collaborative document by ID."""
    _audit("collab_doc_get", user["user_id"], doc_id)

    manager = get_doc_manager()
    doc = manager.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check access
    if user["user_id"] not in doc.collaborators:
        # Allow read if document has no collaborators (public)
        if not doc.collaborators:
            pass  # Public document
        else:
            raise HTTPException(status_code=403, detail="Access denied")

    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "content": doc.content,
        "collaborators": doc.collaborators,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
        "language": doc.language,
        "readonly": doc.readonly,
        "versions": [
            {
                "version_id": v.version_id,
                "parent_id": v.parent_id,
                "created_at": v.created_at,
                "created_by": v.created_by,
                "message": v.message,
            }
            for v in doc.versions[-10:]  # Last 10 versions
        ],
        "syntax_tokens": tokenize_code(doc.content, doc.language)[:20],  # First 20 lines
    }


@router.websocket("/ws/collab-docs")
async def ws_collab_docs(websocket: WebSocket):
    """Real-time updates for collaborative documents (edit_applied, user_joined, user_left)."""
    await websocket.accept()
    doc_id = websocket.query_params.get("doc_id") or ""
    user_id = websocket.query_params.get("user_id") or "anonymous"
    if not doc_id:
        await websocket.close(code=4000)
        return
    _collab_broadcaster.subscribe(doc_id, websocket, user_id)
    try:
        await _collab_broadcaster.broadcast_presence(doc_id)
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _collab_broadcaster.unsubscribe(doc_id, websocket)
        await _collab_broadcaster.broadcast_presence(doc_id)


@router.put("/api/collab-docs/{doc_id}")
async def api_collab_doc_update(
    doc_id: str,
    req: DocUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """Apply an operation to a collaborative document (real-time sync)."""
    _audit("collab_doc_update", user["user_id"], f"{doc_id} op={req.op_type}")

    manager = get_doc_manager()
    doc = manager.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.readonly:
        raise HTTPException(status_code=403, detail="Document is readonly")

    # Validate collaborator access
    if user["user_id"] not in doc.collaborators and doc.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create operation
    op = DocumentOp(
        id="",
        op_type=req.op_type,
        position=req.position,
        text=req.text,
        length=req.length,
        agent_id=user["user_id"],
        timestamp=time.time(),
        version=0,
        metadata=req.metadata or {},
    )

    try:
        updated_doc, transformed_ops = manager.update_document(doc_id, user["user_id"], op)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Real-time: broadcast to other clients watching this doc
    new_version = len(updated_doc.versions)
    await _collab_broadcaster.broadcast_edit(doc_id, updated_doc.content, new_version)

    return {
        "doc_id": updated_doc.doc_id,
        "content": updated_doc.content,
        "version": op.version,
        "new_version": new_version,
        "transformed_ops": [
            {"id": t.id, "position": t.position, "text": t.text}
            for t in transformed_ops
        ],
    }


@router.post("/api/collab-docs/{doc_id}/collaborators")
async def api_collab_doc_add_collaborator(
    doc_id: str,
    req: DocCollaboratorRequest,
    user: dict = Depends(get_current_user),
):
    """Add a collaborator to the document."""
    _audit("collab_doc_add_collaborator", user["user_id"], f"{doc_id} agent={req.agent_id}")

    manager = get_doc_manager()
    doc = manager.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if req.agent_id in doc.collaborators:
        raise HTTPException(status_code=400, detail="Already a collaborator")

    manager.add_collaborator(doc_id, req.agent_id)

    return {
        "doc_id": doc_id,
        "agent_id": req.agent_id,
        "message": "Added as collaborator",
        "collaborators": doc.collaborators + [req.agent_id],
    }


@router.delete("/api/collab-docs/{doc_id}/collaborators/{agent_id}")
async def api_collab_doc_remove_collaborator(
    doc_id: str,
    agent_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove a collaborator from the document."""
    _audit("collab_doc_remove_collaborator", user["user_id"], f"{doc_id} agent={agent_id}")

    manager = get_doc_manager()
    doc = manager.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if agent_id not in doc.collaborators:
        raise HTTPException(status_code=400, detail="Not a collaborator")

    if len(doc.collaborators) == 1:
        raise HTTPException(status_code=400, detail="Cannot remove last collaborator")

    manager.remove_collaborator(doc_id, agent_id)

    return {
        "doc_id": doc_id,
        "agent_id": agent_id,
        "message": "Removed from collaborators",
        "collaborators": [a for a in doc.collaborators if a != agent_id],
    }


@router.get("/api/collab-docs/{doc_id}/history")
async def api_collab_doc_history(
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """Get document version history."""
    _audit("collab_doc_history", user["user_id"], doc_id)

    manager = get_doc_manager()
    doc = manager.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "doc_id": doc_id,
        "versions": [
            {
                "version_id": v.version_id,
                "parent_id": v.parent_id,
                "state_hash": v.state_hash,
                "created_at": v.created_at,
                "created_by": v.created_by,
                "message": v.message,
            }
            for v in doc.versions
        ],
    }


@router.post("/api/collab-docs/{doc_id}/revert")
async def api_collab_doc_revert(
    doc_id: str,
    version_id: str,
    user: dict = Depends(get_current_user),
):
    """Revert document to a previous version."""
    _audit("collab_doc_revert", user["user_id"], f"{doc_id} version={version_id}")

    manager = get_doc_manager()
    doc = manager.revert_to_version(doc_id, version_id, user["user_id"])

    if not doc:
        raise HTTPException(status_code=404, detail="Document or version not found")

    return {
        "doc_id": doc.doc_id,
        "content": doc.content,
        "current_version": doc.versions[-1].version_id,
        "tolerance": _utcnow().isoformat(),
    }


@router.delete("/api/collab-docs/{doc_id}")
async def api_collab_doc_delete(
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a collaborative document."""
    _audit("collab_doc_delete", user["user_id"], doc_id)

    manager = get_doc_manager()
    if manager.delete_document(doc_id):
        return {"deleted": doc_id, "message": "Document deleted"}
    raise HTTPException(status_code=404, detail="Document not found")


# ── Worktree Collaboration Endpoints ─────────────────────────────

class WorktreeCreateRequest(BaseModel):
    agent_id: str
    branch_name: str
    base_branch: str = "main"


class WorktreeCommitRequest(BaseModel):
    message: str


def _get_wt_manager():
    from tools.worktree_manager import get_worktree_manager
    return get_worktree_manager(".")


def _wt_to_dict(wt) -> dict:
    return {
        "path": wt.path,
        "branch": wt.branch,
        "agent_id": wt.agent_id,
        "created_at": wt.created_at.isoformat() if wt.created_at else "",
        "is_active": wt.is_active,
    }


@router.get("/api/worktrees")
async def api_list_worktrees(user: dict = Depends(get_current_user)):
    """List all active worktrees."""
    mgr = _get_wt_manager()
    return {"worktrees": [_wt_to_dict(w) for w in mgr.list_worktrees()]}


@router.post("/api/worktrees")
async def api_create_worktree(
    req: WorktreeCreateRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new worktree for an agent."""
    _audit("worktree_create", user["user_id"], f"{req.agent_id}/{req.branch_name}")
    mgr = _get_wt_manager()
    wt = mgr.create_worktree(req.agent_id, req.branch_name, req.base_branch)
    if wt is None:
        raise HTTPException(status_code=500, detail="Failed to create worktree")
    return _wt_to_dict(wt)


@router.delete("/api/worktrees/{agent_id}")
async def api_remove_worktree(
    agent_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove a worktree."""
    _audit("worktree_remove", user["user_id"], agent_id)
    mgr = _get_wt_manager()
    if not mgr.remove_worktree(agent_id):
        raise HTTPException(status_code=404, detail="Worktree not found")
    return {"removed": agent_id}


@router.post("/api/worktrees/{agent_id}/commit")
async def api_worktree_commit(
    agent_id: str,
    req: WorktreeCommitRequest,
    user: dict = Depends(get_current_user),
):
    """Commit changes in a worktree."""
    _audit("worktree_commit", user["user_id"], f"{agent_id}: {req.message[:80]}")
    mgr = _get_wt_manager()
    if not mgr.commit_changes(agent_id, req.message):
        raise HTTPException(status_code=400, detail="Commit failed or worktree not found")
    return {"committed": agent_id, "message": req.message}


@router.post("/api/worktrees/{agent_id}/merge")
async def api_worktree_merge(
    agent_id: str,
    user: dict = Depends(get_current_user),
):
    """Merge worktree branch to main."""
    _audit("worktree_merge", user["user_id"], agent_id)
    mgr = _get_wt_manager()
    if not mgr.merge_to_main(agent_id):
        raise HTTPException(status_code=400, detail="Merge failed or worktree not found")
    return {"merged": agent_id}


@router.post("/api/worktrees/{agent_id}/sync")
async def api_worktree_sync(
    agent_id: str,
    user: dict = Depends(get_current_user),
):
    """Sync worktree with main branch."""
    _audit("worktree_sync", user["user_id"], agent_id)
    mgr = _get_wt_manager()
    if not mgr.sync_with_main(agent_id):
        raise HTTPException(status_code=400, detail="Sync failed or worktree not found")
    return {"synced": agent_id}


@router.get("/api/worktrees/{agent_id}/diff")
async def api_worktree_diff(
    agent_id: str,
    user: dict = Depends(get_current_user),
):
    """Get diff for a worktree."""
    mgr = _get_wt_manager()
    diff = mgr.get_diff(agent_id)
    if diff is None:
        raise HTTPException(status_code=404, detail="Worktree not found or no diff")
    return {"agent_id": agent_id, "diff": diff}
