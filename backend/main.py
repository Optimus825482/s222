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
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from fastapi import Depends, FastAPI, Header, WebSocket, WebSocketDisconnect, HTTPException
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

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ─────────────────────────────────────────────────────────

# Precomputed bcrypt hash for "518518" (backward compatibility)
_BCRYPT_518518 = "$2b$12$.aDl7KHhQH7/x67LuKwnE.RKH7zrd5ezNuSNX/yS.MwoKEI2oiviK"

USERS = {
    "erkan": {
        "password_hash": _BCRYPT_518518,
        "full_name": "Erkan Erdem",
        "user_id": "erkan",
    },
    "yigit": {
        "password_hash": _BCRYPT_518518,
        "full_name": "Yiğit Avcı",
        "user_id": "yigit",
    },
}

# In-memory token store: token -> user_id
_active_tokens: dict[str, str] = {}
_revoked_tokens: set[str] = set()

_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(7 * 24 * 60 * 60)))
_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", "dev-insecure-change-me")


def _issue_signed_token(user_id: str, ttl_seconds: int = _TOKEN_TTL_SECONDS) -> str:
    """Create stateless signed token: v1.<b64(user_id)>.exp.signature"""
    exp = int(time.time()) + int(ttl_seconds)
    user_b64 = (
        base64.urlsafe_b64encode(user_id.encode("utf-8")).decode("ascii").rstrip("=")
    )
    body = f"{user_b64}.{exp}"
    sig = hmac.new(
        _TOKEN_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"v1.{body}.{sig}"


def _validate_signed_token(token: str) -> str | None:
    """Return user_id if token is valid and not expired/revoked, otherwise None."""
    if not token or token in _revoked_tokens:
        return None
    if not token.startswith("v1."):
        return None

    parts = token.split(".")
    if len(parts) != 4:
        return None

    _, user_b64, exp_raw, sig = parts
    body = f"{user_b64}.{exp_raw}"
    expected_sig = hmac.new(
        _TOKEN_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None

    try:
        exp = int(exp_raw)
    except ValueError:
        return None
    if exp < int(time.time()):
        return None

    # Restore base64 padding before decode.
    padded = user_b64 + "=" * (-len(user_b64) % 4)
    try:
        user_id = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except Exception:
        return None

    return user_id if user_id in USERS else None


def _extract_bearer_token(authorization: str | None) -> str:
    raw = (authorization or "").strip()
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    return ""


class LoginRequest(BaseModel):
    username: str
    password: str


def _get_user_from_token(token: str) -> dict | None:
    if not token:
        return None

    # Backward-compatibility: old in-memory session tokens.
    user_id = _active_tokens.get(token)
    if user_id:
        return USERS.get(user_id)

    # Preferred: stateless signed token.
    user_id = _validate_signed_token(token)
    if not user_id:
        return None
    return USERS.get(user_id)


def get_current_user(authorization: str | None = Header(None, alias="Authorization")) -> dict:
    """Extract Bearer token, resolve user from _active_tokens + USERS; raise 401 if invalid."""
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(401, "Missing or invalid Authorization header")
    user = _get_user_from_token(token)
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return {"user_id": user["user_id"], "full_name": user["full_name"]}


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
    user_id: str = ""


class RAGQueryRequest(BaseModel):
    query: str
    max_results: int = 5
    user_id: str = ""


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
    stored = user["password_hash"]
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        ok = bcrypt.checkpw(req.password.encode(), stored.encode())
    else:
        import hashlib
        ok = hashlib.sha256(req.password.encode()).hexdigest() == stored
    if not ok:
        raise HTTPException(401, "Şifre hatalı")
    token = _issue_signed_token(user["user_id"])
    # Keep compatibility with old lookup path (also supports explicit logout revocation workflows).
    _active_tokens[token] = user["user_id"]
    return {
        "token": token,
        "user_id": user["user_id"],
        "full_name": user["full_name"],
    }


@app.post("/api/auth/logout")
async def api_logout(authorization: str | None = Header(None, alias="Authorization")):
    token = _extract_bearer_token(authorization)
    _active_tokens.pop(token, None)
    if token:
        _revoked_tokens.add(token)
    return {"ok": True}


@app.get("/api/auth/me")
async def api_me(authorization: str | None = Header(None, alias="Authorization")):
    token = _extract_bearer_token(authorization)
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
async def api_list_threads(user: dict = Depends(get_current_user), limit: int = 20):
    return list_threads(limit=limit, user_id=user["user_id"])


@app.post("/api/threads")
async def api_create_thread(user: dict = Depends(get_current_user)):
    thread = Thread()
    save_thread(thread, user_id=user["user_id"])
    return {"id": thread.id}


@app.get("/api/threads/{thread_id}")
async def api_get_thread(thread_id: str, user: dict = Depends(get_current_user)):
    thread = load_thread(thread_id, user_id=user["user_id"])
    if not thread:
        raise HTTPException(404, "Thread not found")
    return thread.model_dump(mode="json")


@app.delete("/api/threads/{thread_id}")
async def api_delete_thread(thread_id: str, user: dict = Depends(get_current_user)):
    ok = delete_thread(thread_id, user_id=user["user_id"])
    if not ok:
        raise HTTPException(404, "Thread not found")
    return {"deleted": True}


@app.delete("/api/threads")
async def api_delete_all_threads(user: dict = Depends(get_current_user)):
    count = delete_all_threads(user_id=user["user_id"])
    return {"deleted": count}


# ── REST Endpoints: Tools (RAG, Skills, MCP, Teachability, Eval) ─

@app.post("/api/rag/ingest")
async def api_rag_ingest(req: RAGIngestRequest, user: dict = Depends(get_current_user)):
    from tools.rag import ingest_document
    result = ingest_document(req.content, req.title, req.source, user_id=user["user_id"])
    return result


@app.post("/api/rag/query")
async def api_rag_query(req: RAGQueryRequest, user: dict = Depends(get_current_user)):
    from tools.rag import query_documents
    results = query_documents(req.query, req.max_results, user_id=user["user_id"])
    return results


@app.get("/api/rag/documents")
async def api_rag_documents(user: dict = Depends(get_current_user)):
    try:
        from tools.rag import list_documents
        return list_documents(user_id=user["user_id"])
    except Exception:
        return []


@app.get("/api/skills")
async def api_list_skills():
    try:
        from tools.dynamic_skills import list_skills
        return list_skills()
    except Exception:
        return []


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
        return {"status": "ok", "migrated": result}
    except Exception as e:
        raise HTTPException(503, f"Migration error: {e}")


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
    """Per-agent evaluation stats (task count, avg score)."""
    try:
        from tools.agent_eval import get_agent_stats
        return get_agent_stats()
    except Exception:
        return {"total_evals": 0, "avg_score": 0, "evals": []}


@app.get("/api/eval/baseline")
async def api_eval_baseline(agent_role: str | None = None):
    """
    Performance baseline report (agent-orchestration-improve-agent skill).
    Returns: task_success_rate_pct, user_satisfaction_score, avg_latency_ms,
    token_efficiency_ratio, total_tasks, success_count.
    """
    try:
        from tools.agent_eval import get_performance_baseline
        return get_performance_baseline(agent_role)
    except Exception as e:
        raise HTTPException(503, "Baseline unavailable") from e


# ── Memory Endpoints ─────────────────────────────────────────────

@app.get("/api/memory/stats")
async def api_memory_stats(user: dict = Depends(get_current_user)):
    """Get layered memory statistics."""
    try:
        from tools.memory import get_memory_stats
        return get_memory_stats()
    except Exception as e:
        return {"error": str(e), "total_memories": 0}


@app.get("/api/memory/layers")
async def api_memory_layers(user: dict = Depends(get_current_user)):
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
async def api_delete_memory(memory_id: int, user: dict = Depends(get_current_user)):
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

def _resolve_project_path(project_name: str):
    """Resolve project path and ensure it is under PROJECTS_DIR (path traversal safe)."""
    from tools.idea_to_project import PROJECTS_DIR
    base = PROJECTS_DIR.resolve()
    path = (PROJECTS_DIR / project_name).resolve()
    if not path.is_relative_to(base) or path == base or not path.exists() or not path.is_dir():
        raise HTTPException(404, "Project not found")
    return path


@app.get("/api/projects")
async def api_list_projects(user: dict = Depends(get_current_user)):
    """List all generated idea-to-project outputs."""
    from tools.idea_to_project import PROJECTS_DIR, PHASES
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    # Sort by creation time (oldest first) so the last element is the newest
    dirs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    dirs.sort(key=lambda d: d.stat().st_ctime)
    for d in dirs:
        phases_done = [f.stem for f in d.glob("*.md")]
        projects.append({
            "name": d.name,
            "phases": phases_done,
            "phase_count": len(phases_done),
            "total_phases": len(PHASES),
        })
    return projects


@app.get("/api/projects/{project_name}/export")
async def api_export_project(project_name: str, user: dict = Depends(get_current_user)):
    """Export full project as a single combined Markdown document."""
    from tools.idea_to_project import PROJECTS_DIR, PHASES
    project_dir = _resolve_project_path(project_name)

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
async def api_export_project_pdf(project_name: str, user: dict = Depends(get_current_user)):
    """Export full project as a professional PDF with Turkish character support."""
    from fastapi.responses import Response
    from tools.idea_to_project import PROJECTS_DIR, PHASES
    from tools.export_service import generate_pdf

    project_dir = _resolve_project_path(project_name)

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

def _resolve_presentation_path(filename: str) -> Path:
    """Resolve presentation filename to path under pres_dir (base name only, no path traversal)."""
    safe_name = Path(filename).name
    pres_dir = Path(__file__).parent.parent / "data" / "presentations"
    pres_dir = pres_dir.resolve()
    filepath = (pres_dir / safe_name).resolve()
    if not filepath.is_relative_to(pres_dir) or not filepath.exists() or filepath.suffix.lower() != ".pptx":
        raise HTTPException(404, "Presentation not found")
    return filepath


def _resolve_image_path(filename: str) -> Path:
    """Resolve image filename to path under images_dir (base name only, no path traversal)."""
    safe_name = Path(filename).name
    images_dir = Path(__file__).parent.parent / "data" / "images"
    images_dir = images_dir.resolve()
    filepath = (images_dir / safe_name).resolve()
    if not filepath.is_relative_to(images_dir) or not filepath.exists():
        raise HTTPException(404, "Image not found")
    return filepath


@app.get("/api/presentations")
async def api_list_presentations(user: dict = Depends(get_current_user)):
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
async def api_download_presentation(filename: str, user: dict = Depends(get_current_user)):
    """Download a generated PPTX file."""
    from fastapi.responses import FileResponse
    filepath = _resolve_presentation_path(filename)
    return FileResponse(
        path=str(filepath),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filepath.name,
    )


@app.get("/api/images/{filename}/download")
async def api_download_image(filename: str, user: dict = Depends(get_current_user)):
    """Download a generated image file."""
    from fastapi.responses import FileResponse
    filepath = _resolve_image_path(filename)
    suffix = filepath.suffix.lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    media_type = media_types.get(suffix, "image/jpeg")
    return FileResponse(
        path=str(filepath),
        media_type=media_type,
        filename=filepath.name,
    )


@app.get("/api/presentations/{filename}/pdf")
async def api_presentation_pdf(filename: str, user: dict = Depends(get_current_user)):
    """Export a PPTX presentation as a professional PDF with slide content."""
    from fastapi.responses import Response
    from tools.export_service import generate_presentation_pdf

    filepath = _resolve_presentation_path(filename)

    title = filepath.stem.replace("_", " ")
    pdf_bytes = generate_presentation_pdf(str(filepath), title=title)
    pdf_name = filepath.name.replace(".pptx", ".pdf")

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
async def api_export_pdf(req: ExportPdfRequest, user: dict = Depends(get_current_user)):
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
async def api_export_html(req: ExportHtmlRequest, user: dict = Depends(get_current_user)):
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

    def __init__(self, ws: WebSocket, events_list: list | None = None):
        self.ws = ws
        self._stop = False
        self._events_list = events_list or []

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
        payload = {
            "type": "live_event",
            "event_type": event_type,
            "agent": agent,
            "content": content,
            "extra": extra,
            "timestamp": time.time(),
        }
        self._events_list.append(payload)
        asyncio.ensure_future(self._send(payload))

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
    Auth: pass token via query ?token=... or in first message {"token": "..."}.
    Client sends: {"message": "...", "thread_id": "...", "pipeline_type": "auto"}
    Server streams: live events, then final result.
    """
    # Optional token from query
    token = (ws.query_params.get("token") or "").strip()
    user_id: str | None = None
    if token:
        user = _get_user_from_token(token)
        if user:
            user_id = user["user_id"]

    await ws.accept()
    ws.state.run_task = None
    ws.state.live_events = []

    async def _execute_run(
        message: str,
        thread: Thread,
        monitor: WSLiveMonitor,
        pipeline_str: str,
        effective_user_id: str | None,
    ):
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
                message,
                thread,
                live_monitor=monitor,
                forced_pipeline=forced_pipe,
                user_id=effective_user_id,
            )
            save_thread(thread, user_id=effective_user_id)

            if monitor.should_stop():
                monitor.error("Kullanıcı tarafından durduruldu")
            else:
                monitor.complete(result[:80] if result else "")

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
        finally:
            ws.state.run_task = None

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type", "chat")

            # If we don't have user_id yet, allow first message to carry token
            if user_id is None and "token" in data:
                token = (data.get("token") or "").strip()
                user = _get_user_from_token(token) if token else None
                if user:
                    user_id = user["user_id"]
                else:
                    await ws.close(code=4001)
                    return

            # Require auth for chat: if no valid user_id after first real message, reject
            if msg_type == "chat" and user_id is None:
                await ws.close(code=4001)
                return

            if msg_type == "stop":
                monitor_obj = getattr(ws.state, "monitor", None)
                if monitor_obj:
                    monitor_obj.request_stop()
                continue

            if msg_type == "ping":
                await ws.send_json({"type": "pong"})
                continue

            # Orchestrator chat: status while run is active (or "no active task")
            if msg_type == "orchestrator_chat":
                user_msg = (data.get("message") or "").strip()
                run_task = getattr(ws.state, "run_task", None)
                events = getattr(ws.state, "live_events", [])
                if run_task and not run_task.done():
                    # Build status from last events
                    step_count = len(events)
                    last_agents = list(dict.fromkeys(e.get("agent", "") for e in events[-20:] if e.get("agent")))
                    status_lines = [
                        f"Görev devam ediyor. Toplam {step_count} adım.",
                        f"Son etkileşimler: {', '.join(last_agents[-5:]) or '—'}.",
                    ]
                    if user_msg.lower() in ("durum", "status", "nerede", "ne oldu", "?"):
                        reply = "\n".join(status_lines)
                    else:
                        reply = "\n".join(status_lines) + "\n\nEk talimatınız kaydedildi; mevcut görev bittikten sonra yeni bir mesaj olarak gönderebilirsiniz."
                    await ws.send_json({
                        "type": "orchestrator_chat_reply",
                        "content": reply,
                        "is_status": True,
                    })
                else:
                    await ws.send_json({
                        "type": "orchestrator_chat_reply",
                        "content": "Şu an aktif görev yok. Yeni görev için ana alandan mesaj gönderin.",
                        "is_status": False,
                    })
                continue

            # Chat message (main task)
            message = data.get("message", "")
            thread_id = data.get("thread_id")
            pipeline_str = data.get("pipeline_type", "auto")
            effective_user_id = user_id or data.get("user_id", "") or None

            if not message:
                await ws.send_json({"type": "error", "message": "Empty message"})
                continue

            active_task = getattr(ws.state, "run_task", None)
            if active_task is not None and not active_task.done():
                await ws.send_json({
                    "type": "error",
                    "message": "Bir görev zaten çalışıyor. Durdurmak için Durdur'a basın veya Orkestratör sohbetinden durum sorun.",
                })
                continue

            thread = load_thread(thread_id, user_id=user_id or None) if thread_id else None
            if not thread:
                thread = Thread()

            ws.state.live_events = []
            monitor = WSLiveMonitor(ws, ws.state.live_events)
            ws.state.monitor = monitor
            monitor.start(message)

            ws.state.run_task = asyncio.create_task(
                _execute_run(message, thread, monitor, pipeline_str, effective_user_id),
            )

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.websocket("/api/ws/chat")
async def ws_chat_api_alias(ws: WebSocket):
    """Alias route for deployments where only /api/* is routed to backend."""
    await ws_chat(ws)


# ── Health ───────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "agents": len(MODELS), "pipelines": len(PipelineType)}
