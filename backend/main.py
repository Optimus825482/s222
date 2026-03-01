"""
Multi-Agent Ops Center — FastAPI Backend.
WebSocket streaming + REST API wrapping existing agent/pipeline/tool infrastructure.
"""

import sys
from pathlib import Path

# Add parent dir so we can import existing modules (agents, pipelines, tools, core, config)
_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

import asyncio
import hashlib
import json
import re
import secrets
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import MODELS
from core.models import Thread, PipelineType, EventType, AgentRole, AgentMetrics
from core.state import save_thread, load_thread, list_threads, delete_thread, delete_all_threads


# ── Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize PostgreSQL on startup
    try:
        from tools.pg_connection import init_database
        init_database()
        print("[Backend] PostgreSQL initialized successfully")
    except Exception as e:
        print(f"[Backend] PostgreSQL init failed (SQLite fallback): {e}")

    # Seed default MCP servers for orchestration
    try:
        from tools.mcp_client import seed_default_servers
        seeded = seed_default_servers()
        if seeded:
            print(f"[Backend] Seeded {seeded} default MCP servers")
    except Exception as e:
        print(f"[Backend] MCP seed failed (non-critical): {e}")

    yield


app = FastAPI(title="Multi-Agent Ops Center API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ─────────────────────────────────────────────────────────

USERS = {
    "erkan": {
        "password_hash": hashlib.sha256("518518".encode()).hexdigest(),
        "full_name": "Erkan Erdem",
        "user_id": "erkan",
    },
    "yigit": {
        "password_hash": hashlib.sha256("518518".encode()).hexdigest(),
        "full_name": "Yiğit Avcı",
        "user_id": "yigit",
    },
}

# In-memory token store: token -> user_id
_active_tokens: dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


def _get_user_from_token(token: str) -> dict | None:
    user_id = _active_tokens.get(token)
    if not user_id:
        return None
    return USERS.get(user_id)


# ── Request/Response Models ──────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    pipeline_type: str = "auto"


class ThreadSummary(BaseModel):
    id: str
    preview: str
    created_at: str
    task_count: int
    event_count: int


class SkillCreateRequest(BaseModel):
    skill_id: str
    name: str
    description: str
    knowledge: str
    category: str = "custom"
    keywords: list[str] = []


class RAGIngestRequest(BaseModel):
    content: str
    title: str
    source: str = ""


class RAGQueryRequest(BaseModel):
    query: str
    max_results: int = 5


class MCPServerRequest(BaseModel):
    server_id: str
    url: str
    name: str = ""


class TeachRequest(BaseModel):
    content: str


# ── Auth Endpoints ────────────────────────────────────────────────

@app.post("/api/auth/login")
async def api_login(req: LoginRequest):
    user = USERS.get(req.username.lower())
    if not user:
        raise HTTPException(401, "Kullanıcı bulunamadı")
    expected = hashlib.sha256(req.password.encode()).hexdigest()
    if user["password_hash"] != expected:
        raise HTTPException(401, "Şifre hatalı")
    token = secrets.token_hex(32)
    _active_tokens[token] = user["user_id"]
    return {
        "token": token,
        "user_id": user["user_id"],
        "full_name": user["full_name"],
    }


@app.post("/api/auth/logout")
async def api_logout(authorization: str = ""):
    token = authorization.replace("Bearer ", "").strip()
    _active_tokens.pop(token, None)
    return {"ok": True}


@app.get("/api/auth/me")
async def api_me(authorization: str = ""):
    token = authorization.replace("Bearer ", "").strip()
    user = _get_user_from_token(token)
    if not user:
        raise HTTPException(401, "Geçersiz token")
    return {"user_id": user["user_id"], "full_name": user["full_name"]}


# ── REST Endpoints: Models & Config ──────────────────────────────

@app.get("/api/models")
async def get_models():
    """Return all model configurations for the agent fleet."""
    return MODELS


@app.get("/api/pipelines")
async def get_pipelines():
    """Return available pipeline types."""
    return [
        {"id": p.value, "label": p.value.replace("_", " ").title()}
        for p in PipelineType
    ]


# ── REST Endpoints: Threads ──────────────────────────────────────

@app.get("/api/threads")
async def api_list_threads(limit: int = 20, user_id: str = ""):
    return list_threads(limit=limit, user_id=user_id or None)


@app.post("/api/threads")
async def api_create_thread(user_id: str = ""):
    thread = Thread()
    save_thread(thread, user_id=user_id or None)
    return {"id": thread.id}


@app.get("/api/threads/{thread_id}")
async def api_get_thread(thread_id: str, user_id: str = ""):
    thread = load_thread(thread_id, user_id=user_id or None)
    if not thread:
        raise HTTPException(404, "Thread not found")
    return thread.model_dump(mode="json")


@app.delete("/api/threads/{thread_id}")
async def api_delete_thread(thread_id: str, user_id: str = ""):
    ok = delete_thread(thread_id, user_id=user_id or None)
    if not ok:
        raise HTTPException(404, "Thread not found")
    return {"deleted": True}


@app.delete("/api/threads")
async def api_delete_all_threads(user_id: str = ""):
    count = delete_all_threads(user_id=user_id or None)
    return {"deleted": count}


# ── REST Endpoints: Tools (RAG, Skills, MCP, Teachability, Eval) ─

@app.post("/api/rag/ingest")
async def api_rag_ingest(req: RAGIngestRequest):
    from tools.rag import rag_ingest
    result = rag_ingest(req.content, req.title, req.source)
    return result


@app.post("/api/rag/query")
async def api_rag_query(req: RAGQueryRequest):
    from tools.rag import rag_query
    results = rag_query(req.query, req.max_results)
    return results


@app.get("/api/rag/documents")
async def api_rag_documents():
    from tools.rag import list_documents
    return list_documents()


@app.get("/api/skills")
async def api_list_skills():
    try:
        from tools.dynamic_skills import list_skills
        return list_skills()
    except Exception:
        return []


@app.post("/api/skills")
async def api_create_skill(req: SkillCreateRequest):
    try:
        from tools.dynamic_skills import create_skill
        return create_skill(
            skill_id=req.skill_id, name=req.name,
            description=req.description, knowledge=req.knowledge,
            category=req.category, keywords=req.keywords,
        )
    except Exception as e:
        raise HTTPException(503, f"Skills module error: {e}")


@app.get("/api/skills/{skill_id}")
async def api_get_skill(skill_id: str):
    try:
        from tools.dynamic_skills import get_skill
        skill = get_skill(skill_id)
        if not skill:
            raise HTTPException(404, "Skill not found")
        return skill
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Skills module error: {e}")


@app.delete("/api/skills/{skill_id}")
async def api_delete_skill(skill_id: str):
    try:
        from tools.dynamic_skills import delete_skill
        return delete_skill(skill_id)
    except Exception as e:
        raise HTTPException(503, f"Skills module error: {e}")


@app.get("/api/mcp/servers")
async def api_mcp_servers():
    try:
        from tools.mcp_client import list_servers
        return list_servers()
    except Exception:
        return []


@app.post("/api/mcp/servers")
async def api_add_mcp_server(req: MCPServerRequest):
    try:
        from tools.mcp_client import register_server
        return register_server(req.server_id, req.url, req.name)
    except Exception as e:
        raise HTTPException(503, f"MCP module error: {e}")


@app.post("/api/mcp/seed")
async def api_mcp_seed(overwrite: bool = False):
    """Re-seed default MCP servers. Use overwrite=true to reset configs."""
    try:
        from tools.mcp_client import seed_default_servers, DEFAULT_MCP_SERVERS
        count = seed_default_servers(overwrite=overwrite)
        return {
            "seeded": count,
            "total_defaults": len(DEFAULT_MCP_SERVERS),
            "message": f"{count} server kaydedildi" if count else "Tüm server'lar zaten kayıtlı",
        }
    except Exception as e:
        raise HTTPException(503, f"MCP seed error: {e}")


@app.get("/api/mcp/servers/{server_id}/tools")
async def api_mcp_tools(server_id: str):
    try:
        from tools.mcp_client import discover_tools
        return await discover_tools(server_id)
    except Exception as e:
        raise HTTPException(503, f"MCP module error: {e}")


@app.get("/api/teachability")
async def api_get_teachings():
    try:
        from tools.teachability import get_all_teachings
        return get_all_teachings()
    except Exception:
        return []


@app.post("/api/teachability")
async def api_add_teaching(req: TeachRequest):
    try:
        from tools.teachability import save_teaching
        return save_teaching(req.content)
    except Exception as e:
        raise HTTPException(503, f"Teachability module error: {e}")


@app.get("/api/eval/stats")
async def api_eval_stats():
    try:
        from tools.agent_eval import get_agent_stats
        return get_agent_stats()
    except Exception:
        return {"total_evals": 0, "avg_score": 0, "evals": []}


# ── Memory Endpoints ─────────────────────────────────────────────

@app.get("/api/memory/stats")
async def api_memory_stats():
    """Get layered memory statistics."""
    try:
        from tools.memory import get_memory_stats
        return get_memory_stats()
    except Exception as e:
        return {"error": str(e), "total_memories": 0}

@app.get("/api/memory/layers")
async def api_memory_layers():
    """Get memories grouped by layer."""
    try:
        from tools.memory import list_memories
        working = list_memories(layer="working", limit=10)
        episodic = list_memories(layer="episodic", limit=20)
        semantic = list_memories(layer="semantic", limit=20)
        return {"working": working, "episodic": episodic, "semantic": semantic}
    except Exception as e:
        return {"working": [], "episodic": [], "semantic": [], "error": str(e)}

@app.delete("/api/memory/{memory_id}")
async def api_delete_memory(memory_id: int):
    try:
        from tools.memory import delete_memory
        ok = delete_memory(memory_id)
        if not ok:
            raise HTTPException(404, "Memory not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, str(e))


# ── Auto-Skills Endpoints ────────────────────────────────────────

@app.get("/api/skills/auto")
async def api_list_auto_skills():
    """List auto-generated skills."""
    try:
        from tools.dynamic_skills import list_skills
        return list_skills(source="auto-learned")
    except Exception:
        return []

@app.post("/api/skills/migrate")
async def api_migrate_skills():
    """Trigger SQLite → PostgreSQL migration."""
    try:
        from tools.pg_connection import migrate_from_sqlite
        result = migrate_from_sqlite()
        return result
    except Exception as e:
        raise HTTPException(503, str(e))

@app.get("/api/db/health")
async def api_db_health():
    """Check PostgreSQL connection health."""
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()
        cur.close()
        release_conn(conn)
        return {"status": "ok", "backend": "postgresql", "version": str(version)}
    except Exception as e:
        return {"status": "error", "backend": "sqlite_fallback", "error": str(e)}


# ── REST Endpoints: Project Export ───────────────────────────────

@app.get("/api/projects")
async def api_list_projects():
    """List all generated idea-to-project outputs."""
    from tools.idea_to_project import PROJECTS_DIR, PHASES
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for d in sorted(PROJECTS_DIR.iterdir()):
        if d.is_dir():
            phases_done = [f.stem for f in d.glob("*.md")]
            projects.append({
                "name": d.name,
                "phases": phases_done,
                "phase_count": len(phases_done),
                "total_phases": len(PHASES),
            })
    return projects


@app.get("/api/projects/{project_name}/export")
async def api_export_project(project_name: str):
    """Export full project as a single combined Markdown document."""
    from tools.idea_to_project import PROJECTS_DIR, PHASES
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")

    parts = [
        f"# 🚀 Proje Raporu\n",
        f"**Proje:** {project_name.replace('_', ' ').title()}\n",
        f"**Oluşturulma:** {__import__('datetime').datetime.now().strftime('%d %B %Y, %H:%M')}\n",
        f"**Pipeline:** Idea-to-Project (5 Faz)\n",
        "---\n",
    ]

    # Table of contents
    parts.append("## 📑 İçindekiler\n")
    for i, phase in enumerate(PHASES, 1):
        filepath = project_dir / f"{phase['id']}.md"
        status = "✅" if filepath.exists() else "⏳"
        parts.append(f"{i}. {status} {phase['name']}")
    parts.append("\n---\n")

    # Phase contents
    for i, phase in enumerate(PHASES, 1):
        filepath = project_dir / f"{phase['id']}.md"
        parts.append(f"\n## {i}. {phase['name']}\n")
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            parts.append(content)
        else:
            parts.append("*Bu faz henüz tamamlanmadı.*")
        parts.append("\n---\n")

    return {"markdown": "\n".join(parts), "project_name": project_name}


@app.get("/api/projects/{project_name}/export/pdf")
async def api_export_project_pdf(project_name: str):
    """Export full project as a professional PDF with Turkish character support."""
    from fastapi.responses import Response
    from tools.idea_to_project import PROJECTS_DIR, PHASES
    from tools.export_service import generate_pdf

    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")

    # Build markdown content
    parts = [
        f"# Proje Raporu\n",
        f"Proje: {project_name.replace('_', ' ').title()}\n",
        "---\n",
    ]
    for i, phase in enumerate(PHASES, 1):
        filepath = project_dir / f"{phase['id']}.md"
        parts.append(f"\n## {i}. {phase['name']}\n")
        if filepath.exists():
            parts.append(filepath.read_text(encoding="utf-8"))
        else:
            parts.append("*Bu faz henüz tamamlanmadı.*")
        parts.append("\n---\n")

    md_content = "\n".join(parts)
    title = project_name.replace("_", " ").title()
    pdf_bytes = generate_pdf(md_content, title=f"Proje Raporu: {title}")

    safe_name = project_name[:40]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_rapor.pdf"'},
    )


# ── REST Endpoints: Presentation Generation ─────────────────────

class PresentationRequest(BaseModel):
    topic: str
    slide_count: int | None = None  # None = use mode default
    with_images: bool = True
    language: str = "tr"
    mode: str = "midi"  # mini, midi, maxi
    theme: str = "corporate"  # corporate, modern_dark, nature


@app.post("/api/presentation/generate")
async def api_generate_presentation(req: PresentationRequest):
    """
    Generate a PPTX presentation: deep research → agent content → AI visuals.
    Supports MINI/MIDI/MAXI modes and multiple themes.
    Returns the PPTX file as download.
    """
    from fastapi.responses import Response
    from tools.presentation_service import (
        build_presentation_prompt, parse_slide_content,
        generate_presentation, deep_research_for_presentation,
        format_research_for_prompt, MODE_CONFIG,
    )

    mode = req.mode.lower()
    if mode not in MODE_CONFIG:
        mode = "midi"
    cfg = MODE_CONFIG[mode]
    slide_count = req.slide_count or cfg["default_slides"]

    # Step 0: Deep Research — depth scales with mode
    research_context = ""
    try:
        research = await deep_research_for_presentation(
            req.topic, language=req.language,
            max_queries=cfg["research_queries"],
            mode=mode,
        )
        research_context = format_research_for_prompt(research)
    except Exception as e:
        print(f"[API] Presentation deep research failed: {e}")

    # Step 1: Use agent to create slide content DIRECTLY (not through orchestrator)
    from pipelines.engine import PipelineEngine
    from core.models import Thread as ThreadModel, AgentRole

    thread = ThreadModel()
    engine = PipelineEngine()

    prompt = build_presentation_prompt(
        req.topic, slide_count, req.language,
        research_context=research_context,
        mode=mode,
    )

    # Use thinker for MIDI/MAXI, researcher for MINI
    if mode in ("midi", "maxi"):
        content_agent = engine.get_agent(AgentRole.THINKER)
    else:
        content_agent = engine.get_agent(AgentRole.RESEARCHER)

    raw_content = await content_agent.execute(prompt, thread)

    # Fallback if primary agent failed
    if not raw_content or raw_content.startswith("[Error]") or len(raw_content.strip()) < 50:
        if mode in ("midi", "maxi"):
            content_agent = engine.get_agent(AgentRole.RESEARCHER)
        else:
            content_agent = engine.get_agent(AgentRole.THINKER)
        raw_content = await content_agent.execute(prompt, thread)

    # Step 2: Parse agent output into structured slides
    slides_data = parse_slide_content(raw_content)

    # Fallback: if parsing failed, create basic slides from raw content
    if not slides_data:
        paragraphs = [p.strip() for p in raw_content.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs[:slide_count], 1):
            lines = [l.strip() for l in para.split("\n") if l.strip()]
            title = lines[0][:60] if lines else f"Slayt {i}"
            bullets = lines[1:6] if len(lines) > 1 else [para[:100]]
            slides_data.append({
                "num": i,
                "title": title,
                "bullets": bullets,
                "image_prompt": f"Professional visual about {req.topic}",
                "is_section": False,
                "quote": None,
                "data_highlights": [],
            })

    # Step 3: Generate PPTX with images and theme
    pptx_bytes = await generate_presentation(
        slides_data=slides_data,
        title=req.topic,
        subtitle=f"{cfg['emoji']} {cfg['label']} | {len(slides_data)} Slayt | AI Destekli Sunum",
        with_images=req.with_images,
        theme=req.theme,
    )

    safe_name = re.sub(r'[^\w\-]', '_', req.topic[:40].lower())
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_{mode}_sunum.pptx"'},
    )


