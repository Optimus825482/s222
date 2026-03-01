"""
Cockpit Dark Theme — Professional Operations Center aesthetic.
Separated: center = clean results, right = activity stream.
"""

DARK_THEME_CSS = """
<style>
    /* ── Global ──────────────────────────────────────────── */
    .stApp {
        background: linear-gradient(180deg, #060a14 0%, #0a1020 50%, #060a14 100%);
    }
    .stApp header { background: transparent !important; }
    .block-container { max-width: 1600px; }

    /* ── Cockpit Header ──────────────────────────────────── */
    .cockpit-header {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 10px 0;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 12px;
    }
    .cockpit-header-title {
        font-size: clamp(16px, 3.5vw, 22px);
        font-weight: 800;
        background: linear-gradient(135deg, #60a5fa, #a78bfa, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    .cockpit-header-sub {
        font-size: 11px;
        color: #475569;
        margin-left: auto;
        font-family: 'Cascadia Code', monospace;
    }

    /* ── Welcome Screen ──────────────────────────────────── */
    .cockpit-welcome {
        text-align: center;
        padding: 80px 20px 40px;
    }
    .cockpit-welcome-title {
        font-size: 22px;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 8px;
    }
    .cockpit-welcome-sub {
        font-size: 14px;
        color: #64748b;
        max-width: 500px;
        margin: 0 auto;
    }
    .cockpit-welcome-hints {
        display: flex;
        gap: 8px;
        justify-content: center;
        flex-wrap: wrap;
        margin-top: 24px;
    }
    .hint-chip {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 12px;
        color: #94a3b8;
    }

    /* ── Chat Messages (Center) ──────────────────────────── */
    .cockpit-msg-user {
        background: linear-gradient(135deg, #0f1d3a 0%, #0d1a33 100%);
        border: 1px solid #1e3a5f;
        border-radius: 16px 16px 4px 16px;
        padding: 16px 20px;
        margin: 10px 0;
        color: #e2e8f0;
        font-size: 14px;
        line-height: 1.6;
    }
    .cockpit-msg-user-label {
        font-size: 10px;
        font-weight: 700;
        color: #3b82f6;
        letter-spacing: 1.5px;
        margin-bottom: 6px;
    }

    .cockpit-msg-result {
        background: linear-gradient(135deg, #0a1628 0%, #0d1117 100%);
        border: 1px solid #1e3a5f;
        border-radius: 16px;
        padding: 0;
        margin: 14px 0;
        overflow: hidden;
    }
    .cockpit-msg-result-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 14px 20px;
        background: linear-gradient(135deg, #111d33 0%, #0f172a 100%);
        border-bottom: 1px solid #1e293b;
    }
    .cockpit-result-badge {
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 1.5px;
        color: #10b981;
        background: #064e3b;
        padding: 3px 10px;
        border-radius: 10px;
        margin-left: auto;
    }
    .cockpit-msg-result-body {
        padding: 18px 20px;
        color: #d1d5db;
        font-size: 14px;
        line-height: 1.7;
    }

    .cockpit-msg-agent {
        background: linear-gradient(135deg, #111827 0%, #0d1117 100%);
        border: 1px solid #1f2937;
        border-radius: 16px 16px 16px 4px;
        padding: 14px 18px;
        margin: 8px 0;
        color: #d1d5db;
        font-size: 14px;
        line-height: 1.6;
    }

    .cockpit-msg-error {
        background: linear-gradient(135deg, #1a0505 0%, #2d0a0a 100%);
        border: 1px solid #7f1d1d;
        border-radius: 12px;
        padding: 12px 16px;
        color: #fca5a5;
        font-size: 13px;
        margin: 8px 0;
    }

    /* ── Activity Stream (Right Column) ──────────────────── */
    .activity-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 15px;
        font-weight: 700;
        color: #e2e8f0;
        padding: 8px 0 10px;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 10px;
    }
    .activity-empty {
        color: #374151;
        font-size: 12px;
        text-align: center;
        padding: 30px 10px;
    }
    .activity-stats {
        display: flex;
        gap: 12px;
        justify-content: center;
        padding: 8px 0;
        margin-bottom: 8px;
        font-size: 11px;
        color: #94a3b8;
        border-bottom: 1px solid #111827;
    }
    .activity-feed {
        max-height: 70vh;
        overflow-y: auto;
        padding-right: 4px;
    }
    .activity-item {
        background: #0a0f1a;
        border: 1px solid #151d2e;
        border-left: 3px solid #374151;
        border-radius: 8px;
        padding: 8px 10px;
        margin: 4px 0;
        font-size: 11px;
        color: #94a3b8;
        transition: border-color 0.2s;
    }
    .activity-item:hover { border-color: #334155; }
    .activity-item-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 3px;
        font-size: 11px;
    }
    .activity-item-body {
        font-size: 11px;
        color: #6b7280;
        line-height: 1.4;
        word-break: break-word;
    }
    .activity-agent { font-size: 10px; font-weight: 600; }
    .activity-tool { border-left-color: #f59e0b; }
    .activity-result {
        border-left-color: #10b981;
        background: #060f0a;
        border-color: #0a2618;
    }
    .activity-error {
        border-left-color: #ef4444;
        background: #1a0505;
        border-color: #2d0a0a;
    }
    .activity-routing {
        border-left-color: #ec4899;
        background: #140a1a;
    }
    .activity-pipeline {
        text-align: center;
        color: #3b82f6;
        font-size: 11px;
        border-left-color: #3b82f6;
        background: #060a1a;
    }

    /* ── Agent Cards ─────────────────────────────────────── */
    .agent-card {
        background: linear-gradient(135deg, #0a1020 0%, #111827 100%);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 14px;
        margin: 6px 0;
        transition: all 0.3s ease;
    }
    .agent-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 0 16px rgba(59, 130, 246, 0.1);
    }
    .agent-card .agent-icon { font-size: 24px; }
    .agent-card .agent-name { font-size: 13px; font-weight: 600; color: #e2e8f0; }
    .agent-card .agent-status { font-size: 10px; padding: 2px 8px; border-radius: 12px; }
    .status-idle { background: #064e3b; color: #6ee7b7; }
    .status-active { background: #1e3a5f; color: #60a5fa; }
    .status-busy { background: #78350f; color: #fbbf24; }
    .status-error { background: #7f1d1d; color: #fca5a5; }
    .agent-metric { font-size: 11px; color: #94a3b8; margin-top: 4px; }
    .agent-metric-value { font-size: 16px; font-weight: 700; color: #e2e8f0; }

    /* ── Pipeline Viz ────────────────────────────────────── */
    .pipeline-node {
        background: #0f172a;
        border: 2px solid #3b82f6;
        border-radius: 10px;
        padding: 10px 14px;
        display: inline-block;
        color: #e2e8f0;
        font-size: 12px;
        font-weight: 500;
    }

    /* ── Metrics Panel ───────────────────────────────────── */
    .metric-card {
        background: #0a1020;
        border: 1px solid #151d2e;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
    }
    .metric-label { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 22px; font-weight: 700; color: #10b981; margin-top: 2px; }
    .metric-value.warning { color: #f59e0b; }
    .metric-value.info { color: #3b82f6; }

    /* ── Task History ────────────────────────────────────── */
    .task-row {
        background: #0a1020;
        border: 1px solid #151d2e;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 3px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .task-row .task-id { color: #475569; font-size: 11px; font-family: monospace; }
    .task-row .task-preview { color: #d1d5db; font-size: 12px; flex: 1; }
    .task-row .task-badge { font-size: 10px; padding: 2px 8px; border-radius: 6px; font-weight: 600; }
    .badge-sequential { background: #1e3a5f; color: #60a5fa; }
    .badge-parallel { background: #3b0764; color: #c084fc; }
    .badge-consensus { background: #78350f; color: #fbbf24; }
    .badge-iterative { background: #064e3b; color: #6ee7b7; }
    .badge-deep_research { background: #1e1b4b; color: #818cf8; }

    /* ── Sidebar ─────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: #060a14 !important;
        border-right: 1px solid #111827;
    }
    section[data-testid="stSidebar"] .stMarkdown { color: #c9d1d9; }

    /* ── Scrollbar ───────────────────────────────────────── */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }

    /* ── Expander ────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background: #0a1020 !important;
        border: 1px solid #151d2e !important;
        border-radius: 8px !important;
        color: #94a3b8 !important;
        font-size: 12px !important;
    }

    /* ── Live Monitor (st.status) ────────────────────────── */
    [data-testid="stStatusWidget"] {
        background: #0a0f1a !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
    }
    [data-testid="stStatusWidget"] summary {
        color: #e2e8f0 !important;
        font-weight: 600 !important;
    }

    /* ── A2A Stream (sidebar) ────────────────────────────── */
    .a2a-stream { max-height: 350px; overflow-y: auto; padding-right: 4px; }
    .a2a-entry {
        background: #0a0f1a;
        border: 1px solid #151d2e;
        border-radius: 6px;
        padding: 6px 8px;
        margin: 3px 0;
    }
    .a2a-entry:hover { border-color: #1e293b; }
    .a2a-content { font-size: 10px; color: #6b7280; margin-top: 3px; line-height: 1.3; word-break: break-word; }
    .a2a-arrow { text-align: center; font-size: 11px; color: #374151; padding: 1px 0; }
    .agent-status-dot {
        background: #0a1020;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 3px 6px;
        font-size: 13px;
        text-align: center;
    }

    /* ── Mobile Responsive ───────────────────────────────── */
    @media (max-width: 768px) {
        .block-container { padding: 0.5rem 0.8rem !important; max-width: 100% !important; }
        section[data-testid="stSidebar"] { min-width: 240px !important; width: 240px !important; }
        .agent-card { padding: 10px; margin: 3px 0; }
        .cockpit-msg-user, .cockpit-msg-agent, .cockpit-msg-result-body { font-size: 13px; padding: 12px 14px; }
        .activity-feed { max-height: 40vh; }
        .activity-item { padding: 6px 8px; }
        .cockpit-welcome { padding: 40px 10px 20px; }
    }
    @media (max-width: 480px) {
        .block-container { padding: 0.3rem 0.5rem !important; }
        .cockpit-msg-user, .cockpit-msg-agent { font-size: 12px; border-radius: 10px; }
    }
    @media (pointer: coarse) {
        .stButton > button { min-height: 44px; }
        [data-testid="stChatInput"] textarea { min-height: 44px; font-size: 16px !important; }
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
    return (
        f'<span class="agent-badge" style="background:{bg};color:{fg};'
        f'font-size:11px;padding:2px 8px;border-radius:8px;font-weight:600;">'
        f'{text}</span>'
    )
