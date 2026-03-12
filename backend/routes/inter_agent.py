"""
Inter-Agent Monitor API — Messages, Knowledge, Status endpoints.

Frontend inter-agent-monitor-panel.tsx bu endpoint'leri kullanır.
EventBus middleware ile geçen mesajları yakalar, in-memory store tutar.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/inter-agent", tags=["Inter-Agent Monitor"])

# ── In-Memory Stores ─────────────────────────────────────────────

_message_history: deque[dict[str, Any]] = deque(maxlen=200)
_shared_knowledge: dict[str, dict[str, Any]] = {}

# ── Middleware for EventBus ──────────────────────────────────────

_middleware_installed = False


def _install_bus_middleware():
    """EventBus'a middleware ekleyerek geçen mesajları yakala."""
    global _middleware_installed
    if _middleware_installed:
        return
    try:
        from core.event_bus import get_event_bus
        from core.protocols import MessageEnvelope

        bus = get_event_bus()

        async def capture_middleware(msg: MessageEnvelope) -> MessageEnvelope:
            _message_history.append({
                "id": msg.id,
                "from_agent": msg.source_agent,
                "to_agent": msg.target_agent or "broadcast",
                "message_type": msg.message_type.value if hasattr(msg.message_type, "value") else str(msg.message_type),
                "content": msg.payload.get("content", msg.payload.get("description", str(msg.payload)[:200])),
                "priority": msg.priority.value if hasattr(msg.priority, "value") else int(msg.priority),
                "requires_response": msg.correlation_id is not None,
                "created_at": msg.timestamp.isoformat(),
            })
            return msg  # pass-through

        bus.add_middleware(capture_middleware)
        _middleware_installed = True
    except Exception:
        pass  # EventBus not ready yet — will retry on next request


# ── Helper ───────────────────────────────────────────────────────

AGENT_ROLES = ["orchestrator", "thinker", "researcher", "speed", "reasoner", "critic"]


def _get_agent_statuses() -> list[dict[str, Any]]:
    """Mevcut agent durumlarını EventBus subscription + AgentMessageBus'tan derle."""
    statuses = []
    try:
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        subs = bus.get_subscriptions()  # channel → [agent_roles]
        active_agents = set()
        for agents in subs.values():
            active_agents.update(agents)
    except Exception:
        active_agents = set()

    # Count pending messages per agent from DLQ
    pending_counts: dict[str, int] = {r: 0 for r in AGENT_ROLES}
    try:
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        dlq_msgs = bus.dlq.peek(100)
        for m in dlq_msgs:
            target = m.get("target_agent", "")
            if target in pending_counts:
                pending_counts[target] += 1
    except Exception:
        pass

    # Also add Faz 16 AgentMessageBus pending counts
    try:
        from tools.inter_agent_comm import get_message_bus
        msg_bus = get_message_bus()
        for role in AGENT_ROLES:
            pending_counts[role] += msg_bus.get_pending_count(role)
            # If agent has a queue in AgentMessageBus, consider it active
            if role in msg_bus._queues:
                active_agents.add(role)
    except Exception:
        pass

    for role in AGENT_ROLES:
        statuses.append({
            "agent_role": role,
            "pending_messages": pending_counts.get(role, 0),
            "status": "healthy" if role in active_agents else "idle",
        })
    return statuses


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/messages")
async def get_messages(limit: int = 50):
    """Agent-arası mesaj geçmişi — merges EventBus + AgentMessageBus."""
    _install_bus_middleware()

    # Source 1: EventBus middleware captured messages
    eventbus_msgs = list(_message_history)

    # Source 2: Faz 16 AgentMessageBus history
    try:
        from tools.inter_agent_comm import get_message_bus
        bus = get_message_bus()
        faz16_msgs = bus.get_history(limit=limit)
    except Exception:
        faz16_msgs = []

    # Merge & dedup by id
    seen_ids: set[str] = set()
    merged: list[dict[str, Any]] = []
    for msg in eventbus_msgs:
        mid = msg.get("id", "")
        if mid and mid in seen_ids:
            continue
        seen_ids.add(mid)
        merged.append(msg)
    for msg in faz16_msgs:
        mid = msg.get("id", "")
        if mid and mid in seen_ids:
            continue
        seen_ids.add(mid)
        merged.append(msg)

    # Sort newest first
    merged.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    merged = merged[:limit]
    return {"messages": merged}


@router.get("/knowledge")
async def get_knowledge():
    """Paylaşılan bilgi havuzu — merges EventBus store + AgentMessageBus."""
    _install_bus_middleware()

    # Source 1: EventBus middleware knowledge
    knowledge_list: list[dict[str, Any]] = list(_shared_knowledge.values())
    seen_keys: set[str] = {e.get("key", "") for e in knowledge_list}

    # Source 2: Faz 16 AgentMessageBus knowledge
    try:
        from tools.inter_agent_comm import get_message_bus
        bus = get_message_bus()
        for key, value in bus.get_all_knowledge().items():
            if key in seen_keys:
                continue
            seen_keys.add(key)
            knowledge_list.append({
                "key": key,
                "value": value,
                "source_agent": "agent",
                "tags": [],
                "created_at": "",
            })
    except Exception:
        pass

    return {"knowledge": knowledge_list}


@router.get("/status")
async def get_status():
    """Agent durumları ve genel istatistikler — merges both sources."""
    _install_bus_middleware()
    agents = _get_agent_statuses()
    active_count = sum(1 for a in agents if a["status"] == "healthy")

    # EventBus counts
    eventbus_msg_count = len(_message_history)
    eventbus_knowledge_count = len(_shared_knowledge)

    # Faz 16 AgentMessageBus counts
    try:
        from tools.inter_agent_comm import get_message_bus
        bus = get_message_bus()
        faz16_msg_count = len(bus.get_history(limit=10000))
        faz16_knowledge_count = len(bus.get_all_knowledge())
    except Exception:
        faz16_msg_count = 0
        faz16_knowledge_count = 0

    return {
        "agents": agents,
        "total_messages": eventbus_msg_count + faz16_msg_count,
        "total_knowledge": eventbus_knowledge_count + faz16_knowledge_count,
        "active_agents": active_count,
    }


# ── Knowledge Management ────────────────────────────────────────

@router.post("/knowledge")
async def share_knowledge(data: dict[str, Any]):
    """Agent'lar arası bilgi paylaşımı."""
    key = data.get("key", f"k_{uuid.uuid4().hex[:8]}")
    entry = {
        "key": key,
        "value": data.get("value", ""),
        "source_agent": data.get("source_agent", "unknown"),
        "tags": data.get("tags", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _shared_knowledge[key] = entry
    return {"ok": True, "key": key}