# ── Presentation File Endpoints ─────────────────────────────────

@app.get("/api/presentations")
async def api_list_presentations():
    """List all generated presentations."""
    pres_dir = Path(__file__).parent.parent / "data" / "presentations"
    if not pres_dir.exists():
        return []
    files = sorted(pres_dir.glob("*.pptx"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {"name": f.stem, "filename": f.name, "size_kb": round(f.stat().st_size / 1024)}
        for f in files
    ]


@app.get("/api/presentations/{filename}/download")
async def api_download_presentation(filename: str):
    """Download a generated PPTX file."""
    from fastapi.responses import FileResponse
    pres_dir = Path(__file__).parent.parent / "data" / "presentations"
    filepath = pres_dir / filename
    if not filepath.exists() or not filepath.suffix == ".pptx":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Presentation not found")
    return FileResponse(
        path=str(filepath),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )


@app.get("/api/presentations/{filename}/pdf")
async def api_presentation_pdf(filename: str):
    """Export a PPTX presentation as a professional PDF with slide content."""
    from fastapi.responses import Response
    from tools.export_service import generate_presentation_pdf

    pres_dir = Path(__file__).parent.parent / "data" / "presentations"
    filepath = pres_dir / filename
    if not filepath.exists() or not filepath.suffix == ".pptx":
        raise HTTPException(status_code=404, detail="Presentation not found")

    title = filename.replace("_", " ").replace(".pptx", "").strip()
    pdf_bytes = generate_presentation_pdf(str(filepath), title=title)
    pdf_name = filename.replace(".pptx", ".pdf")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{pdf_name}"'},
    )


