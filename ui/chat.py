"""
Chat interface component — main interaction area.
"""

from __future__ import annotations

import streamlit as st

from config import MODELS
from core.models import EventType, Thread
from ui.theme import agent_badge_html


def render_chat_history(thread: Thread | None) -> None:
    """Render chat messages from thread events."""
    if not thread or not thread.events:
        st.markdown(
            """
            <div style="text-align:center;padding:60px 20px;color:#475569;">
                <div style="font-size:48px;margin-bottom:16px;">🧠</div>
                <div style="font-size:18px;font-weight:600;color:#94a3b8;">Multi-Agent Operations Center</div>
                <div style="font-size:14px;margin-top:8px;">
                    Qwen orchestrator ile görev gönder — specialist agent'lar çözüm üretsin.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for event in thread.events:
        if event.event_type == EventType.USER_MESSAGE:
            st.markdown(
                f'<div class="chat-msg-user">💬 {_escape(event.content)}</div>',
                unsafe_allow_html=True,
            )

        elif event.event_type == EventType.AGENT_RESPONSE:
            role = event.agent_role.value if event.agent_role else "system"
            cfg = MODELS.get(role, {})
            icon = cfg.get("icon", "🤖")
            badge = agent_badge_html(role)

            st.markdown(
                f'<div class="chat-msg-agent">{badge} {icon} {_escape(event.content)}</div>',
                unsafe_allow_html=True,
            )

        elif event.event_type == EventType.AGENT_THINKING:
            role = event.agent_role.value if event.agent_role else "agent"
            with st.expander(f"💭 {role} thinking...", expanded=False):
                st.markdown(f"```\n{event.content[:500]}\n```")

        elif event.event_type == EventType.ROUTING_DECISION:
            st.markdown(
                f'<div class="chat-msg-agent">'
                f'{agent_badge_html("orchestrator", "🧠 Routing")} '
                f'{_escape(event.content)}</div>',
                unsafe_allow_html=True,
            )

        elif event.event_type == EventType.PIPELINE_START:
            st.markdown(
                f'<div style="text-align:center;color:#3b82f6;font-size:12px;padding:4px;">'
                f'▶ {_escape(event.content)}</div>',
                unsafe_allow_html=True,
            )

        elif event.event_type == EventType.PIPELINE_COMPLETE:
            st.markdown(
                f'<div style="text-align:center;color:#10b981;font-size:12px;padding:4px;">'
                f'✅ {_escape(event.content)}</div>',
                unsafe_allow_html=True,
            )

        elif event.event_type == EventType.ERROR:
            st.markdown(
                f'<div style="background:#7f1d1d;border:1px solid #991b1b;border-radius:8px;'
                f'padding:10px;color:#fca5a5;font-size:13px;">'
                f'⚠️ {_escape(event.content)}</div>',
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
