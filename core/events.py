"""
Event serialization — 12-Factor #3: Own your context window.
XML-style serialization for token-efficient LLM context building.
"""

from __future__ import annotations

from .models import Event, EventType, Thread


def serialize_event(event: Event) -> str:
    """Serialize a single event to XML-style string for LLM context."""
    tag = event.event_type.value
    if event.agent_role:
        tag = f"{event.agent_role.value}_{tag}"

    meta_lines = ""
    if event.metadata:
        skip = {"tokens", "thinking_content"}
        meta_lines = "\n".join(
            f"  {k}: {v}" for k, v in event.metadata.items() if k not in skip
        )
        if meta_lines:
            meta_lines = "\n" + meta_lines

    return f"<{tag}>\n  {event.content}{meta_lines}\n</{tag}>"


def serialize_thread_for_llm(
    thread: Thread,
    max_events: int = 50,
    include_types: set[EventType] | None = None,
) -> str:
    """
    Build full context window string from thread events.
    Filters by type and caps at max_events for token budget.
    """
    events = thread.events[-max_events:]
    if include_types:
        events = [e for e in events if e.event_type in include_types]
    return "\n\n".join(serialize_event(e) for e in events)


def build_orchestrator_context(thread: Thread) -> str:
    """Full context for orchestrator — sees everything."""
    return serialize_thread_for_llm(thread, max_events=40)


def build_specialist_context(thread: Thread, task_description: str) -> str:
    """Focused context for specialist — only relevant events + task."""
    relevant_types = {
        EventType.USER_MESSAGE,
        EventType.ROUTING_DECISION,
        EventType.TOOL_RESULT,
        EventType.SYNTHESIS,
        EventType.ERROR,
    }
    history = serialize_thread_for_llm(thread, max_events=15, include_types=relevant_types)
    return f"{history}\n\n<current_task>\n  {task_description}\n</current_task>"
