"""
Pipeline execution flow visualization.
"""

from __future__ import annotations

import streamlit as st

from config import MODELS
from core.models import PipelineType, Task, TaskStatus


def render_pipeline_selector() -> PipelineType:
    """Pipeline type selector buttons — responsive layout."""
    options = [
        ("🔄 Auto", PipelineType.AUTO),
        ("➡️ Seq", PipelineType.SEQUENTIAL),
        ("⚡ Par", PipelineType.PARALLEL),
        ("🗳️ Con", PipelineType.CONSENSUS),
        ("🔁 Iter", PipelineType.ITERATIVE),
    ]

    selected = st.session_state.get("pipeline_type", PipelineType.AUTO)
    cols = st.columns(5)

    for col, (label, ptype) in zip(cols, options):
        with col:
            is_active = selected == ptype
            variant = "primary" if is_active else "secondary"
            if st.button(label, key=f"pipe_{ptype.value}", use_container_width=True, type=variant):
                st.session_state["pipeline_type"] = ptype
                selected = ptype

    return selected


def render_pipeline_flow(task: Task | None) -> None:
    """Visualize current pipeline execution flow."""
    if not task or not task.sub_tasks:
        return

    st.markdown(f"**Pipeline:** `{task.pipeline_type.value}` — {len(task.sub_tasks)} sub-tasks")

    if task.pipeline_type in (PipelineType.PARALLEL, PipelineType.CONSENSUS):
        _render_parallel_flow(task)
    elif task.pipeline_type == PipelineType.ITERATIVE:
        _render_iterative_flow(task)
    else:
        _render_sequential_flow(task)


def _render_sequential_flow(task: Task) -> None:
    """Sequential: A → B → C"""
    cols = []
    for i, st_item in enumerate(task.sub_tasks):
        if i > 0:
            cols.append("arrow")
        cols.append(st_item)

    display_cols = st.columns(len(cols))
    for col, item in zip(display_cols, cols):
        with col:
            if item == "arrow":
                st.markdown(
                    '<div style="text-align:center;color:#475569;font-size:24px;padding-top:12px;">→</div>',
                    unsafe_allow_html=True,
                )
            else:
                _render_node(item)


def _render_parallel_flow(task: Task) -> None:
    """Parallel: [A, B, C] running simultaneously."""
    cols = st.columns(len(task.sub_tasks))
    for col, st_item in zip(cols, task.sub_tasks):
        with col:
            _render_node(st_item)


def _render_iterative_flow(task: Task) -> None:
    """Iterative: Producer ↔ Reviewer."""
    if len(task.sub_tasks) >= 2:
        c1, c2, c3 = st.columns([2, 1, 2])
        with c1:
            _render_node(task.sub_tasks[0])
        with c2:
            st.markdown(
                '<div style="text-align:center;color:#475569;font-size:20px;padding-top:12px;">⇄</div>',
                unsafe_allow_html=True,
            )
        with c3:
            _render_node(task.sub_tasks[1])


def _render_node(subtask) -> None:
    """Render a single pipeline node."""
    cfg = MODELS.get(subtask.assigned_agent.value, {})
    icon = cfg.get("icon", "🤖")
    color = cfg.get("color", "#3b82f6")
    name = cfg.get("name", subtask.assigned_agent.value)

    status_map = {
        TaskStatus.PENDING: ("⏳", "#475569"),
        TaskStatus.RUNNING: ("⚙️", "#3b82f6"),
        TaskStatus.COMPLETED: ("✅", "#10b981"),
        TaskStatus.FAILED: ("❌", "#ef4444"),
    }
    s_icon, s_color = status_map.get(subtask.status, ("⏳", "#475569"))

    st.markdown(
        f"""
        <div class="pipeline-node" style="border-color:{color};text-align:center;width:100%;">
            <div style="font-size:24px;">{icon}</div>
            <div style="font-size:12px;font-weight:600;color:{color};">{name}</div>
            <div style="font-size:10px;color:#94a3b8;margin-top:4px;">
                {subtask.description[:40]}...
            </div>
            <div style="font-size:11px;color:{s_color};margin-top:6px;">
                {s_icon} {subtask.status.value}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
