"""
Tool Activity Stream — right panel showing real-time tool usage.
Displays web_search, web_fetch, find_skill, use_skill calls with details.
"""

from __future__ import annotations

import streamlit as st

from config import MODELS
from core.models import EventType, Thread
from ui.theme import AGENT_COLORS


# Tool type → icon + color mapping
TOOL_ICONS = {
    "web_search": ("🔍", "#3b82f6"),
    "web_fetch": ("🌐", "#8b5cf6"),
    "find_skill": ("🎯", "#f59e0b"),
    "use_skill": ("⚡", "#10b981"),
    "decompose_task": ("🧩", "#ec4899"),
    "direct_response": ("💬", "#6b7280"),
    "synthesize_results": ("🔗", "#06b6d4"),
}


def _parse_tool_name(content: str) -> str:
    """Extract tool name from event content like 'web_search({...})'."""
    paren = content.find("(")
    if paren > 0:
        return content[:paren].strip()
    return content.split()[0] if content else "unknown"


def _parse_tool_args(content: str) -> str:
    """Extract tool arguments preview from event content."""
    paren = content.find("(")
    if paren > 0:
        args = content[paren + 1:].rstrip(")")
        return args[:150] + ("..." if len(args) > 150 else "")
    return ""


def render_tool_stream(thread: Thread | None) -> None:
    """Render the tool activity stream panel."""
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <span style="font-size:20px;">🔧</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;">Tool Activity</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not thread or not thread.events:
        st.markdown(
            '<div style="color:#475569;font-size:13px;text-align:center;padding:20px;">'
            'Henüz tool kullanımı yok</div>',
            unsafe_allow_html=True,
        )
        return

    # Filter tool-related events (calls + results)
    tool_events = [
        e for e in thread.events
        if e.event_type in (EventType.TOOL_CALL, EventType.TOOL_RESULT)
    ]

    if not tool_events:
        st.markdown(
            '<div style="color:#475569;font-size:13px;text-align:center;padding:20px;">'
            'Henüz tool kullanımı yok</div>',
            unsafe_allow_html=True,
        )
        return

    # Pair tool calls with their results
    entries = []
    i = 0
    while i < len(tool_events):
        ev = tool_events[i]
        if ev.event_type == EventType.TOOL_CALL:
            tool_name = _parse_tool_name(ev.content)
            tool_args = _parse_tool_args(ev.content)
            agent = ev.agent_role.value if ev.agent_role else "system"

            # Look for matching result
            result_preview = ""
            if i + 1 < len(tool_events) and tool_events[i + 1].event_type == EventType.TOOL_RESULT:
                result_preview = tool_events[i + 1].content[:200]
                i += 1

            entries.append({
                "tool": tool_name,
                "args": tool_args,
                "agent": agent,
                "result": result_preview,
                "timestamp": ev.timestamp,
            })
        i += 1

    # Render entries in reverse (newest first)
    for entry in reversed(entries):
        _render_tool_entry(entry)


def _render_tool_entry(entry: dict) -> None:
    """Render a single tool activity entry."""
    tool = entry["tool"]
    agent = entry["agent"]
    args = entry["args"]
    result = entry["result"]

    icon, color = TOOL_ICONS.get(tool, ("🔧", "#6b7280"))
    agent_fg, agent_bg = AGENT_COLORS.get(agent, ("#94a3b8", "#1f2937"))

    # Agent config for icon
    from config import MODELS
    agent_cfg = MODELS.get(agent, {})
    agent_icon = agent_cfg.get("icon", "🤖")

    # Escape HTML
    args_safe = (
        args.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    result_safe = (
        result.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace("\n", "<br>")
    ) if result else ""

    # Build the card
    result_html = ""
    if result_safe:
        result_html = (
            f'<div class="tool-result">'
            f'<div style="font-size:10px;color:#6b7280;margin-bottom:2px;">RESULT</div>'
            f'{result_safe}'
            f'</div>'
        )

    st.markdown(
        f"""
        <div class="tool-entry" style="border-left:3px solid {color};">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-size:14px;">{icon}</span>
                    <span style="font-size:13px;font-weight:600;color:{color};">{tool}</span>
                </div>
                <span class="agent-badge" style="background:{agent_bg};color:{agent_fg};font-size:10px;padding:1px 6px;border-radius:6px;">
                    {agent_icon} {agent}
                </span>
            </div>
            <div class="tool-args">{args_safe}</div>
            {result_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
