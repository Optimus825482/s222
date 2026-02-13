"""
Multi-Agent Operations Center — Streamlit Dashboard.
Qwen3 80B orchestrator + 4 specialist agents.
12-Factor Agent architecture.

Layout: Sidebar (agents + A2A) | Center (chat + pipeline) | Right (tool stream)
"""

import sys
from pathlib import Path

_root = str(Path(__file__).parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import asyncio
import streamlit as st

from config import MODELS
from core.models import Thread, PipelineType
from core.state import save_thread, load_thread, list_threads
from ui.theme import DARK_THEME_CSS
from ui.agent_cards import render_agent_cards
from ui.a2a_stream import render_a2a_stream, render_agent_status_live
from ui.chat import render_chat_history
from ui.pipeline_view import render_pipeline_selector, render_pipeline_flow
from ui.metrics import render_metrics_panel
from ui.task_history import render_task_history
from ui.tool_stream import render_tool_stream


# ── Page Config ──────────────────────────────────────────────────

st.set_page_config(
    page_title="Multi-Agent Ops Center",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

# Viewport meta for mobile
st.markdown(
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">',
    unsafe_allow_html=True,
)


# ── Session State ────────────────────────────────────────────────

if "thread" not in st.session_state:
    st.session_state.thread = Thread()
if "pipeline_type" not in st.session_state:
    st.session_state.pipeline_type = PipelineType.AUTO
if "processing" not in st.session_state:
    st.session_state.processing = False


def get_thread() -> Thread:
    return st.session_state.thread


# ── Async Runner ─────────────────────────────────────────────────

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── Sidebar: Agent Fleet + A2A Stream ────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:12px 0;">
            <div style="font-size:32px;">🧠</div>
            <div style="font-size:16px;font-weight:700;color:#e2e8f0;margin-top:4px;">
                Multi-Agent Ops
            </div>
            <div style="font-size:11px;color:#6b7280;">
                Qwen Orchestrated • 12-Factor
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Live agent status dots
    render_agent_status_live(get_thread())

    # Agent cards (compact)
    render_agent_cards(get_thread())

    st.markdown("---")

    # A2A Communication Stream
    render_a2a_stream(get_thread())

    st.markdown("---")

    # Metrics
    render_metrics_panel(get_thread())

    st.markdown("---")

    # Session management
    st.markdown("### 💾 Sessions")
    col_new, col_save = st.columns(2)
    with col_new:
        if st.button("🆕 New", use_container_width=True):
            st.session_state.thread = Thread()
            st.rerun()
    with col_save:
        if st.button("💾 Save", use_container_width=True):
            tid = save_thread(get_thread())
            st.toast(f"Saved: {tid[:8]}", icon="✅")

    saved = list_threads(limit=5)
    if saved:
        for t_info in saved:
            preview = t_info["preview"][:35] or "(empty)"
            if st.button(f"📂 {preview}", key=f"load_{t_info['id']}", use_container_width=True):
                loaded = load_thread(t_info["id"])
                if loaded:
                    st.session_state.thread = loaded
                    st.rerun()


# ── Main Area: 2-column layout (Chat | Tool Stream) ─────────────

# Header
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap;">
        <span style="font-size:28px;">🧠</span>
        <span style="font-size:clamp(16px, 4vw, 22px);font-weight:700;color:#e2e8f0;">
            Multi-Agent Operations Center
        </span>
        <span style="font-size:12px;color:#6b7280;margin-left:auto;">
            Qwen3 80B • 4 Agents • 4 Pipelines
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Pipeline selector (full width)
selected_pipeline = render_pipeline_selector()

st.markdown("---")

# Two columns: Chat (left ~70%) | Tool Stream (right ~30%)
col_chat, col_tools = st.columns([7, 3])

with col_chat:
    # Chat area
    render_chat_history(get_thread())

    # Pipeline flow visualization
    thread = get_thread()
    if thread.tasks:
        current_task = thread.tasks[-1]
        render_pipeline_flow(current_task)

    st.markdown("---")

    # Task history
    render_task_history(get_thread())

with col_tools:
    # Tool Activity Stream
    render_tool_stream(get_thread())


# ── Chat Input ───────────────────────────────────────────────────

user_input = st.chat_input(
    "Görev gönder — Qwen analiz edip specialist agent'lara yönlendirecek...",
    disabled=st.session_state.processing,
)

if user_input and not st.session_state.processing:
    st.session_state.processing = True
    thread = get_thread()

    try:
        from agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()
        result = run_async(orchestrator.route_and_execute(user_input, thread))
        save_thread(thread)
        st.session_state.pop("last_error", None)

    except Exception as e:
        import traceback
        st.session_state["last_error"] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    finally:
        st.session_state.processing = False
        st.rerun()

# Show persistent error if exists
if "last_error" in st.session_state:
    st.error(st.session_state["last_error"])
    if st.button("🗑️ Hatayı temizle"):
        st.session_state.pop("last_error", None)
        st.rerun()
