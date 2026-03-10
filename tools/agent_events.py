"""
Agent Events — Inspired by pi-mom's event system.

Three event types adapted for multi-agent:
- Immediate: triggers instantly (webhooks, external signals)
- One-shot: triggers at a specific time, then auto-deletes
- Periodic: triggers on cron schedule, persists until deleted

Unlike mom's file-based approach, we use PostgreSQL + in-memory scheduling
to integrate with our existing scheduled_tasks infrastructure.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class AgentEventType(str, Enum):
    IMMEDIATE = "immediate"
    ONE_SHOT = "one-shot"
    PERIODIC = "periodic"


class AgentEvent:
    """An event that can wake up an agent."""

    def __init__(
        self,
        event_type: AgentEventType,
        target_agent: str,
        message: str,
        schedule: str | None = None,
        trigger_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        event_id: str | None = None,
        created_by: str | None = None,
    ):
        self.id = event_id or f"evt-{uuid.uuid4().hex[:8]}"
        self.event_type = event_type
        self.target_agent = target_agent
        self.message = message
        self.schedule = schedule          # cron expr for periodic
        self.trigger_at = trigger_at      # datetime for one-shot
        self.metadata = metadata or {}
        self.created_by = created_by
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "target_agent": self.target_agent,
            "message": self.message,
            "schedule": self.schedule,
            "trigger_at": self.trigger_at.isoformat() if self.trigger_at else None,
            "metadata": self.metadata,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }


# ── Event Manager ────────────────────────────────────────────────

# Max events per agent (like mom's 5 per channel)
MAX_EVENTS_PER_AGENT = 10

# Registered event handlers: agent_role -> async callback
_handlers: dict[str, Callable[[AgentEvent], Awaitable[str]]] = {}

# In-memory event queue (immediate events)
_immediate_queue: list[AgentEvent] = []

# Active events registry
_active_events: dict[str, AgentEvent] = {}


def register_event_handler(
    agent_role: str,
    handler: Callable[[AgentEvent], Awaitable[str]],
) -> None:
    """Register a handler for when an agent receives an event."""
    _handlers[agent_role] = handler
    logger.info("[AgentEvents] Registered handler for %s", agent_role)


def create_event(
    event_type: AgentEventType,
    target_agent: str,
    message: str,
    schedule: str | None = None,
    trigger_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> AgentEvent:
    """
    Create an agent event.

    - immediate: queued for next processing cycle
    - one-shot: scheduled for trigger_at, auto-deleted after
    - periodic: scheduled on cron, persists until deleted
    """
    # Check per-agent limit
    agent_events = [
        e for e in _active_events.values()
        if e.target_agent == target_agent
    ]
    if len(agent_events) >= MAX_EVENTS_PER_AGENT:
        raise ValueError(
            f"Agent '{target_agent}' has {MAX_EVENTS_PER_AGENT} events (max). "
            "Delete some before creating new ones."
        )

    event = AgentEvent(
        event_type=event_type,
        target_agent=target_agent,
        message=message,
        schedule=schedule,
        trigger_at=trigger_at,
        metadata=metadata,
        created_by=created_by,
    )

    if event_type == AgentEventType.IMMEDIATE:
        _immediate_queue.append(event)
        logger.info("[AgentEvents] Immediate event queued for %s", target_agent)
    else:
        _active_events[event.id] = event
        _persist_event_to_scheduler(event)
        logger.info(
            "[AgentEvents] %s event '%s' created for %s",
            event_type.value, event.id, target_agent,
        )

    return event


def delete_event(event_id: str) -> bool:
    """Delete an event by ID."""
    if event_id in _active_events:
        del _active_events[event_id]
        logger.info("[AgentEvents] Deleted event %s", event_id)
        return True
    return False


def list_events(
    target_agent: str | None = None,
    event_type: AgentEventType | None = None,
) -> list[dict[str, Any]]:
    """List active events with optional filters."""
    results = []
    for event in _active_events.values():
        if target_agent and event.target_agent != target_agent:
            continue
        if event_type and event.event_type != event_type:
            continue
        results.append(event.to_dict())
    return results


async def process_immediate_events() -> list[dict[str, Any]]:
    """Process all queued immediate events. Returns results."""
    global _immediate_queue
    if not _immediate_queue:
        return []

    batch = _immediate_queue[:]
    _immediate_queue = []
    results = []

    for event in batch:
        handler = _handlers.get(event.target_agent)
        if handler:
            try:
                response = await handler(event)
                results.append({
                    "event_id": event.id,
                    "agent": event.target_agent,
                    "response": response,
                    "status": "completed",
                })
            except Exception as e:
                results.append({
                    "event_id": event.id,
                    "agent": event.target_agent,
                    "response": str(e),
                    "status": "error",
                })
        else:
            results.append({
                "event_id": event.id,
                "agent": event.target_agent,
                "response": "No handler registered",
                "status": "skipped",
            })

    return results


def _persist_event_to_scheduler(event: AgentEvent) -> None:
    """
    Bridge to existing scheduled_tasks system.
    Converts agent events to scheduled tasks for execution.
    """
    try:
        from tools.scheduled_tasks import get_scheduled_task_scheduler, TaskType
        import asyncio

        scheduler = get_scheduled_task_scheduler()

        if event.event_type == AgentEventType.PERIODIC and event.schedule:
            # Create a periodic scheduled task
            asyncio.create_task(scheduler.create_task(
                name=f"agent-event:{event.id}",
                task_type=TaskType.AGENT_EVENT,
                cron_expr=event.schedule,
                handler_ref="agent_event_handler",
                params={
                    "event_id": event.id,
                    "target_agent": event.target_agent,
                    "message": event.message,
                    "metadata": event.metadata,
                },
                tags=["agent-event", event.target_agent],
                task_id=event.id,
            ))
        elif event.event_type == AgentEventType.ONE_SHOT and event.trigger_at:
            # Convert to cron-like one-shot via scheduler
            asyncio.create_task(scheduler.create_task(
                name=f"agent-event:{event.id}",
                task_type=TaskType.AGENT_EVENT,
                cron_expr=_datetime_to_cron(event.trigger_at),
                handler_ref="agent_event_handler",
                params={
                    "event_id": event.id,
                    "target_agent": event.target_agent,
                    "message": event.message,
                    "metadata": event.metadata,
                    "one_shot": True,
                },
                tags=["agent-event", "one-shot", event.target_agent],
                task_id=event.id,
            ))
    except Exception as e:
        logger.warning("[AgentEvents] Could not persist to scheduler: %s", e)


def _datetime_to_cron(dt: datetime) -> str:
    """Convert a datetime to a cron expression (minute hour day month *)."""
    return f"{dt.minute} {dt.hour} {dt.day} {dt.month} *"


def get_event_stats() -> dict[str, Any]:
    """Get event system statistics."""
    by_agent: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for event in _active_events.values():
        by_agent[event.target_agent] = by_agent.get(event.target_agent, 0) + 1
        by_type[event.event_type.value] = by_type.get(event.event_type.value, 0) + 1

    return {
        "total_active": len(_active_events),
        "immediate_queued": len(_immediate_queue),
        "by_agent": by_agent,
        "by_type": by_type,
    }
