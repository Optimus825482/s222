"""
Task history panel — shows completed tasks with pipeline info.
"""

from __future__ import annotations

import streamlit as st

from core.models import Task, TaskStatus, Thread


def render_task_history(thread: Thread | None) -> None:
    """Render task history below the chat area."""
    if not thread or not thread.tasks:
        return

    st.markdown("### 📋 Task History")

    for task in reversed(thread.tasks):
        status_map = {
            TaskStatus.COMPLETED: ("✅", "#10b981"),
            TaskStatus.FAILED: ("❌", "#ef4444"),
            TaskStatus.RUNNING: ("⚙️", "#3b82f6"),
            TaskStatus.PENDING: ("⏳", "#6b7280"),
            TaskStatus.ROUTING: ("🔄", "#f59e0b"),
            TaskStatus.REVIEWING: ("👁️", "#a78bfa"),
        }
        s_icon, s_color = status_map.get(task.status, ("⏳", "#6b7280"))

        badge_class = f"badge-{task.pipeline_type.value}"
        agents_used = ", ".join(
            st.assigned_agent.value for st in task.sub_tasks
        ) if task.sub_tasks else "direct"

        latency_str = f"{task.total_latency_ms:.0f}ms" if task.total_latency_ms else "—"

        st.markdown(
            f"""
            <div class="task-row">
                <span class="task-id">#{task.id[:6]}</span>
                <span class="task-preview">{_escape(task.user_input[:60])}</span>
                <span class="task-badge {badge_class}">{task.pipeline_type.value}</span>
                <span style="color:{s_color};font-size:13px;">{s_icon}</span>
                <span style="color:#6b7280;font-size:12px;font-family:monospace;">{latency_str}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Expandable result
        if task.final_result:
            with st.expander(f"Result #{task.id[:6]}", expanded=False):
                st.markdown(task.final_result)
                if task.sub_tasks:
                    st.markdown("**Agents:**")
                    for sub in task.sub_tasks:
                        st.markdown(
                            f"- `{sub.assigned_agent.value}`: {sub.status.value} "
                            f"({sub.token_usage} tokens, {sub.latency_ms:.0f}ms)"
                        )


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
