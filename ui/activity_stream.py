"""
Unified Activity Stream — right column cockpit panel.
Combines tool calls, agent steps, pipeline events into a single live feed.
Replaces the old tool_stream + a2a_stream separation.
"""

from __future__ import annotations

import streamlit as st

from config import MODELS
from core.models import EventType, Thread
from ui.theme import AGENT_COLORS


# Events to show in activity stream (everything except user messages and final responses)
_ACTIVITY_EVENTS = {
    EventType.ROUTING_DECISION,
    EventType.AGENT_START,
    EventType.AGENT_THINKING,
    EventType.TOOL_CALL,
    EventType.TOOL_RESULT,
    EventType.PIPELINE_START,
    EventType.PIPELINE_STEP,
    EventType.PIPELINE_COMPLETE,
    EventType.SYNTHESIS,
    EventType.ERROR,
}

# Event type display config
_EVENT_CONFIG = {
    EventType.ROUTING_DECISION: ("🧭", "Routing", "#ec4899"),
    EventType.AGENT_START:      ("🚀", "Start", "#3b82f6"),
    EventType.AGENT_THINKING:   ("💭", "Thinking", "#a78bfa"),
    EventType.TOOL_CALL:        ("🔧", "Tool", "#f59e0b"),
    EventType.TOOL_RESULT:      ("📋", "Result", "#10b981"),
    EventType.PIPELINE_START:   ("▶️", "Pipeline", "#3b82f6"),
    EventType.PIPELINE_STEP:    ("⏩", "Step", "#06b6d4"),
    EventType.PIPELINE_COMPLETE:("✅", "Done", "#10b981"),
    EventType.SYNTHESIS:        ("🔗", "Synthesis", "#8b5cf6"),
    EventType.ERROR:            ("⚠️", "Error", "#ef4444"),
}


def render_activity_stream(thread: Thread | None) -> None:
    """Render unified activity stream for the right cockpit column."""
    # Header
    st.markdown(
        '<div class="activity-header">'
        '<span style="font-size:18px;">📡</span> '
        '<span>Activity Stream</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not thread or not thread.events:
        st.markdown(
            '<div class="activity-empty">Agent aktivitesi bekleniyor...</div>',
            unsafe_allow_html=True,
        )
        return

    # Filter activity events
    activity = [e for e in thread.events if e.event_type in _ACTIVITY_EVENTS]

    if not activity:
        st.markdown(
            '<div class="activity-empty">Agent aktivitesi bekleniyor...</div>',
            unsafe_allow_html=True,
        )
        return

    # Stats bar
    tool_count = sum(1 for e in activity if e.event_type == EventType.TOOL_CALL)
    agent_count = len({e.agent_role.value for e in activity if e.agent_role})
    error_count = sum(1 for e in activity if e.event_type == EventType.ERROR)

    st.markdown(
        f'<div class="activity-stats">'
        f'<span>🔧 {tool_count}</span>'
        f'<span>🤖 {agent_count}</span>'
        f'<span>{"⚠️ " + str(error_count) if error_count else "✅ 0"}</span>'
        f'<span>📊 {len(activity)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Render events (newest first), max 30
    recent = list(reversed(activity[-30:]))
    html_parts = ['<div class="activity-feed">']

    for ev in recent:
        icon, label, accent = _EVENT_CONFIG.get(
            ev.event_type, ("📌", "Event", "#6b7280")
        )
        agent = ev.agent_role.value if ev.agent_role else "system"
        cfg = MODELS.get(agent, {})
        agent_icon = cfg.get("icon", "⚙️")
        agent_color = cfg.get("color", "#6b7280")

        content = ev.content[:160]
        content_safe = (
            content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        # Different styling per event type
        if ev.event_type == EventType.TOOL_CALL:
            html_parts.append(
                f'<div class="activity-item activity-tool" style="border-left-color:{accent};">'
                f'<div class="activity-item-header">'
                f'<span>{icon} <b style="color:{accent};">{label}</b></span>'
                f'<span class="activity-agent" style="color:{agent_color};">{agent_icon} {agent}</span>'
                f'</div>'
                f'<div class="activity-item-body">{content_safe}</div>'
                f'</div>'
            )
        elif ev.event_type == EventType.TOOL_RESULT:
            html_parts.append(
                f'<div class="activity-item activity-result">'
                f'<div class="activity-item-body" style="color:#6ee7b7;">'
                f'{icon} {content_safe[:100]}</div>'
                f'</div>'
            )
        elif ev.event_type == EventType.ERROR:
            html_parts.append(
                f'<div class="activity-item activity-error">'
                f'{icon} <span style="color:#fca5a5;">{content_safe}</span>'
                f'</div>'
            )
        elif ev.event_type == EventType.ROUTING_DECISION:
            html_parts.append(
                f'<div class="activity-item activity-routing">'
                f'<div class="activity-item-header">'
                f'{icon} <b style="color:{accent};">Routing</b>'
                f'</div>'
                f'<div class="activity-item-body">{content_safe}</div>'
                f'</div>'
            )
        elif ev.event_type in (EventType.PIPELINE_START, EventType.PIPELINE_COMPLETE):
            html_parts.append(
                f'<div class="activity-item activity-pipeline">'
                f'{icon} {content_safe}'
                f'</div>'
            )
        else:
            html_parts.append(
                f'<div class="activity-item" style="border-left-color:{accent};">'
                f'<div class="activity-item-header">'
                f'<span>{icon} {label}</span>'
                f'<span class="activity-agent" style="color:{agent_color};">{agent_icon}</span>'
                f'</div>'
                f'<div class="activity-item-body">{content_safe}</div>'
                f'</div>'
            )

    html_parts.append('</div>')
    st.markdown("\n".join(html_parts), unsafe_allow_html=True)
