"""
Metrics panel — token usage, latency, cost tracking.
"""

from __future__ import annotations

import streamlit as st

from core.models import AgentMetrics, Thread


def render_metrics_panel(thread: Thread | None) -> None:
    """Render aggregate metrics at the bottom of sidebar."""
    st.markdown("### 📊 Metrics")
    st.markdown("---")

    total_calls = 0
    total_tokens = 0
    total_latency = 0.0
    total_errors = 0

    if thread and thread.agent_metrics:
        for key, m in thread.agent_metrics.items():
            if isinstance(m, dict):
                m = AgentMetrics(**m)
            total_calls += m.total_calls
            total_tokens += m.total_tokens
            total_latency += m.total_latency_ms
            total_errors += m.error_count

    avg_latency = total_latency / max(total_calls, 1)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Calls</div>
                <div class="metric-value info">{total_calls}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Tokens</div>
                <div class="metric-value">{_format_number(total_tokens)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")  # spacer

    c3, c4 = st.columns(2)
    with c3:
        color_class = "warning" if avg_latency > 3000 else ""
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Avg Latency</div>
                <div class="metric-value {color_class}">{avg_latency:.0f}ms</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        color_class = "warning" if total_errors > 0 else ""
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Errors</div>
                <div class="metric-value {color_class}">{total_errors}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Task count
    task_count = len(thread.tasks) if thread else 0
    st.markdown(
        f"""
        <div class="metric-card" style="margin-top:8px;">
            <div class="metric-label">Tasks Completed</div>
            <div class="metric-value info">{task_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
