"""
Live Activity Monitor — realtime progress during task execution.
Uses Streamlit st.status() + st.empty() for live updates.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from config import MODELS
from ui.theme import AGENT_COLORS


@dataclass
class LiveEvent:
    """Single live event for the monitor."""
    timestamp: float
    event_type: str  # agent_start, tool_call, tool_result, thinking, response, pipeline, error
    agent: str
    content: str
    extra: dict = field(default_factory=dict)


class LiveMonitor:
    """
    Realtime activity monitor that updates Streamlit containers
    during async execution. Thread-safe via st.session_state.
    """

    def __init__(self):
        if "live_events" not in st.session_state:
            st.session_state.live_events = []
        if "stop_requested" not in st.session_state:
            st.session_state.stop_requested = False

        self._status_container = None
        self._progress_area = None
        self._step_counter = 0

    def start(self, task_description: str):
        """Initialize the live monitor UI containers."""
        st.session_state.live_events = []
        st.session_state.stop_requested = False
        self._step_counter = 0

        self._status_container = st.status(
            f"🧠 İşleniyor: {task_description[:60]}...",
            expanded=True,
        )
        return self

    def should_stop(self) -> bool:
        """Check if user requested stop."""
        return st.session_state.get("stop_requested", False)

    def emit(self, event_type: str, agent: str, content: str, **extra):
        """Emit a live event and update UI."""
        event = LiveEvent(
            timestamp=time.time(),
            event_type=event_type,
            agent=agent,
            content=content,
            extra=extra,
        )
        # Store as dict for Streamlit session_state serialization safety
        st.session_state.live_events.append({
            "timestamp": event.timestamp,
            "event_type": event.event_type,
            "agent": event.agent,
            "content": event.content,
            "extra": event.extra,
        })
        self._step_counter += 1
        self._render_event(event)

    def complete(self, summary: str = ""):
        """Mark execution as complete."""
        if self._status_container:
            self._status_container.update(
                label=f"✅ Tamamlandı — {summary[:80]}" if summary else "✅ Tamamlandı",
                state="complete",
                expanded=False,
            )

    def error(self, message: str):
        """Mark execution as failed."""
        if self._status_container:
            self._status_container.update(
                label=f"❌ Hata: {message[:80]}",
                state="error",
                expanded=True,
            )

    def _render_event(self, event: LiveEvent):
        """Render a single event inside the status container."""
        if not self._status_container:
            return

        with self._status_container:
            cfg = MODELS.get(event.agent, {})
            icon = cfg.get("icon", "⚙️")
            color = cfg.get("color", "#6b7280")

            if event.event_type == "agent_start":
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
                    f'<span style="font-size:16px;">{icon}</span>'
                    f'<span style="color:{color};font-weight:600;font-size:13px;">'
                    f'{cfg.get("name", event.agent)}</span>'
                    f'<span style="color:#6b7280;font-size:12px;">başlatıldı</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            elif event.event_type == "tool_call":
                tool_name = event.extra.get("tool_name", "")
                tool_icon = _tool_icon(tool_name)
                st.markdown(
                    f'<div style="background:#0f1729;border-left:3px solid {color};'
                    f'border-radius:6px;padding:6px 10px;margin:3px 0;font-size:12px;">'
                    f'{tool_icon} <span style="color:#60a5fa;font-weight:600;">{tool_name}</span>'
                    f' <span style="color:#475569;">by</span> {icon}'
                    f'<div style="color:#94a3b8;font-size:11px;margin-top:2px;">'
                    f'{_escape(event.content[:120])}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            elif event.event_type == "tool_result":
                st.markdown(
                    f'<div style="color:#6ee7b7;font-size:11px;padding:2px 10px;'
                    f'border-left:3px solid #064e3b;margin:2px 0;">'
                    f'📋 {_escape(event.content[:150])}</div>',
                    unsafe_allow_html=True,
                )

            elif event.event_type == "thinking":
                st.markdown(
                    f'<div style="color:#a78bfa;font-size:11px;padding:2px 10px;">'
                    f'💭 {icon} düşünüyor...</div>',
                    unsafe_allow_html=True,
                )

            elif event.event_type == "response":
                st.markdown(
                    f'<div style="color:#e2e8f0;font-size:12px;padding:4px 10px;'
                    f'border-left:3px solid {color};margin:3px 0;">'
                    f'{icon} <span style="color:{color};font-weight:600;">'
                    f'{cfg.get("name", event.agent)}</span> yanıtladı'
                    f'<div style="color:#94a3b8;font-size:11px;margin-top:2px;">'
                    f'{_escape(event.content[:200])}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            elif event.event_type == "pipeline":
                st.markdown(
                    f'<div style="text-align:center;color:#3b82f6;font-size:12px;'
                    f'padding:4px;border:1px dashed #1e3a5f;border-radius:6px;margin:4px 0;">'
                    f'🔄 {_escape(event.content)}</div>',
                    unsafe_allow_html=True,
                )

            elif event.event_type == "routing":
                st.markdown(
                    f'<div style="background:#1a0a2e;border:1px solid #7c3aed;'
                    f'border-radius:6px;padding:6px 10px;margin:4px 0;font-size:12px;">'
                    f'🧭 <span style="color:#c084fc;font-weight:600;">Routing:</span> '
                    f'{_escape(event.content)}</div>',
                    unsafe_allow_html=True,
                )

            elif event.event_type == "error":
                st.markdown(
                    f'<div style="background:#7f1d1d;border:1px solid #991b1b;'
                    f'border-radius:6px;padding:6px 10px;margin:3px 0;'
                    f'color:#fca5a5;font-size:12px;">'
                    f'⚠️ {_escape(event.content[:200])}</div>',
                    unsafe_allow_html=True,
                )


def render_stop_button() -> bool:
    """Render a stop button. Returns True if stop was requested."""
    if st.session_state.get("processing", False):
        if st.button("⏹️ Durdur", key="stop_btn", type="secondary", use_container_width=True):
            st.session_state.stop_requested = True
            return True
    return False


def render_live_event_log():
    """Render the accumulated live events as a compact log after execution."""
    events = st.session_state.get("live_events", [])
    if not events:
        return

    with st.expander(f"📊 Son Çalışma Detayı ({len(events)} adım)", expanded=False):
        for ev in events:
            agent = ev.get("agent", "system") if isinstance(ev, dict) else getattr(ev, "agent", "system")
            event_type = ev.get("event_type", "") if isinstance(ev, dict) else getattr(ev, "event_type", "")
            content = ev.get("content", "") if isinstance(ev, dict) else getattr(ev, "content", "")

            cfg = MODELS.get(agent, {})
            icon = cfg.get("icon", "⚙️")
            color = cfg.get("color", "#6b7280")

            type_labels = {
                "agent_start": "🚀",
                "tool_call": "🔧",
                "tool_result": "📋",
                "thinking": "💭",
                "response": "💬",
                "pipeline": "🔄",
                "routing": "🧭",
                "error": "⚠️",
            }
            type_icon = type_labels.get(event_type, "📌")

            st.markdown(
                f'<div style="font-size:11px;color:#94a3b8;padding:2px 0;'
                f'border-bottom:1px solid #1e293b;">'
                f'{type_icon} {icon} '
                f'<span style="color:{color};">{agent}</span> '
                f'{_escape(content[:100])}</div>',
                unsafe_allow_html=True,
            )


def _tool_icon(tool_name: str) -> str:
    icons = {
        "web_search": "🔍",
        "web_fetch": "🌐",
        "find_skill": "🎯",
        "use_skill": "⚡",
        "decompose_task": "🧩",
        "direct_response": "💬",
        "synthesize_results": "🔗",
        "save_memory": "💾",
        "recall_memory": "🧠",
    }
    return icons.get(tool_name, "🔧")


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", " ")
    )
