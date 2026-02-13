"""
Dark theme CSS — Professional Operations Center aesthetic.
"""

DARK_THEME_CSS = """
<style>
    /* ── Global ──────────────────────────────────────────── */
    .stApp {
        background: linear-gradient(180deg, #0a0e1a 0%, #0e1525 50%, #0a0e1a 100%);
    }
    .stApp header { background: transparent !important; }
    .block-container { max-width: 1400px; }

    /* ── Agent Cards ─────────────────────────────────────── */
    .agent-card {
        background: linear-gradient(135deg, #111827 0%, #1a2332 100%);
        border: 1px solid #1e3a5f;
        border-radius: 14px;
        padding: 18px;
        margin: 8px 0;
        transition: all 0.3s ease;
    }
    .agent-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.15);
        transform: translateY(-2px);
    }
    .agent-card .agent-icon { font-size: 28px; }
    .agent-card .agent-name {
        font-size: 14px;
        font-weight: 600;
        color: #e2e8f0;
        margin-top: 4px;
    }
    .agent-card .agent-status {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 12px;
        display: inline-block;
        margin-top: 6px;
    }
    .status-idle { background: #064e3b; color: #6ee7b7; }
    .status-active { background: #1e3a5f; color: #60a5fa; }
    .status-busy { background: #78350f; color: #fbbf24; }
    .status-error { background: #7f1d1d; color: #fca5a5; }

    .agent-metric {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 4px;
    }
    .agent-metric-value {
        font-size: 18px;
        font-weight: 700;
        color: #e2e8f0;
    }

    /* ── Chat ────────────────────────────────────────────── */
    .chat-msg-user {
        background: linear-gradient(135deg, #1e3a5f 0%, #1a2744 100%);
        border: 1px solid #2563eb33;
        border-radius: 14px 14px 4px 14px;
        padding: 14px 18px;
        margin: 6px 0;
        color: #e2e8f0;
    }
    .chat-msg-agent {
        background: linear-gradient(135deg, #1a2332 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 14px 14px 14px 4px;
        padding: 14px 18px;
        margin: 6px 0;
        color: #d1d5db;
    }
    .chat-msg-agent .agent-badge {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 8px;
        margin-right: 6px;
        font-weight: 600;
    }

    /* ── Pipeline Viz ────────────────────────────────────── */
    .pipeline-node {
        background: #1e293b;
        border: 2px solid #3b82f6;
        border-radius: 10px;
        padding: 10px 16px;
        display: inline-block;
        color: #e2e8f0;
        font-size: 13px;
        font-weight: 500;
    }
    .pipeline-node.active {
        border-color: #10b981;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.3);
    }
    .pipeline-node.completed {
        border-color: #6ee7b7;
        background: #064e3b;
    }
    .pipeline-arrow {
        color: #475569;
        font-size: 20px;
        margin: 0 8px;
    }

    /* ── Metrics Panel ───────────────────────────────────── */
    .metric-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .metric-label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 26px; font-weight: 700; color: #10b981; margin-top: 4px; }
    .metric-value.warning { color: #f59e0b; }
    .metric-value.info { color: #3b82f6; }

    /* ── Task History ────────────────────────────────────── */
    .task-row {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 4px 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .task-row .task-id { color: #6b7280; font-size: 12px; font-family: monospace; }
    .task-row .task-preview { color: #d1d5db; font-size: 13px; flex: 1; }
    .task-row .task-badge {
        font-size: 11px;
        padding: 2px 10px;
        border-radius: 8px;
        font-weight: 600;
    }
    .badge-sequential { background: #1e3a5f; color: #60a5fa; }
    .badge-parallel { background: #3b0764; color: #c084fc; }
    .badge-consensus { background: #78350f; color: #fbbf24; }
    .badge-iterative { background: #064e3b; color: #6ee7b7; }

    /* ── Sidebar ─────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: #0d1117 !important;
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] .stMarkdown { color: #c9d1d9; }

    /* ── Scrollbar ───────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a0e1a; }
    ::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #2563eb; }

    /* ── Mobile Responsive ───────────────────────────────── */
    @media (max-width: 768px) {
        .block-container { padding: 0.5rem 0.8rem !important; max-width: 100% !important; }
        section[data-testid="stSidebar"] { min-width: 260px !important; width: 260px !important; }
        .agent-card { padding: 12px; margin: 4px 0; }
        .agent-card .agent-icon { font-size: 22px; }
        .agent-card .agent-name { font-size: 12px; }
        .agent-metric-value { font-size: 14px; }
        .agent-metric { font-size: 10px; }
        .chat-msg-user, .chat-msg-agent { padding: 10px 12px; font-size: 13px; }
        .metric-card { padding: 10px; }
        .metric-value { font-size: 20px; }
        .metric-label { font-size: 10px; }
        .tool-entry { padding: 8px 10px; }
        .tool-args { font-size: 10px; max-height: 40px; }
        .tool-result { font-size: 10px; max-height: 50px; }
        .task-row { padding: 8px 10px; flex-wrap: wrap; gap: 6px; }
        .task-row .task-preview { font-size: 12px; }
        .pipeline-node { padding: 6px 10px; font-size: 11px; }
        .pipeline-node div[style*="font-size:24px"] { font-size: 18px !important; }
        .a2a-entry { padding: 6px 8px; }
        .a2a-content { font-size: 10px; }
        .right-panel-header { font-size: 14px; }
        /* Hide tool stream column on very small screens */
        [data-testid="stHorizontalBlock"] > div:last-child {
            min-width: 0 !important;
        }
    }

    @media (max-width: 480px) {
        .block-container { padding: 0.3rem 0.5rem !important; }
        .agent-card { padding: 8px; }
        .chat-msg-user, .chat-msg-agent { padding: 8px 10px; font-size: 12px; border-radius: 10px; }
        .metric-card { padding: 8px; }
        .metric-value { font-size: 18px; }
        .agent-status-dot { padding: 2px 5px; font-size: 12px; }
    }

    /* ── Touch-friendly inputs ───────────────────────────── */
    @media (pointer: coarse) {
        .stButton > button { min-height: 44px; }
        [data-testid="stChatInput"] textarea { min-height: 44px; font-size: 16px !important; }
    }

    /* ── Expander (thinking) ─────────────────────────────── */
    .streamlit-expanderHeader {
        background: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 8px !important;
        color: #94a3b8 !important;
        font-size: 12px !important;
    }

    /* ── Tool Activity Stream ────────────────────────────── */
    .tool-entry {
        background: linear-gradient(135deg, #0f1729 0%, #111827 100%);
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 12px 14px;
        margin: 6px 0;
        transition: all 0.2s ease;
    }
    .tool-entry:hover {
        border-color: #334155;
        background: linear-gradient(135deg, #111d33 0%, #151f30 100%);
    }
    .tool-args {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 6px;
        padding: 6px 8px;
        background: #0a0e1a;
        border-radius: 6px;
        font-family: 'Cascadia Code', 'Fira Code', monospace;
        word-break: break-all;
        max-height: 60px;
        overflow: hidden;
    }
    .tool-result {
        font-size: 11px;
        color: #6ee7b7;
        margin-top: 6px;
        padding: 6px 8px;
        background: #061a14;
        border: 1px solid #064e3b;
        border-radius: 6px;
        max-height: 80px;
        overflow: hidden;
        line-height: 1.4;
    }

    /* ── Right Panel ─────────────────────────────────────── */
    .right-panel-header {
        font-size: 16px;
        font-weight: 700;
        color: #e2e8f0;
        padding: 8px 0;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 12px;
    }

    /* ── A2A Communication Stream ────────────────────────── */
    .a2a-stream {
        max-height: 400px;
        overflow-y: auto;
        padding-right: 4px;
    }
    .a2a-entry {
        background: #0d1117;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 8px 10px;
        margin: 4px 0;
        transition: all 0.2s ease;
    }
    .a2a-entry:hover {
        border-color: #334155;
        background: #111827;
    }
    .a2a-content {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 4px;
        line-height: 1.4;
        word-break: break-word;
    }
    .a2a-arrow {
        text-align: center;
        font-size: 12px;
        color: #475569;
        padding: 2px 0;
        letter-spacing: 2px;
    }
    .agent-status-dot {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 4px 8px;
        font-size: 14px;
        text-align: center;
    }
</style>
"""

# Agent color mapping for badges
AGENT_COLORS = {
    "orchestrator": ("#ec4899", "#831843"),
    "thinker": ("#00e5ff", "#0e3a4a"),
    "speed": ("#a78bfa", "#2e1065"),
    "researcher": ("#f59e0b", "#78350f"),
    "reasoner": ("#10b981", "#064e3b"),
}


def agent_badge_html(role: str, label: str | None = None) -> str:
    """Generate colored badge HTML for an agent role."""
    fg, bg = AGENT_COLORS.get(role, ("#94a3b8", "#1f2937"))
    text = label or role.capitalize()
    return f'<span class="agent-badge" style="background:{bg};color:{fg};">{text}</span>'
