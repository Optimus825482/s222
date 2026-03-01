"""
Chat interface — cockpit center panel.
Shows ONLY user messages + final synthesized results.
All intermediate steps (tool calls, routing, pipeline events) go to Activity Stream.
"""

from __future__ import annotations

import streamlit as st

from config import MODELS
from core.models import EventType, Thread, Task
from ui.theme import agent_badge_html
from ui.export import render_export_buttons


# Only these event types render in the center chat area
_CHAT_EVENTS = {
    EventType.USER_MESSAGE,
    EventType.AGENT_RESPONSE,
    EventType.ERROR,
}


def render_chat_history(thread: Thread | None) -> None:
    """Render clean chat — user messages + final agent responses only."""
    if not thread or not thread.events:
        st.markdown(
            """
            <div class="cockpit-welcome">
                <div style="font-size:56px;margin-bottom:16px;">🧠</div>
                <div class="cockpit-welcome-title">Multi-Agent Operations Center</div>
                <div class="cockpit-welcome-sub">
                    Görev gönder — Qwen orchestrator analiz edip specialist agent'lara yönlendirsin.
                </div>
                <div class="cockpit-welcome-hints">
                    <span class="hint-chip">🔬 Deep Research</span>
                    <span class="hint-chip">⚡ Parallel Analysis</span>
                    <span class="hint-chip">🗳️ Consensus</span>
                    <span class="hint-chip">🔁 Iterative Refine</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Collect final responses paired with their tasks for export
    task_results = {}
    for task in (thread.tasks or []):
        if task.final_result:
            task_results[task.final_result[:50]] = task

    for event in thread.events:
        if event.event_type not in _CHAT_EVENTS:
            continue

        if event.event_type == EventType.USER_MESSAGE:
            st.markdown(
                f'<div class="cockpit-msg-user">'
                f'<div class="cockpit-msg-user-label">YOU</div>'
                f'{_escape(event.content)}'
                f'</div>',
                unsafe_allow_html=True,
            )

        elif event.event_type == EventType.AGENT_RESPONSE:
            role = event.agent_role.value if event.agent_role else "system"
            cfg = MODELS.get(role, {})
            icon = cfg.get("icon", "🤖")
            color = cfg.get("color", "#6b7280")
            name = cfg.get("name", role)

            # Check if this is a final synthesized result (from orchestrator)
            is_final = role == "orchestrator" and len(event.content) > 100

            if is_final:
                st.markdown(
                    f'<div class="cockpit-msg-result">'
                    f'<div class="cockpit-msg-result-header">'
                    f'<span style="font-size:18px;">{icon}</span> '
                    f'<span style="color:{color};font-weight:700;">{name}</span>'
                    f'<span class="cockpit-result-badge">FINAL RESULT</span>'
                    f'</div>'
                    f'<div class="cockpit-msg-result-body">{_escape(event.content)}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                # Export buttons for final results
                matched_task = task_results.get(event.content[:50])
                render_export_buttons(event.content, matched_task)
            else:
                badge = agent_badge_html(role)
                st.markdown(
                    f'<div class="cockpit-msg-agent">'
                    f'{badge} {icon} {_escape(event.content)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        elif event.event_type == EventType.ERROR:
            st.markdown(
                f'<div class="cockpit-msg-error">'
                f'⚠️ {_escape(event.content)}'
                f'</div>',
                unsafe_allow_html=True,
            )


def _escape(text: str) -> str:
    """Basic HTML escape for safe rendering."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
