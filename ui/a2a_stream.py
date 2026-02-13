"""
Agent-to-Agent (A2A) Communication Stream — sidebar component.
Shows live inter-agent delegation, handoffs, and conversations.
"""

from __future__ import annotations

import streamlit as st

from config import MODELS
from core.models import EventType, Thread
from ui.theme import AGENT_COLORS


# Event types that represent A2A communication
A2A_EVENT_TYPES = {
    EventType.ROUTING_DECISION,
    EventType.PIPELINE_START,
    EventType.PIPELINE_STEP,
    EventType.PIPELINE_COMPLETE,
    EventType.AGENT_START,
    EventType.AGENT_RESPONSE,
    EventType.TOOL_CALL,
    EventType.TOOL_RESULT,
    EventType.SYNTHESIS,
}

# Friendly labels for event types
EVENT_LABELS = {
    EventType.ROUTING_DECISION: ("🧭", "Routing"),
    EventType.PIPELINE_START: ("▶️", "Pipeline Start"),
    EventType.PIPELINE_STEP: ("⏩", "Pipeline Step"),
    EventType.PIPELINE_COMPLETE: ("✅", "Pipeline Done"),
    EventType.AGENT_START: ("🚀", "Agent Start"),
    EventType.AGENT_RESPONSE: ("💬", "Response"),
    EventType.TOOL_CALL: ("🔧", "Tool Call"),
    EventType.TOOL_RESULT: ("📋", "Tool Result"),
    EventType.SYNTHESIS: ("🔗", "Synthesis"),
}


def render_a2a_stream(thread: Thread | None) -> None:
    """Render agent-to-agent communication stream in sidebar."""
    st.markdown(
        '<div style="display:flex;align-items:center;gap:8px;margin:8px 0;">'
        '<span style="font-size:16px;">🔄</span>'
        '<span style="font-size:14px;font-weight:700;color:#e2e8f0;">A2A Live Stream</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not thread or not thread.events:
        st.markdown(
            '<div style="color:#475569;font-size:12px;text-align:center;padding:12px;">'
            'Agent iletişimi bekleniyor...</div>',
            unsafe_allow_html=True,
        )
        return

    # Filter A2A events
    a2a_events = [
        e for e in thread.events
        if e.event_type in A2A_EVENT_TYPES
    ]

    if not a2a_events:
        st.markdown(
            '<div style="color:#475569;font-size:12px;text-align:center;padding:12px;">'
            'Agent iletişimi bekleniyor...</div>',
            unsafe_allow_html=True,
        )
        return

    # Show last N events (newest at top)
    max_display = 15
    recent = list(reversed(a2a_events[-max_display:]))

    # Build the stream HTML
    html_parts = ['<div class="a2a-stream">']

    prev_agent = None
    for ev in recent:
        agent = ev.agent_role.value if ev.agent_role else "system"
        icon_ev, label = EVENT_LABELS.get(ev.event_type, ("📌", "Event"))

        # Agent info
        agent_cfg = MODELS.get(agent, {})
        agent_icon = agent_cfg.get("icon", "⚙️")
        agent_color = agent_cfg.get("color", "#6b7280")

        # Show delegation arrow when agent changes
        arrow_html = ""
        if prev_agent and prev_agent != agent and ev.event_type not in (
            EventType.TOOL_RESULT, EventType.PIPELINE_COMPLETE
        ):
            prev_cfg = MODELS.get(prev_agent, {})
            prev_icon = prev_cfg.get("icon", "⚙️")
            prev_color = prev_cfg.get("color", "#6b7280")
            arrow_html = (
                f'<div class="a2a-arrow">'
                f'<span style="color:{prev_color};">{prev_icon}</span>'
                f' → '
                f'<span style="color:{agent_color};">{agent_icon}</span>'
                f'</div>'
            )

        # Content preview (truncated)
        content = ev.content[:120]
        content_safe = (
            content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        # Event type specific styling
        if ev.event_type == EventType.ROUTING_DECISION:
            border_color = "#ec4899"
        elif ev.event_type == EventType.PIPELINE_START:
            border_color = "#3b82f6"
        elif ev.event_type == EventType.PIPELINE_COMPLETE:
            border_color = "#10b981"
        elif ev.event_type == EventType.TOOL_CALL:
            border_color = "#f59e0b"
        elif ev.event_type == EventType.AGENT_RESPONSE:
            border_color = agent_color
        else:
            border_color = "#374151"

        html_parts.append(arrow_html)
        html_parts.append(
            f'<div class="a2a-entry" style="border-left:2px solid {border_color};">'
            f'  <div style="display:flex;justify-content:space-between;align-items:center;">'
            f'    <span style="font-size:11px;">'
            f'      <span style="color:{agent_color};">{agent_icon}</span> '
            f'      {icon_ev} <span style="color:#94a3b8;">{label}</span>'
            f'    </span>'
            f'  </div>'
            f'  <div class="a2a-content">{content_safe}</div>'
            f'</div>'
        )

        prev_agent = agent

    html_parts.append('</div>')
    st.markdown("\n".join(html_parts), unsafe_allow_html=True)


def render_agent_status_live(thread: Thread | None) -> None:
    """Render compact live agent status indicators."""
    if not thread:
        return

    # Determine which agents are currently active based on recent events
    active_agents = set()
    if thread.events:
        # Check last 5 events for active agents
        for ev in thread.events[-5:]:
            if ev.agent_role:
                active_agents.add(ev.agent_role.value)

    # Render compact status row
    cols_html = []
    for key, cfg in MODELS.items():
        icon = cfg["icon"]
        color = cfg["color"]
        is_active = key in active_agents
        has_metrics = key in thread.agent_metrics

        if is_active:
            status_dot = f'<span style="color:#10b981;">●</span>'
            glow = f"box-shadow: 0 0 8px {color}40;"
        elif has_metrics:
            status_dot = f'<span style="color:#3b82f6;">●</span>'
            glow = ""
        else:
            status_dot = f'<span style="color:#374151;">○</span>'
            glow = ""

        cols_html.append(
            f'<div class="agent-status-dot" style="border-color:{color};{glow}">'
            f'  {icon} {status_dot}'
            f'</div>'
        )

    st.markdown(
        '<div style="display:flex;gap:6px;justify-content:center;margin:8px 0;">'
        + "".join(cols_html)
        + '</div>',
        unsafe_allow_html=True,
    )
