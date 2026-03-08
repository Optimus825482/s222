"""
Agent Communication Protocol API — EventBus, Handoff, Task Delegation endpoints.

Faz 15: Ajan-arası iletişim izleme ve yönetim API'si.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/agent-comm", tags=["Agent Communication"])


@router.get("/bus/stats")
async def bus_stats():
    """EventBus istatistikleri — kanal bazlı publish/deliver/fail sayıları."""
    try:
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        return {"ok": True, "stats": bus.get_stats()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/bus/subscriptions")
async def bus_subscriptions():
    """Aktif kanal abonelikleri — hangi agent hangi kanalda."""
    try:
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        return {"ok": True, "subscriptions": bus.get_subscriptions()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/bus/dlq")
async def bus_dlq(limit: int = 20):
    """Dead Letter Queue — teslim edilemeyen mesajlar."""
    try:
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        return {
            "ok": True,
            "dlq_size": bus.dlq.size,
            "messages": bus.dlq.peek(limit),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/bus/dlq/clear")
async def bus_dlq_clear():
    """DLQ'yu temizle."""
    try:
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        cleared = bus.dlq.clear()
        return {"ok": True, "cleared": cleared}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/handoffs")
async def active_handoffs():
    """Aktif agent handoff'ları."""
    try:
        from core.handoff import get_handoff_manager
        mgr = get_handoff_manager()
        return {
            "ok": True,
            "handoffs": mgr.get_active_handoffs(),
            "stats": mgr.get_stats(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/delegations")
async def task_delegations():
    """Aktif görev delegasyonları."""
    try:
        from core.task_delegation import get_task_delegation_manager
        mgr = get_task_delegation_manager()
        return {"ok": True, "stats": mgr.get_stats()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/delegations/{agent_role}/queue")
async def agent_task_queue(agent_role: str):
    """Belirli bir agent'ın görev kuyruğu."""
    try:
        from core.task_delegation import get_task_delegation_manager
        mgr = get_task_delegation_manager()
        return {"ok": True, "queue": mgr.get_agent_queue(agent_role)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/overview")
async def communication_overview():
    """Tüm iletişim protokolü özet dashboard'u."""
    result = {"ok": True}
    try:
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        result["bus"] = bus.get_stats()
    except Exception:
        result["bus"] = None

    try:
        from core.handoff import get_handoff_manager
        hm = get_handoff_manager()
        result["handoffs"] = hm.get_stats()
    except Exception:
        result["handoffs"] = None

    try:
        from core.task_delegation import get_task_delegation_manager
        tm = get_task_delegation_manager()
        result["delegations"] = tm.get_stats()
    except Exception:
        result["delegations"] = None

    return result