# ── Generic Export Endpoints ─────────────────────────────────────

class ExportPdfRequest(BaseModel):
    markdown: str
    title: str = "Rapor"


@app.post("/api/export/pdf")
async def api_export_pdf(req: ExportPdfRequest):
    """Convert any markdown content to professional PDF."""
    from fastapi.responses import Response
    from tools.export_service import generate_pdf

    pdf_bytes = generate_pdf(req.markdown, title=req.title)
    safe_name = re.sub(r'[^\w\-]', '_', req.title[:40].lower())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
    )


class ExportHtmlRequest(BaseModel):
    markdown: str
    title: str = "Rapor"


@app.post("/api/export/html")
async def api_export_html(req: ExportHtmlRequest):
    """Convert any markdown content to a standalone styled HTML report."""
    from fastapi.responses import Response
    from tools.export_service import generate_html

    html_content = generate_html(req.markdown, title=req.title)
    safe_name = re.sub(r'[^\w\-]', '_', req.title[:40].lower())
    return Response(
        content=html_content.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.html"'},
    )


# ── WebSocket: Real-time Agent Execution ─────────────────────────

class WSLiveMonitor:
    """WebSocket-based live monitor replacing Streamlit's LiveMonitor."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self._stop = False

    def should_stop(self) -> bool:
        return self._stop

    def request_stop(self):
        self._stop = True

    async def _send(self, data: dict):
        try:
            await self.ws.send_json(data)
        except Exception:
            pass

    def start(self, task_description: str):
        asyncio.ensure_future(self._send({
            "type": "monitor_start",
            "description": task_description,
        }))

    def emit(self, event_type: str, agent: str, content: str, **extra):
        asyncio.ensure_future(self._send({
            "type": "live_event",
            "event_type": event_type,
            "agent": agent,
            "content": content,
            "extra": extra,
            "timestamp": time.time(),
        }))

    def complete(self, summary: str = ""):
        asyncio.ensure_future(self._send({
            "type": "monitor_complete",
            "summary": summary,
        }))

    def error(self, message: str):
        asyncio.ensure_future(self._send({
            "type": "monitor_error",
            "message": message,
        }))


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    """
    WebSocket endpoint for real-time agent execution.
    Client sends: {"message": "...", "thread_id": "...", "pipeline_type": "auto"}
    Server streams: live events, then final result.
    """
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type", "chat")

            if msg_type == "stop":
                # Client requests stop
                if hasattr(ws, "_monitor") and ws._monitor:
                    ws._monitor.request_stop()
                continue

            if msg_type == "ping":
                await ws.send_json({"type": "pong"})
                continue

            # Chat message
            message = data.get("message", "")
            thread_id = data.get("thread_id")
            pipeline_str = data.get("pipeline_type", "auto")
            user_id = data.get("user_id", "")

            if not message:
                await ws.send_json({"type": "error", "message": "Empty message"})
                continue

            # Load or create thread
            thread = load_thread(thread_id, user_id=user_id or None) if thread_id else None
            if not thread:
                thread = Thread()

            # Create WS monitor
            monitor = WSLiveMonitor(ws)
            ws._monitor = monitor
            monitor.start(message)

            try:
                from agents.orchestrator import OrchestratorAgent

                orchestrator = OrchestratorAgent()
                forced_pipe = None
                if pipeline_str != "auto":
                    try:
                        forced_pipe = PipelineType(pipeline_str)
                    except ValueError:
                        pass

                result = await orchestrator.route_and_execute(
                    message, thread,
                    live_monitor=monitor,
                    forced_pipeline=forced_pipe,
                    user_id=user_id or None,
                )
                save_thread(thread, user_id=user_id or None)

                if monitor.should_stop():
                    monitor.error("Kullanıcı tarafından durduruldu")
                else:
                    monitor.complete(result[:80] if result else "")

                # Send final result + full thread state
                await ws.send_json({
                    "type": "result",
                    "thread_id": thread.id,
                    "result": result,
                    "thread": thread.model_dump(mode="json"),
                })

            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                monitor.error(err)
                await ws.send_json({
                    "type": "error",
                    "message": err,
                    "traceback": traceback.format_exc(),
                    "thread_id": thread.id,
                })

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ── Health ───────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "agents": len(MODELS), "pipelines": len(PipelineType)}
