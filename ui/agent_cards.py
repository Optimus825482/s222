"""
Agent status cards — sidebar component showing live agent metrics.
"""

from __future__ import annotations

import streamlit as st

from config import MODELS
from core.models import AgentMetrics, Thread


def render_agent_cards(thread: Thread | None) -> None:
    """Render agent status cards in sidebar."""
    st.markdown("### 🤖 Agent Fleet")
    st.markdown("---")

    for key, cfg in MODELS.items():
        metrics = None
        status = "idle"
        if thread and key in thread.agent_metrics:
            m = thread.agent_metrics[key]
            if isinstance(m, dict):
                metrics = AgentMetrics(**m)
            else:
                metrics = m
            if metrics.last_active:
                status = "active"

        icon = cfg["icon"]
        name = cfg["name"]
        color = cfg["color"]

        # Pre-compute values to avoid None access in f-string
        calls = metrics.total_calls if metrics else 0
        tokens = metrics.total_tokens if metrics else 0
        avg_ms = f"{metrics.avg_latency_ms:.0f}" if metrics else "0"

        status_emoji = {"idle": "⚪", "active": "🟢", "busy": "🟡", "error": "🔴"}.get(status, "⚪")

        with st.container():
            st.markdown(
                f"""
                <div class="agent-card" style="border-left: 3px solid {color};">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <span class="agent-icon">{icon}</span>
                            <span class="agent-name" style="color:{color};">{name}</span>
                        </div>
                        <span class="agent-status status-{status}">{status_emoji} {status}</span>
                    </div>
                    <div style="display:flex;gap:16px;margin-top:10px;">
                        <div class="agent-metric">
                            <div class="agent-metric-value">{calls}</div>
                            <div>calls</div>
                        </div>
                        <div class="agent-metric">
                            <div class="agent-metric-value">{tokens}</div>
                            <div>tokens</div>
                        </div>
                        <div class="agent-metric">
                            <div class="agent-metric-value">{avg_ms}ms</div>
                            <div>avg</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
