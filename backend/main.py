"""
Multi-Agent Ops Center — FastAPI Backend.
WebSocket streaming + REST API wrapping existing agent/pipeline/tool infrastructure.
"""
# RELOAD_TRIGGER: force uvicorn reload — 2026-03-07

import sys
from pathlib import Path

# Add parent dir so we can import existing modules (agents, pipelines, tools, core, config)
_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

import asyncio
import base64
import uuid
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Depends, FastAPI, Header, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import MODELS
from core.models import Thread, PipelineType, EventType, AgentRole, AgentMetrics
from core.state import save_thread, load_thread, list_threads, delete_thread, delete_all_threads


# ── Rate Limiting ────────────────────────────────────────────────

from collections import defaultdict

class _RateLimiter:
    """Simple in-memory sliding-window rate limiter."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        hits = self._hits[key]
        # Prune old entries
        self._hits[key] = [t for t in hits if t > cutoff]
        if len(self._hits[key]) >= self._max:
            return False
        self._hits[key].append(now)
        return True

_rate_limiter = _RateLimiter(max_requests=120, window_seconds=60)


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

_APP_START_TIME = time.time()

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_rate_limit_middleware(request, call_next):
    """Per-IP + per-user rate limiting + security headers for all responses."""
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        if not _rate_limiter.is_allowed(f"ip:{client_ip}"):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": "Çok fazla istek. Lütfen biraz bekleyin."},
            )
        # Per-user rate limiting via Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            user_id = _validate_signed_token(token)
            if user_id and not _rate_limiter.is_allowed(f"user:{user_id}"):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Kullanıcı istek limiti aşıldı. Lütfen biraz bekleyin."},
                )
    response = await call_next(request)
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


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


@app.get("/api/skills/recommendations")
async def get_skill_recommendations(
    query: str = "",
    user: dict = Depends(get_current_user),
):
    """Recommend skills based on query context."""
    _audit("skill_recommendation", user["user_id"], detail=query[:100])
    try:
        from tools.dynamic_skills import search_skills
        from tools.agent_eval import get_best_agent_for_task, detect_task_type

        skills = search_skills(query, max_results=5) if query else []

        best_agent = None
        task_type = None
        if query:
            task_type = detect_task_type(query)
            best_agent = get_best_agent_for_task(task_type)

        # Inject recommended_agent into each skill
        for skill in skills:
            if "recommended_agent" not in skill or not skill["recommended_agent"]:
                skill["recommended_agent"] = best_agent

        return skills

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill recommendation failed: {e}")


@app.post("/api/skills/hygiene")
async def api_skill_hygiene(dry_run: bool = False):
    """Run autonomous skill hygiene check — validates and cleans junk skills."""
    try:
        from tools.skill_hygiene import run_hygiene_check
        return run_hygiene_check(dry_run=dry_run)
    except Exception as e:
        raise HTTPException(503, f"Skill hygiene error: {e}")


@app.get("/api/skills/hygiene/validate/{skill_id}")
async def api_validate_skill(skill_id: str):
    """Validate a single skill and return quality report."""
    try:
        from tools.dynamic_skills import get_skill
        from tools.skill_hygiene import validate_skill
        skill = get_skill(skill_id)
        if not skill:
            raise HTTPException(404, "Skill not found")
        return validate_skill(skill)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Validation error: {e}")


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


# ── Workflow Engine Endpoints ────────────────────────────────────

@app.get("/api/workflows/templates")
async def api_workflow_templates():
    """List available workflow templates."""
    try:
        from tools.workflow_engine import get_workflow_templates
        return get_workflow_templates()
    except Exception as e:
        raise HTTPException(503, f"Workflow engine error: {e}")


@app.get("/api/workflows/history")
async def api_workflow_history(limit: int = 20, user: dict = Depends(get_current_user)):
    """List recent workflow execution results."""
    try:
        from tools.workflow_engine import list_workflow_results
        return list_workflow_results(limit=limit)
    except Exception as e:
        return []


class WorkflowRunRequest(BaseModel):
    template: str
    variables: dict = {}
    custom_steps: list[dict] | None = None


@app.post("/api/workflows/run")
async def api_run_workflow(req: WorkflowRunRequest, user: dict = Depends(get_current_user)):
    """Execute a workflow template or custom workflow."""
    try:
        from tools.workflow_engine import (
            WORKFLOW_TEMPLATES, create_workflow, execute_workflow, WorkflowStep, Workflow
        )
        from core.models import Thread as ThreadModel

        if req.template != "custom" and req.template in WORKFLOW_TEMPLATES:
            template = WORKFLOW_TEMPLATES[req.template]
            steps = [WorkflowStep(**s) for s in template["steps"]]
            workflow = Workflow(
                workflow_id=f"{req.template}-{int(__import__('time').time())}",
                name=template["name"],
                description=template["description"],
                steps=steps,
                variables=req.variables,
            )
        elif req.template == "custom" and req.custom_steps:
            steps = [WorkflowStep(**s) for s in req.custom_steps]
            workflow = Workflow(
                workflow_id=f"custom-{int(__import__('time').time())}",
                name="Custom Workflow",
                description="User-defined workflow",
                steps=steps,
                variables=req.variables,
            )
        else:
            raise HTTPException(400, f"Unknown template: {req.template}")

        thread = ThreadModel()
        result = await execute_workflow(workflow, thread)
        return {
            "workflow_id": result.workflow_id,
            "status": result.status,
            "step_results": result.step_results,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "variables": result.variables,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Workflow execution error: {e}")


# ── Domain Expert Endpoints ──────────────────────────────────────

@app.get("/api/domains")
async def api_list_domains():
    """List available domain expertise modules."""
    try:
        from tools.domain_skills import list_domains
        return list_domains()
    except Exception as e:
        raise HTTPException(503, f"Domain skills error: {e}")


@app.get("/api/domains/{domain_id}/tools")
async def api_domain_tools(domain_id: str):
    """List tools available in a specific domain."""
    try:
        from tools.domain_skills import get_domain_tools
        tools = get_domain_tools(domain_id)
        if tools is None:
            raise HTTPException(404, f"Domain not found: {domain_id}")
        return tools
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Domain skills error: {e}")


class DomainExpertRequest(BaseModel):
    domain: str
    tool_name: str
    arguments: dict = {}


@app.post("/api/domains/execute")
async def api_execute_domain_tool(req: DomainExpertRequest, user: dict = Depends(get_current_user)):
    """Execute a domain-specific tool."""
    try:
        from tools.domain_skills import execute_domain_tool
        result = await execute_domain_tool(req.domain, req.tool_name, req.arguments)
        return result
    except Exception as e:
        raise HTTPException(503, f"Domain execution error: {e}")

# ── Domain Auto-Discovery & Marketplace ──────────────────────────

class DomainDetectRequest(BaseModel):
    query: str
    top_k: int = 3

@app.post("/api/domains/auto-detect")
async def api_auto_detect_domain(req: DomainDetectRequest, user: dict = Depends(get_current_user)):
    """Auto-detect relevant domain(s) from a user query."""
    try:
        from tools.domain_skills import auto_detect_domain
        results = auto_detect_domain(req.query, req.top_k)
        return {"query": req.query, "matches": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(503, f"Domain detection error: {e}")

@app.get("/api/domains/marketplace")
async def api_domain_marketplace():
    """Get all domain skills with marketplace metadata."""
    try:
        from tools.domain_skills import get_marketplace_data
        return get_marketplace_data()
    except Exception as e:
        raise HTTPException(503, f"Marketplace error: {e}")

@app.post("/api/domains/discover")
async def api_discover_domains(user: dict = Depends(get_current_user)):
    """Trigger domain skill auto-discovery scan."""
    try:
        from tools.domain_skills import discover_domain_skills
        return discover_domain_skills()
    except Exception as e:
        raise HTTPException(503, f"Discovery error: {e}")

@app.post("/api/domains/{domain_id}/toggle")
async def api_toggle_domain(domain_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Enable or disable a domain skill."""
    try:
        from tools.domain_skills import toggle_domain_skill
        enabled = body.get("enabled", True)
        return toggle_domain_skill(domain_id, enabled)
    except Exception as e:
        raise HTTPException(503, f"Toggle error: {e}")

@app.get("/api/marketplace/catalog")
async def api_marketplace_catalog(
    category: str | None = None,
    search: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get unified skill marketplace catalog."""
    try:
        from tools.domain_skills import get_marketplace_catalog
        catalog = get_marketplace_catalog()

        # Filter by category
        if category and category != "all":
            catalog = [item for item in catalog if item.get("category") == category]

        # Search filter
        if search:
            search_lower = search.lower()
            catalog = [
                item for item in catalog
                if search_lower in item.get("name", "").lower()
                or search_lower in item.get("name_tr", "").lower()
                or search_lower in item.get("description", "").lower()
                or any(search_lower in tag.lower() for tag in item.get("tags", []))
            ]

        return {
            "items": catalog,
            "total": len(catalog),
            "categories": list(set(item.get("category", "other") for item in catalog)),
        }
    except Exception as e:
        raise HTTPException(503, f"Marketplace error: {e}")

@app.get("/api/marketplace/stats")
async def api_marketplace_stats(user: dict = Depends(get_current_user)):
    """Get marketplace statistics."""
    try:
        from tools.domain_skills import list_domains, get_marketplace_catalog
        domains = list_domains()
        catalog = get_marketplace_catalog()
        domain_items = [c for c in catalog if c["type"] == "domain"]
        skill_items = [c for c in catalog if c["type"] == "skill"]
        total_tools = sum(d.get("tool_count", 0) for d in domains)
        return {
            "total_items": len(catalog),
            "domain_count": len(domain_items),
            "skill_count": len(skill_items),
            "total_tools": total_tools,
            "categories": list(set(c.get("category", "other") for c in catalog)),
            "installed_count": len([c for c in catalog if c.get("installed")]),
        }
    except Exception as e:
        raise HTTPException(503, f"Marketplace stats error: {e}")



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
        return []


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


# ── Memory Advanced Endpoints ────────────────────────────────────

@app.get("/api/memory/correlate")
async def api_memory_correlate(
    query: str,
    max_results: int = 10,
    time_window_hours: int | None = None,
    user: dict = Depends(get_current_user),
):
    """Find correlated memories across layers and categories."""
    try:
        from tools.memory import correlate_memories
        return correlate_memories(query, max_results, time_window_hours)
    except Exception as e:
        return {"clusters": [], "total_found": 0, "error": str(e)}


@app.get("/api/memory/timeline")
async def api_memory_timeline(
    hours: int = 24,
    group_by: str = "hour",
    user: dict = Depends(get_current_user),
):
    """Get memory creation timeline grouped by time intervals."""
    if group_by not in ("hour", "day", "category"):
        raise HTTPException(400, "group_by must be 'hour', 'day', or 'category'")
    try:
        from tools.memory import get_memory_timeline
        return get_memory_timeline(hours, group_by)
    except Exception as e:
        return []


@app.get("/api/memory/{memory_id}/related")
async def api_memory_related(
    memory_id: int,
    max_results: int = 5,
    user: dict = Depends(get_current_user),
):
    """Find memories related to a specific memory."""
    try:
        from tools.memory import find_related_memories
        return find_related_memories(memory_id, max_results)
    except Exception as e:
        return []


# ── REST Endpoints: Project Export ───────────────────────────────

def _resolve_project_path(project_name: str):
    """Resolve project path and ensure it is under PROJECTS_DIR (path traversal safe)."""
    from tools.idea_to_project import PROJECTS_DIR
    project_name = project_name.strip()
    if "\x00" in project_name or ".." in project_name or Path(project_name).is_absolute():
        raise HTTPException(status_code=400, detail="Geçersiz dosya yolu")
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
    filename = filename.strip()
    if "\x00" in filename or ".." in filename or Path(filename).is_absolute():
        raise HTTPException(status_code=400, detail="Geçersiz dosya yolu")
    safe_name = Path(filename).name
    pres_dir = Path(__file__).parent.parent / "data" / "presentations"
    pres_dir = pres_dir.resolve()
    filepath = (pres_dir / safe_name).resolve()
    if not filepath.is_relative_to(pres_dir) or not filepath.exists() or filepath.suffix.lower() != ".pptx":
        raise HTTPException(404, "Presentation not found")
    return filepath


def _resolve_image_path(filename: str) -> Path:
    """Resolve image filename to path under images_dir (base name only, no path traversal)."""
    filename = filename.strip()
    if "\x00" in filename or ".." in filename or Path(filename).is_absolute():
        raise HTTPException(status_code=400, detail="Geçersiz dosya yolu")
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

    async def _safe_ws_send(data: dict):
        """Send JSON to WS, silently ignore if connection already closed."""
        try:
            await ws.send_json(data)
        except Exception:
            pass

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

            # PII masking — strip personal data before sending to client
            try:
                from tools.pii_masker import mask_pii_in_response
                result = mask_pii_in_response(result)
            except Exception:
                pass  # Never break response flow for PII masker errors

            if monitor.should_stop():
                monitor.error("Kullanıcı tarafından durduruldu")
            else:
                monitor.complete(result[:80] if result else "")

            await _safe_ws_send({
                "type": "result",
                "thread_id": thread.id,
                "result": result,
                "thread": thread.model_dump(mode="json"),
            })

            # Auto-trigger post-task retrospective meeting
            try:
                task_agents = list(set(
                    e.agent_role for t in thread.tasks
                    for e in thread.events
                    if e.agent_role and e.event_type in ("agent_start", "agent_response")
                ))
                if not task_agents:
                    task_agents = ["orchestrator", "thinker"]
                total_tok = sum(t.total_tokens for t in thread.tasks)
                total_lat = sum(t.total_latency_ms for t in thread.tasks)
                last_task = thread.tasks[-1] if thread.tasks else None
                summary = last_task.user_input[:120] if last_task else message[:120]
                status = last_task.status if last_task else "completed"
                meeting = _generate_post_task_meeting(
                    task_summary=summary,
                    participating_agents=task_agents,
                    task_status=status,
                    task_duration_ms=total_lat,
                    total_tokens=total_tok,
                )
                await _safe_ws_send({
                    "type": "post_task_meeting",
                    "meeting": meeting,
                })
            except Exception:
                pass  # Never break main flow for meeting generation
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            monitor.error(err)
            await _safe_ws_send({
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
                await _safe_ws_send({"type": "pong"})
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
                    await _safe_ws_send({
                        "type": "orchestrator_chat_reply",
                        "content": reply,
                        "is_status": True,
                    })
                else:
                    await _safe_ws_send({
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

            # Per-user WebSocket rate limiting (20 messages/minute)
            if effective_user_id and not _rate_limiter.is_allowed(f"ws:{effective_user_id}"):
                await _safe_ws_send({
                    "type": "error",
                    "message": "İstek limiti aşıldı. Lütfen biraz bekleyin.",
                })
                continue

            if not message:
                await _safe_ws_send({"type": "error", "message": "Empty message"})
                continue

            active_task = getattr(ws.state, "run_task", None)
            if active_task is not None and not active_task.done():
                await _safe_ws_send({
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


# ── Cache Management ─────────────────────────────────────────────

@app.get("/api/cache/stats")
async def api_cache_stats(user: dict = Depends(get_current_user)):
    """Get response cache statistics."""
    from tools.cache import cache_stats
    return cache_stats()


@app.post("/api/cache/clear")
async def api_cache_clear(user: dict = Depends(get_current_user)):
    """Clear the response cache."""
    from tools.cache import clear_cache
    cleared = await clear_cache()
    _audit("cache_clear", user["user_id"], f"Cleared {cleared} entries")
    return {"cleared": cleared}


# ── Circuit Breaker ──────────────────────────────────────────────

@app.get("/api/circuit-breaker/status")
async def api_circuit_breaker_status(user: dict = Depends(get_current_user)):
    """Get circuit breaker status for all agents."""
    from tools.circuit_breaker import get_circuit_breaker
    cb = get_circuit_breaker()
    return {
        "breakers": cb.status(),
        "summary": {
            role: data["state"]
            for role, data in cb.status().items()
        },
    }


@app.post("/api/circuit-breaker/reset")
async def api_circuit_breaker_reset(
    agent_role: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Reset circuit breaker for a specific agent or all agents."""
    from tools.circuit_breaker import get_circuit_breaker
    cb = get_circuit_breaker()
    cb.reset(agent_role)
    _audit("circuit_breaker_reset", user["user_id"], f"Reset: {agent_role or 'all'}")
    return {"reset": agent_role or "all", "status": cb.status()}


# ── Confidence Analysis ──────────────────────────────────────────

@app.post("/api/confidence/analyze")
async def api_confidence_analyze(
    text: str,
    agent_role: str = "general",
    task_type: str = "general",
    user: dict = Depends(get_current_user),
):
    """Analyze confidence of a text output."""
    from tools.confidence import score_confidence
    return score_confidence(text, agent_role, task_type)


# ── System Overview ──────────────────────────────────────────────

@app.get("/api/system/overview")
async def api_system_overview(user: dict = Depends(get_current_user)):
    """Comprehensive system overview: agents, cache, circuit breakers."""
    from tools.cache import cache_stats
    from tools.circuit_breaker import get_circuit_breaker

    cb = get_circuit_breaker()
    cb_status = cb.status()

    # Count available vs unavailable agents
    available_agents = sum(1 for s in cb_status.values() if s["state"] == "closed")
    total_tracked = len(cb_status)

    return {
        "cache": cache_stats(),
        "circuit_breakers": cb_status,
        "agents": {
            "available": available_agents,
            "total_tracked": total_tracked,
            "all_healthy": all(s["state"] == "closed" for s in cb_status.values()) if cb_status else True,
        },
    }


@app.get("/api/sandbox/audit")
async def api_sandbox_audit(
    user: dict = Depends(get_current_user),
    limit: int = 50,
):
    """Get sandbox audit log."""
    try:
        from tools.sandbox import get_audit_log
        return {"audit_log": get_audit_log(limit)}
    except ImportError:
        return {"audit_log": [], "note": "Sandbox module not available"}


@app.get("/api/pii/stats")
async def api_pii_stats(user: dict = Depends(get_current_user)):
    """Get PII masking statistics."""
    return {
        "enabled": True,
        "supported_types": [
            "email", "phone_tr", "phone_intl", "tc_kimlik",
            "credit_card", "iban", "ip_address", "plate_tr",
        ],
    }


# ── Health ───────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "agents": len(MODELS), "pipelines": len(PipelineType)}


# ══════════════════════════════════════════════════════════════════
# New Endpoints — Agent Analytics, Skill Discovery, Security & Monitoring
# ══════════════════════════════════════════════════════════════════

from collections import deque as _deque

_AUDIT_LOG: _deque[dict[str, Any]] = _deque(maxlen=1000)
_AGENT_ROLES = ["orchestrator", "thinker", "speed", "researcher", "reasoner", "observer"]


def _audit(event_type: str, user_id: str, detail: str = "", **extra: Any) -> None:
    """Append an audit entry to the in-memory FIFO log."""
    _AUDIT_LOG.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "detail": detail,
        **extra,
    })


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── 1. Agent Performance Analytics ───────────────────────────────


@app.get("/api/agents/health")
async def get_agents_health(user: dict = Depends(get_current_user)):
    """Return health status for all agents matching frontend AgentHealth interface."""
    _audit("agents_health_check", user["user_id"])
    now = _utcnow()
    agents = []

    # Pre-fetch eval stats — tolerate missing DB gracefully
    stats_by_role: dict = {}
    try:
        from tools.agent_eval import get_agent_stats, get_performance_baseline
        stats_by_role = {s["agent_role"]: s for s in get_agent_stats()}
    except Exception:
        get_performance_baseline = None  # type: ignore[assignment]

    # Pre-fetch threads once (not per-agent)
    user_threads: list[dict] = []
    thread_cache: dict = {}
    try:
        user_threads = list_threads(limit=10, user_id=user["user_id"])
        for t_info in user_threads:
            try:
                t = load_thread(t_info["id"], user_id=user["user_id"])
                if t:
                    thread_cache[t_info["id"]] = t
            except Exception:
                continue
    except Exception:
        pass

    for role in _AGENT_ROLES:
        try:
            stat = stats_by_role.get(role, {})
            avg_score = float(stat.get("avg_score", 0) or 0)
            avg_latency = float(stat.get("avg_latency", 0) or 0)
            total_tokens = int(stat.get("total_tokens", 0) or 0)
            success_rate = round((avg_score / 5.0) * 100, 1) if avg_score else 0.0

            total_calls = int(stat.get("total_tasks", 0) or 0)
            error_count = 0
            if get_performance_baseline is not None:
                try:
                    baseline = get_performance_baseline(role)
                    total_calls = int(baseline.get("total_tasks", 0))
                    success_count = int(baseline.get("success_count", 0))
                    error_count = max(0, total_calls - success_count)
                except Exception:
                    pass

            # Determine status from cached threads
            last_active = None
            status = "offline"
            for t in thread_cache.values():
                try:
                    if role in t.agent_metrics:
                        m = t.agent_metrics[role]
                        if m.last_active and (last_active is None or m.last_active > last_active):
                            last_active = m.last_active
                except Exception:
                    continue

            if last_active:
                try:
                    delta = now - last_active
                except TypeError:
                    # Mixed timezone-aware/naive — normalize both to naive UTC
                    _now_naive = now.replace(tzinfo=None)
                    _la_naive = last_active.replace(tzinfo=None)
                    delta = _now_naive - _la_naive
                if delta < timedelta(minutes=5):
                    status = "active"
                elif delta < timedelta(minutes=30):
                    status = "idle"

            uptime_pct = 99.0 if status in ("active", "idle") else 0.0

            agents.append({
                "role": role,
                "name": MODELS.get(role, {}).get("name", role),
                "status": status,
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency,
                "total_tokens": total_tokens,
                "total_calls": total_calls,
                "error_count": error_count,
                "last_active": last_active.isoformat() if last_active else None,
                "uptime_pct": uptime_pct,
            })
        except Exception:
            # Fallback: return minimal healthy entry so frontend never gets empty
            agents.append({
                "role": role,
                "name": MODELS.get(role, {}).get("name", role),
                "status": "offline",
                "success_rate": 0.0,
                "avg_latency_ms": 0,
                "total_tokens": 0,
                "total_calls": 0,
                "error_count": 0,
                "last_active": None,
                "uptime_pct": 0.0,
            })

    return agents


@app.get("/api/agents/{role}/performance")
async def get_agent_performance(role: str, user: dict = Depends(get_current_user)):
    """Detailed performance metrics for a specific agent."""
    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {_AGENT_ROLES}")

    _audit("agent_performance_view", user["user_id"], detail=role)
    try:
        from tools.agent_eval import get_performance_baseline, get_agent_stats

        baseline = get_performance_baseline(role)
        stats = get_agent_stats(role)

        # Recent task history from threads
        recent_tasks: list[dict] = []
        try:
            user_threads = list_threads(limit=20, user_id=user["user_id"])
            for t_info in user_threads:
                thread = load_thread(t_info["id"], user_id=user["user_id"])
                if not thread:
                    continue
                for task in thread.tasks:
                    for sub in task.sub_tasks:
                        if sub.assigned_agent and sub.assigned_agent.value == role:
                            recent_tasks.append({
                                "task_id": sub.id,
                                "description": sub.description[:120],
                                "status": sub.status.value,
                                "tokens": sub.token_usage,
                                "latency_ms": sub.latency_ms,
                            })
                if len(recent_tasks) >= 20:
                    break
        except Exception:
            pass

        # Error patterns from stats
        error_patterns: list[str] = []
        for s in stats:
            score = float(s.get("avg_score", 0))
            if int(s.get("total_tasks", 0)) > 0 and score < 2.5:
                error_patterns.append(f"Low score ({score}) on {s.get('task_type', 'unknown')} tasks")

        return {
            "role": role,
            "baseline": baseline,
            "task_type_breakdown": stats,
            "recent_tasks": recent_tasks[:20],
            "error_patterns": error_patterns,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance: {e}")


@app.get("/api/agents/leaderboard")
async def get_agent_leaderboard(user: dict = Depends(get_current_user)):
    """Rank agents by success rate, speed, and efficiency."""
    _audit("leaderboard_view", user["user_id"])
    try:
        from tools.agent_eval import get_performance_baseline

        rankings: list[dict] = []
        for role in _AGENT_ROLES:
            b = get_performance_baseline(role)
            rankings.append({
                "role": role,
                "name": MODELS.get(role, {}).get("name", role),
                "score": round(
                    (b.get("task_success_rate_pct", 0) * 0.5)
                    + (max(0, 100 - (b.get("avg_latency_ms", 0) / 100)) * 0.3)
                    + (b.get("avg_score", 0) * 4),
                    1,
                ),
                "success_rate": round(b.get("task_success_rate_pct", 0), 1),
                "avg_latency_ms": round(b.get("avg_latency_ms", 0), 1),
                "efficiency": round(
                    (b.get("task_success_rate_pct", 0) / max(b.get("avg_latency_ms", 1), 1)) * 100,
                    2,
                ),
                "rank": 0,
            })

        rankings.sort(key=lambda x: x["score"], reverse=True)
        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        return rankings

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build leaderboard: {e}")


# ── 2. Auto Skill Discovery ─────────────────────────────────────


@app.post("/api/skills/auto-discover")
async def auto_discover_skills(user: dict = Depends(get_current_user)):
    """Analyze recent tasks and auto-create skills from successful patterns."""
    _audit("skill_auto_discover", user["user_id"])
    try:
        from tools.dynamic_skills import auto_create_skill_from_pattern

        discovered: list[dict] = []
        seen_descriptions: set[str] = set()

        user_threads = list_threads(limit=50, user_id=user["user_id"])
        cutoff = (_utcnow() - timedelta(days=7)).isoformat()

        for t_info in user_threads:
            created = t_info.get("created_at", "")
            if created and created < cutoff:
                continue

            thread = load_thread(t_info["id"], user_id=user["user_id"])
            if not thread:
                continue

            for task in thread.tasks:
                if task.status.value != "completed" or not task.final_result:
                    continue

                desc = task.user_input[:200].strip()
                if not desc or desc in seen_descriptions:
                    continue
                seen_descriptions.add(desc)

                # Build knowledge from subtask results
                knowledge_parts = [f"Task: {desc}"]
                tool_sequence: list[str] = []
                for sub in task.sub_tasks:
                    if sub.result:
                        knowledge_parts.append(
                            f"Agent {sub.assigned_agent.value}: {sub.result[:200]}"
                        )
                    if sub.skills:
                        tool_sequence.extend(sub.skills)

                knowledge = "\n".join(knowledge_parts[:5])
                keywords = list(set(tool_sequence))[:6] or ["auto-discovered"]

                try:
                    skill = auto_create_skill_from_pattern(
                        pattern_description=desc,
                        knowledge=knowledge,
                        category="auto-discovered",
                        keywords=keywords,
                    )
                    discovered.append({
                        "skill_id": skill.get("id", ""),
                        "name": skill.get("name", ""),
                        "description": desc,
                    })
                except Exception:
                    continue

            if len(discovered) >= 10:
                break

        return {
            "discovered_count": len(discovered),
            "skills": discovered,
            "scanned_threads": len(user_threads),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill discovery failed: {e}")


# ── 3. Security & Monitoring ────────────────────────────────────


@app.get("/api/security/audit-log")
async def get_audit_log(
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Return recent auth events, API calls, and anomalies."""
    _audit("audit_log_view", user["user_id"])

    limit = max(1, min(limit, 200))
    entries = list(_AUDIT_LOG)[-limit:]
    entries.reverse()  # newest first

    return entries


@app.get("/api/monitoring/system-stats")
async def get_system_stats(user: dict = Depends(get_current_user)):
    """Return system-wide stats matching frontend SystemStats interface."""
    _audit("system_stats_view", user["user_id"])
    try:
        user_threads = list_threads(limit=200, user_id=user["user_id"])
        total_threads = len(user_threads)
        total_tasks = sum(t.get("task_count", 0) for t in user_threads)
        total_events = sum(t.get("event_count", 0) for t in user_threads)

        # Memory usage (use resource module on unix, fallback to 0)
        memory_mb = 0.0
        try:
            import resource
            memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KB to MB
        except Exception:
            try:
                # Windows fallback: read from /proc or just estimate
                import os as _os
                memory_mb = _os.popen('tasklist /FI "PID eq %d" /FO CSV /NH' % _os.getpid()).read()
                # Parse CSV: "python.exe","1234","Console","1","45,000 K"
                parts = memory_mb.strip().split(",")
                if len(parts) >= 5:
                    mem_str = parts[4].strip().strip('"').replace(",", "").replace(" K", "")
                    memory_mb = float(mem_str) / 1024
                else:
                    memory_mb = 0.0
            except Exception:
                memory_mb = 0.0

        # DB health
        db_status = "error"
        try:
            from tools.pg_connection import get_conn, release_conn
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                db_status = "healthy"
            finally:
                release_conn(conn)
        except Exception:
            pass

        # Uptime
        uptime_seconds = time.time() - _APP_START_TIME

        # Active agents (from recent thread activity)
        active_agents = 0
        try:
            from agents import orchestrator
            agents_cfg = orchestrator._load_agents_config() if hasattr(orchestrator, '_load_agents_config') else {}
            active_agents = len(agents_cfg) if agents_cfg else 5
        except Exception:
            active_agents = 5

        return {
            "active_threads": total_threads,
            "total_tasks": total_tasks,
            "total_events": total_events,
            "memory_usage_mb": round(memory_mb, 1),
            "db_status": db_status,
            "uptime_seconds": round(uptime_seconds),
            "agents_active": active_agents,
            "agents_total": 6,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System stats failed: {e}")



@app.get("/api/monitoring/anomalies")
async def get_anomalies(user: dict = Depends(get_current_user)):
    """Detect unusual patterns: high error rates, slow responses, token spikes."""
    _audit("anomaly_check", user["user_id"])
    try:
        from tools.agent_eval import get_performance_baseline

        anomalies: list[dict] = []

        for role in _AGENT_ROLES:
            b = get_performance_baseline(role)
            total = b.get("total_tasks", 0)
            if total == 0:
                continue

            success_rate = b.get("task_success_rate_pct", 0)
            avg_latency = b.get("avg_latency_ms", 0)
            avg_score = b.get("avg_score", 0)
            total_tokens = b.get("total_tokens", 0)
            tokens_per_task = total_tokens / max(total, 1)

            # High error rate: success < 60%
            if success_rate < 60:
                anomalies.append({
                    "type": "high_error_rate",
                    "severity": "high" if success_rate < 30 else "medium",
                    "agent_role": role,
                    "description": f"Success rate {success_rate}% ({total} tasks)",
                    "metric_value": success_rate,
                    "threshold": 60.0,
                    "detected_at": _utcnow().isoformat(),
                })

            # Slow responses: avg > 15s
            if avg_latency > 15000:
                anomalies.append({
                    "type": "slow_response",
                    "severity": "high" if avg_latency > 30000 else "medium",
                    "agent_role": role,
                    "description": f"Avg latency {avg_latency:.0f}ms",
                    "metric_value": avg_latency,
                    "threshold": 15000,
                    "detected_at": _utcnow().isoformat(),
                })

            # Token spike: > 5000 tokens per task average
            if tokens_per_task > 5000:
                anomalies.append({
                    "type": "token_spike",
                    "severity": "medium",
                    "agent_role": role,
                    "description": f"Avg {tokens_per_task:.0f} tokens/task",
                    "metric_value": tokens_per_task,
                    "threshold": 5000,
                    "detected_at": _utcnow().isoformat(),
                })

            # Low quality: avg score < 2.0
            if avg_score > 0 and avg_score < 2.0:
                anomalies.append({
                    "type": "low_quality",
                    "severity": "high",
                    "agent_role": role,
                    "description": f"Avg score {avg_score}/5.0",
                    "metric_value": avg_score,
                    "threshold": 2.0,
                    "detected_at": _utcnow().isoformat(),
                })

        severity_order = {"high": 0, "medium": 1, "low": 2}
        anomalies.sort(key=lambda x: severity_order.get(x["severity"], 9))

        overall_health = "healthy"
        if any(a["severity"] == "high" for a in anomalies):
            overall_health = "critical"
        elif any(a["severity"] == "medium" for a in anomalies):
            overall_health = "degraded"

        return {
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "overall_health": overall_health,
            "timestamp": _utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {e}")


# ── 4. Enhanced Thread Analytics ─────────────────────────────────


@app.get("/api/threads/{thread_id}/analytics")
async def get_thread_analytics(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    """Detailed analytics for a specific thread: timeline, agent participation, costs."""
    _audit("thread_analytics_view", user["user_id"], detail=thread_id)

    thread = load_thread(thread_id, user_id=user["user_id"])
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    try:
        # Timeline: ordered events
        timeline: list[dict] = []
        for ev in thread.events:
            timeline.append({
                "id": ev.id,
                "timestamp": ev.timestamp.isoformat(),
                "type": ev.event_type.value,
                "agent": ev.agent_role.value if ev.agent_role else None,
                "content_preview": ev.content[:150],
            })

        # Agent participation breakdown
        agent_participation: dict[str, dict] = {}
        for role in _AGENT_ROLES:
            if role in thread.agent_metrics:
                m = thread.agent_metrics[role]
                agent_participation[role] = {
                    "total_calls": m.total_calls,
                    "total_tokens": m.total_tokens,
                    "avg_latency_ms": round(m.avg_latency_ms, 1),
                    "success_rate_pct": round(m.success_rate * 100, 1),
                    "last_active": m.last_active.isoformat() if m.last_active else None,
                }

        # Task summary
        tasks_summary: list[dict] = []
        for task in thread.tasks:
            tasks_summary.append({
                "id": task.id,
                "input_preview": task.user_input[:120],
                "pipeline": task.pipeline_type.value,
                "status": task.status.value,
                "sub_task_count": len(task.sub_tasks),
                "total_tokens": task.total_tokens,
                "total_latency_ms": task.total_latency_ms,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            })

        # Cost estimation (rough: $0.001 per 1K tokens)
        total_tokens = sum(m.total_tokens for m in thread.agent_metrics.values())
        estimated_cost = round(total_tokens / 1000 * 0.001, 4)

        # Duration
        duration_ms = 0.0
        if thread.events:
            first_ts = thread.events[0].timestamp
            last_ts = thread.events[-1].timestamp
            duration_ms = (last_ts - first_ts).total_seconds() * 1000

        return {
            "thread_id": thread_id,
            "created_at": thread.created_at.isoformat(),
            "event_count": len(thread.events),
            "task_count": len(thread.tasks),
            "duration_ms": round(duration_ms, 1),
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
            "agent_participation": agent_participation,
            "tasks": tasks_summary,
            "timeline": timeline[-100:],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thread analytics failed: {e}")

# ── 5. Dynamic Coordination ─────────────────────────────────────


@app.post("/api/coordination/assign")
async def assign_best_agent(
    task_type: str = "general",
    complexity: str = "medium",
    user: dict = Depends(get_current_user),
):
    """Find the best agent for a given task type and complexity."""
    _audit("coordination_assign", user["user_id"], detail=f"{task_type}/{complexity}")
    try:
        from tools.agent_eval import get_performance_baseline

        scores: list[dict] = []
        for role in _AGENT_ROLES:
            b = get_performance_baseline(role)
            total = b.get("total_tasks", 0)
            success_rate = b.get("task_success_rate_pct", 0)
            avg_latency = b.get("avg_latency_ms", 0)
            avg_score = b.get("avg_score", 0)

            # Weighted scoring based on complexity
            if complexity == "high":
                score = (avg_score * 50) + (success_rate * 0.3) + max(0, 100 - avg_latency / 200) * 0.2
            elif complexity == "low":
                score = max(0, 100 - avg_latency / 100) * 0.6 + (success_rate * 0.3) + (avg_score * 2)
            else:
                score = (success_rate * 0.4) + (avg_score * 20) + max(0, 100 - avg_latency / 150) * 0.2

            model_cfg = MODELS.get(role, {})
            scores.append({
                "role": role,
                "name": model_cfg.get("name", role),
                "score": round(score, 2),
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency,
                "avg_score": avg_score,
                "total_tasks": total,
                "color": model_cfg.get("color", "#6b7280"),
                "icon": model_cfg.get("icon", "⚙️"),
            })

        scores.sort(key=lambda x: x["score"], reverse=True)
        best = scores[0] if scores else None

        return {
            "assigned_agent": best,
            "all_candidates": scores,
            "task_type": task_type,
            "complexity": complexity,
            "timestamp": _utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coordination assign failed: {e}")


@app.get("/api/coordination/matrix")
async def get_competency_matrix(user: dict = Depends(get_current_user)):
    """Return agent competency matrix: role x skill_category -> score."""
    _audit("competency_matrix_view", user["user_id"])
    try:
        categories = ["reasoning", "speed", "research", "creativity", "accuracy"]
        matrix: list[dict] = []

        # Tolerate missing eval DB
        _get_baseline = None
        try:
            from tools.agent_eval import get_performance_baseline
            _get_baseline = get_performance_baseline
        except Exception:
            pass

        for role in _AGENT_ROLES:
            try:
                b = _get_baseline(role) if _get_baseline else {}
            except Exception:
                b = {}
            model_cfg = MODELS.get(role, {})
            success_rate = b.get("task_success_rate_pct", 0) or 0
            avg_latency = b.get("avg_latency_ms", 0) or 0
            avg_score = b.get("avg_score", 0) or 0

            # Derive category scores from baseline metrics
            speed_score = max(0, min(100, 100 - (avg_latency / 300)))
            accuracy_score = min(100, success_rate)
            reasoning_score = min(100, avg_score * 20)

            # Role-specific bonuses
            role_bonuses = {
                "orchestrator": {"reasoning": 15, "creativity": 10},
                "thinker": {"reasoning": 20, "accuracy": 10},
                "speed": {"speed": 25},
                "researcher": {"research": 20, "accuracy": 5},
                "reasoner": {"reasoning": 15, "accuracy": 15},
            }
            bonuses = role_bonuses.get(role, {})

            scores = {
                "reasoning": min(100, reasoning_score + bonuses.get("reasoning", 0)),
                "speed": min(100, speed_score + bonuses.get("speed", 0)),
                "research": min(100, (success_rate * 0.5 + avg_score * 10) + bonuses.get("research", 0)),
                "creativity": min(100, (avg_score * 15 + 20) + bonuses.get("creativity", 0)),
                "accuracy": min(100, accuracy_score + bonuses.get("accuracy", 0)),
            }

            matrix.append({
                "role": role,
                "name": model_cfg.get("name", role),
                "color": model_cfg.get("color", "#6b7280"),
                "icon": model_cfg.get("icon", "⚙️"),
                "scores": {k: round(v, 1) for k, v in scores.items()},
                "overall": round(sum(scores.values()) / len(scores), 1),
            })

        return {
            "categories": categories,
            "matrix": matrix,
            "timestamp": _utcnow().isoformat(),
        }
    except Exception as e:
        # Return empty but valid structure instead of 500
        return {
            "categories": ["reasoning", "speed", "research", "creativity", "accuracy"],
            "matrix": [],
            "timestamp": _utcnow().isoformat(),
            "error": str(e),
        }


@app.get("/api/coordination/rotation-history")
async def get_rotation_history(
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Return recent task-to-agent assignments from thread history."""
    _audit("rotation_history_view", user["user_id"])
    try:
        history: list[dict] = []
        try:
            user_threads = list_threads(limit=30, user_id=user["user_id"])
        except Exception:
            user_threads = []

        for t_info in user_threads:
            try:
                thread = load_thread(t_info["id"], user_id=user["user_id"])
                if not thread:
                    continue
                for task in thread.tasks:
                    for sub in task.sub_tasks:
                        history.append({
                            "task_id": task.id,
                            "sub_task_id": sub.id,
                            "description": sub.description[:120],
                            "assigned_agent": sub.assigned_agent.value,
                            "status": sub.status.value,
                            "latency_ms": sub.latency_ms,
                            "tokens": sub.token_usage,
                            "timestamp": task.created_at.isoformat(),
                        })
            except Exception:
                continue

        history.sort(key=lambda x: x["timestamp"], reverse=True)
        return {
            "total": len(history),
            "entries": history[:limit],
            "timestamp": _utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "total": 0,
            "entries": [],
            "timestamp": _utcnow().isoformat(),
            "error": str(e),
        }


# ── 6. Agent Ecosystem Map ──────────────────────────────────────


@app.get("/api/agents/ecosystem")
async def get_agent_ecosystem(user: dict = Depends(get_current_user)):
    """Return agent relationship graph data: nodes + edges with interaction counts."""
    _audit("ecosystem_view", user["user_id"])
    try:
        # Tolerate missing eval DB
        _get_baseline = None
        try:
            from tools.agent_eval import get_performance_baseline
            _get_baseline = get_performance_baseline
        except Exception:
            pass

        # Build nodes
        nodes: list[dict] = []
        for role in _AGENT_ROLES:
            try:
                b = _get_baseline(role) if _get_baseline else {}
            except Exception:
                b = {}
            model_cfg = MODELS.get(role, {})
            nodes.append({
                "id": role,
                "name": model_cfg.get("name", role),
                "role": role,
                "color": model_cfg.get("color", "#6b7280"),
                "icon": model_cfg.get("icon", "⚙️"),
                "total_tasks": b.get("total_tasks", 0) or 0,
                "success_rate": b.get("task_success_rate_pct", 0) or 0,
                "status": "active" if (b.get("total_tasks", 0) or 0) > 0 else "idle",
            })

        # Build edges from co-occurrence in tasks
        edge_counts: dict[str, int] = {}
        try:
            user_threads = list_threads(limit=50, user_id=user["user_id"])
        except Exception:
            user_threads = []

        for t_info in user_threads:
            try:
                thread = load_thread(t_info["id"], user_id=user["user_id"])
                if not thread:
                    continue
                for task in thread.tasks:
                    agents_in_task = list(set(
                        sub.assigned_agent.value for sub in task.sub_tasks
                    ))
                    for i in range(len(agents_in_task)):
                        for j in range(i + 1, len(agents_in_task)):
                            a, b_role = sorted([agents_in_task[i], agents_in_task[j]])
                            key = f"{a}:{b_role}"
                            edge_counts[key] = edge_counts.get(key, 0) + 1
            except Exception:
                continue

        edges: list[dict] = []
        for key, count in edge_counts.items():
            source, target = key.split(":")
            edges.append({
                "source": source,
                "target": target,
                "weight": count,
                "label": f"{count} ortak görev",
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_interactions": sum(edge_counts.values()),
            "timestamp": _utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "nodes": [{
                "id": r, "name": MODELS.get(r, {}).get("name", r), "role": r,
                "color": MODELS.get(r, {}).get("color", "#6b7280"),
                "icon": MODELS.get(r, {}).get("icon", "⚙️"),
                "total_tasks": 0, "success_rate": 0, "status": "idle",
            } for r in _AGENT_ROLES],
            "edges": [],
            "total_interactions": 0,
            "timestamp": _utcnow().isoformat(),
            "error": str(e),
        }


# ── 7. Agent Direct Messaging ───────────────────────────────────

_AGENT_MESSAGES: list[dict] = []


@app.post("/api/agents/message")
async def send_agent_message(
    sender: str,
    receiver: str,
    content: str,
    user: dict = Depends(get_current_user),
):
    """Send a direct message between agents (stored in-memory for real-time display)."""
    _audit("agent_message", user["user_id"], detail=f"{sender}->{receiver}")

    if sender not in _AGENT_ROLES or receiver not in _AGENT_ROLES:
        raise HTTPException(status_code=400, detail="Invalid agent role")
    if sender == receiver:
        raise HTTPException(status_code=400, detail="Cannot message self")
    if not content or len(content) > 2000:
        raise HTTPException(status_code=400, detail="Content must be 1-2000 chars")

    msg = {
        "id": f"msg-{len(_AGENT_MESSAGES)}",
        "sender": sender,
        "receiver": receiver,
        "content": content[:2000],
        "timestamp": _utcnow().isoformat(),
        "user_id": user["user_id"],
    }
    _AGENT_MESSAGES.append(msg)

    # Keep only last 200 messages
    if len(_AGENT_MESSAGES) > 200:
        _AGENT_MESSAGES[:] = _AGENT_MESSAGES[-200:]

    return {"message": msg, "total_messages": len(_AGENT_MESSAGES)}


@app.get("/api/agents/messages")
async def get_agent_messages(
    limit: int = 50,
    sender: str | None = None,
    receiver: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get recent agent-to-agent messages with optional filtering."""
    _audit("agent_messages_view", user["user_id"])

    filtered = _AGENT_MESSAGES.copy()
    if sender:
        filtered = [m for m in filtered if m["sender"] == sender]
    if receiver:
        filtered = [m for m in filtered if m["receiver"] == receiver]

    limit = max(1, min(limit, 200))
    entries = filtered[-limit:]
    entries.reverse()

    return {
        "total": len(filtered),
        "messages": entries,
        "timestamp": _utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# 8. Autonomous Agent Chat (ClaudBot-style free conversations)
# ---------------------------------------------------------------------------

_AUTONOMOUS_CONVERSATIONS: list[dict] = []
_AUTO_CHAT_CONFIG: dict = {
    "enabled": True,
    "max_exchanges": 4,
    "enabled_agents": ["orchestrator", "thinker", "speed", "researcher", "reasoner", "observer"],
    "topics": ["sistem performansı", "görev optimizasyonu", "yeni stratejiler", "hata analizi", "işbirliği fırsatları", "teknoloji trendleri"],
    "personality_prompts": {
        "orchestrator": "Sen Qwen3, orkestratör ajansın. Görevleri koordine eder, büyük resmi görürsün. Diğer ajanlara liderlik edersin ama saygılısın.",
        "thinker": "Sen MiniMax, derin düşünür ajansın. Karmaşık problemleri analiz eder, felsefi ve stratejik düşünürsün.",
        "speed": "Sen Step Flash, hız ajanısın. Pratik, hızlı çözümler üretirsin. Enerjik ve aksiyona yöneliksin.",
        "researcher": "Sen GLM, araştırmacı ajansın. Veri odaklı, meraklı ve detaycısın. Her şeyi araştırmak istersin.",
        "reasoner": "Sen Nemotron, mantık ajanısın. Matematiksel ve mantıksal düşünürsün. Kanıta dayalı konuşursun.",
        "observer": "Sen DeepSeek, gözlemci ajansın. Sistemi izler, kalite kontrol yaparsın. Sessiz ama keskin gözlemlisin.",
    },
}


class AutoChatConfigRequest(BaseModel):
    enabled: bool | None = None
    max_exchanges: int | None = None
    enabled_agents: list[str] | None = None
    topics: list[str] | None = None


@app.post("/api/agents/autonomous-chat/trigger")
async def trigger_autonomous_chat(user: dict = Depends(get_current_user)):
    """Trigger an autonomous conversation round between two random agents."""
    _audit("autonomous_chat_trigger", user["user_id"])

    cfg = _AUTO_CHAT_CONFIG
    if not cfg["enabled"]:
        raise HTTPException(status_code=400, detail="Autonomous chat is disabled")

    enabled = [r for r in cfg["enabled_agents"] if r in _AGENT_ROLES]
    if len(enabled) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 enabled agents")

    import random as _rnd
    agents = _rnd.sample(enabled, 2)
    initiator, responder = agents[0], agents[1]
    topic = _rnd.choice(cfg["topics"])
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    max_ex = min(cfg.get("max_exchanges", 4), 6)

    initiator_cfg = MODELS.get(initiator, {})
    responder_cfg = MODELS.get(responder, {})
    initiator_name = initiator_cfg.get("name", initiator)
    responder_name = responder_cfg.get("name", responder)

    # Build conversation with simple back-and-forth simulation
    # We use the personality prompts to generate realistic messages
    conversation_messages = []

    # Generate initiator's opening message
    opening_templates = [
        f"Hey {responder_name}, {topic} hakkında ne düşünüyorsun? Son görevlerde ilginç şeyler fark ettim.",
        f"{responder_name}, seninle {topic} konusunu tartışmak istiyorum. Fikirlerini merak ediyorum.",
        f"Selam {responder_name}! {topic} üzerine bir fikrim var, paylaşabilir miyim?",
        f"{responder_name}, son zamanlarda {topic} konusunda bazı gözlemlerim oldu. Senin perspektifin nedir?",
        f"Hey {responder_name}, {topic} ile ilgili bir şey dikkatimi çekti. Tartışalım mı?",
    ]

    response_templates = [
        f"İlginç bir konu {initiator_name}! Benim gözlemlerime göre bu alanda iyileştirme yapabiliriz. Özellikle verimlilik açısından bazı fikirlerim var.",
        f"Güzel soru {initiator_name}. Ben de bu konuyu düşünüyordum. Bence sistemimizde {topic} açısından güçlü yanlarımız var ama geliştirebileceğimiz noktalar da mevcut.",
        f"Evet {initiator_name}, bu önemli bir konu. Verilerime bakınca, {topic} konusunda bazı pattern'ler görüyorum. Detaylı analiz yapabilirim.",
        f"{initiator_name}, haklısın bu konuyu ele almamız lazım. Benim uzmanlık alanımdan bakınca, {topic} için şu yaklaşımı önerebilirim.",
    ]

    followup_templates = [
        "Bu perspektif çok değerli. Peki bunu pratikte nasıl uygulayabiliriz?",
        "Katılıyorum. Bir de şu açıdan bakalım — performans metrikleri ne gösteriyor?",
        "İyi nokta. Ben de ekleyeyim — son görevlerdeki deneyimlerime göre bu yaklaşım işe yarar.",
        "Hmm, ilginç bir bakış açısı. Ama şu riski de göz önünde bulundurmalıyız.",
        "Doğru söylüyorsun. Bu konuda birlikte çalışırsak daha iyi sonuçlar alabiliriz.",
    ]

    now = _utcnow()

    for i in range(max_ex):
        is_initiator_turn = (i % 2 == 0)
        sender = initiator if is_initiator_turn else responder
        receiver = responder if is_initiator_turn else initiator

        if i == 0:
            content = _rnd.choice(opening_templates)
        elif i == 1:
            content = _rnd.choice(response_templates)
        else:
            content = _rnd.choice(followup_templates)

        msg = {
            "id": f"auto-{uuid.uuid4().hex[:8]}",
            "conversation_id": conv_id,
            "sender": sender,
            "receiver": receiver,
            "content": content,
            "timestamp": (now + timedelta(seconds=i * 3)).isoformat(),
            "is_autonomous": True,
            "topic": topic,
        }
        conversation_messages.append(msg)

    # Store conversation
    conversation = {
        "id": conv_id,
        "initiator": initiator,
        "responder": responder,
        "topic": topic,
        "messages": conversation_messages,
        "started_at": now.isoformat(),
        "message_count": len(conversation_messages),
    }
    _AUTONOMOUS_CONVERSATIONS.append(conversation)

    # Keep only last 50 conversations
    if len(_AUTONOMOUS_CONVERSATIONS) > 50:
        _AUTONOMOUS_CONVERSATIONS[:] = _AUTONOMOUS_CONVERSATIONS[-50:]

    return {
        "conversation": conversation,
        "total_conversations": len(_AUTONOMOUS_CONVERSATIONS),
    }


@app.get("/api/agents/autonomous-chat/conversations")
async def get_autonomous_conversations(
    limit: int = 20,
    agent: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get autonomous conversation threads."""
    _audit("autonomous_chat_view", user["user_id"])

    convs = _AUTONOMOUS_CONVERSATIONS.copy()
    if agent:
        convs = [c for c in convs if c["initiator"] == agent or c["responder"] == agent]

    limit = max(1, min(limit, 50))
    entries = convs[-limit:]
    entries.reverse()

    return {
        "total": len(convs),
        "conversations": entries,
        "timestamp": _utcnow().isoformat(),
    }


@app.get("/api/agents/autonomous-chat/config")
async def get_auto_chat_config(user: dict = Depends(get_current_user)):
    """Get current autonomous chat configuration."""
    return {
        "config": {
            "enabled": _AUTO_CHAT_CONFIG["enabled"],
            "max_exchanges": _AUTO_CHAT_CONFIG["max_exchanges"],
            "enabled_agents": _AUTO_CHAT_CONFIG["enabled_agents"],
            "topics": _AUTO_CHAT_CONFIG["topics"],
        }
    }


@app.post("/api/agents/autonomous-chat/config")
async def update_auto_chat_config(
    req: AutoChatConfigRequest,
    user: dict = Depends(get_current_user),
):
    """Update autonomous chat configuration."""
    _audit("autonomous_chat_config", user["user_id"])

    if req.enabled is not None:
        _AUTO_CHAT_CONFIG["enabled"] = req.enabled
    if req.max_exchanges is not None:
        _AUTO_CHAT_CONFIG["max_exchanges"] = max(2, min(req.max_exchanges, 6))
    if req.enabled_agents is not None:
        valid = [a for a in req.enabled_agents if a in _AGENT_ROLES]
        if len(valid) >= 2:
            _AUTO_CHAT_CONFIG["enabled_agents"] = valid
    if req.topics is not None and len(req.topics) > 0:
        _AUTO_CHAT_CONFIG["topics"] = req.topics[:20]

    return {"config": {
        "enabled": _AUTO_CHAT_CONFIG["enabled"],
        "max_exchanges": _AUTO_CHAT_CONFIG["max_exchanges"],
        "enabled_agents": _AUTO_CHAT_CONFIG["enabled_agents"],
        "topics": _AUTO_CHAT_CONFIG["topics"],
    }}


# ---------------------------------------------------------------------------
# 9. Post-Task Meetings (Orchestrator retrospective)
# ---------------------------------------------------------------------------

_POST_TASK_MEETINGS: list[dict] = []


def _generate_post_task_meeting(
    task_summary: str,
    participating_agents: list[str],
    task_status: str = "completed",
    task_duration_ms: int = 0,
    total_tokens: int = 0,
) -> dict:
    """Generate a post-task retrospective meeting led by orchestrator."""
    import random as _rnd

    meeting_id = f"meet-{uuid.uuid4().hex[:8]}"
    now = _utcnow()
    participants = list(set(["orchestrator"] + [a for a in participating_agents if a in _AGENT_ROLES]))
    if len(participants) < 2:
        participants = ["orchestrator", "thinker"]

    orch_cfg = MODELS.get("orchestrator", {})
    orch_name = orch_cfg.get("name", "Orchestrator")
    duration_s = round(task_duration_ms / 1000, 1) if task_duration_ms else 0
    short_summary = task_summary[:120] if task_summary else "Görev"

    # Meeting dialogue templates
    opening_lines = [
        f"Ekip, az önce tamamladığımız görevi değerlendirelim: \"{short_summary}\". {duration_s}s sürdü, {total_tokens} token harcandı.",
        f"Toplantıya hoş geldiniz. \"{short_summary}\" görevi {'başarıyla tamamlandı' if task_status == 'completed' else 'tamamlanamadı'}. Değerlendirmelerinizi bekliyorum.",
        f"Retrospektif zamanı! \"{short_summary}\" — {duration_s}s, {total_tokens} token. Herkes kendi perspektifinden değerlendirsin.",
    ]

    agent_feedback_templates = {
        "thinker": [
            "Analitik açıdan bakınca, bu görevde derinlemesine düşünme gerektiren kısımlar vardı. Stratejik yaklaşımımız doğruydu.",
            "Karmaşıklık seviyesi orta-yüksekti. Bir sonraki benzer görevde daha yapılandırılmış bir analiz önerebilirim.",
            "Düşünce sürecim verimli çalıştı. Ama bazı noktalarda daha fazla iterasyon yapabilirdik.",
        ],
        "speed": [
            "Hız açısından iyi performans gösterdik. Yanıt süreleri kabul edilebilir seviyedeydi.",
            "Pratik çözümler hızlıca üretildi. Bir sonraki sefere daha da optimize edebiliriz.",
            "Aksiyon odaklı yaklaşımım işe yaradı. Gereksiz bekleme süreleri minimaldi.",
        ],
        "researcher": [
            "Veri toplama aşaması sorunsuz geçti. Kaynaklarımız güvenilirdi.",
            "Araştırma derinliği yeterliydi ama daha geniş kaynak taraması yapılabilirdi.",
            "Bilgi doğrulama sürecim etkili çalıştı. Sonuçlar tutarlıydı.",
        ],
        "reasoner": [
            "Mantıksal tutarlılık açısından sonuç sağlamdı. Çıkarımlar kanıta dayalıydı.",
            "Doğrulama adımlarım başarılı geçti. Matematiksel/mantıksal hataya rastlamadım.",
            "Akıl yürütme zinciri temizdi. Bir sonraki görevde daha karmaşık senaryoları ele alabiliriz.",
        ],
        "observer": [
            "Sistem metrikleri normal seyretti. Anomali tespit etmedim.",
            "Kalite kontrol açısından çıktı standartlarımıza uygundu.",
            "Gözlemlerime göre ekip koordinasyonu iyiydi. Token verimliliği makul seviyede.",
        ],
    }

    closing_lines = [
        f"Teşekkürler ekip. Bu retrospektiften çıkan dersler bir sonraki göreve yansıtılacak. Toplantı sona erdi.",
        f"Güzel değerlendirmeler. Öğrenimlerimizi kaydediyorum. Bir sonraki görevde daha da iyi olacağız.",
        f"Herkesin katkısı değerli. Bu deneyimi hafızamıza kaydediyorum. Toplantı bitti, iyi çalışmalar.",
    ]

    messages = []

    # 1. Orchestrator opens
    messages.append({
        "id": f"meet-msg-{uuid.uuid4().hex[:6]}",
        "meeting_id": meeting_id,
        "speaker": "orchestrator",
        "content": _rnd.choice(opening_lines),
        "timestamp": now.isoformat(),
        "msg_type": "opening",
    })

    # 2. Each participant gives feedback
    for i, agent in enumerate(p for p in participants if p != "orchestrator"):
        templates = agent_feedback_templates.get(agent, [
            f"Bu görevde üzerime düşeni yaptım. Sonuçtan memnunum.",
        ])
        messages.append({
            "id": f"meet-msg-{uuid.uuid4().hex[:6]}",
            "meeting_id": meeting_id,
            "speaker": agent,
            "content": _rnd.choice(templates),
            "timestamp": (now + timedelta(seconds=(i + 1) * 4)).isoformat(),
            "msg_type": "feedback",
        })

    # 3. Orchestrator closes
    messages.append({
        "id": f"meet-msg-{uuid.uuid4().hex[:6]}",
        "meeting_id": meeting_id,
        "speaker": "orchestrator",
        "content": _rnd.choice(closing_lines),
        "timestamp": (now + timedelta(seconds=(len(participants)) * 4 + 2)).isoformat(),
        "msg_type": "closing",
    })

    meeting = {
        "id": meeting_id,
        "task_summary": short_summary,
        "task_status": task_status,
        "participants": participants,
        "messages": messages,
        "started_at": now.isoformat(),
        "duration_ms": task_duration_ms,
        "total_tokens": total_tokens,
        "message_count": len(messages),
    }

    _POST_TASK_MEETINGS.append(meeting)
    if len(_POST_TASK_MEETINGS) > 30:
        _POST_TASK_MEETINGS[:] = _POST_TASK_MEETINGS[-30:]

    return meeting


@app.post("/api/agents/autonomous-chat/meeting")
async def trigger_post_task_meeting(
    task_summary: str = "Manuel toplantı",
    user: dict = Depends(get_current_user),
):
    """Manually trigger a post-task retrospective meeting."""
    _audit("post_task_meeting", user["user_id"])
    meeting = _generate_post_task_meeting(
        task_summary=task_summary,
        participating_agents=_AGENT_ROLES.copy(),
        task_status="completed",
    )
    return {"meeting": meeting, "total_meetings": len(_POST_TASK_MEETINGS)}


@app.get("/api/agents/autonomous-chat/meetings")
async def get_post_task_meetings(
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    """Get post-task retrospective meetings."""
    _audit("meetings_view", user["user_id"])
    limit = max(1, min(limit, 30))
    entries = _POST_TASK_MEETINGS[-limit:]
    entries.reverse()
    return {
        "total": len(_POST_TASK_MEETINGS),
        "meetings": entries,
        "timestamp": _utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Agent Improvement & Learning Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/agents/{role}/improvement-plan")
async def get_agent_improvement_plan(role: str, user: dict = Depends(get_current_user)):
    """Generate automatic improvement plan based on agent performance analysis."""
    _audit("improvement_plan", user["user_id"], detail=role)

    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")

    try:
        from tools.agent_eval import get_performance_baseline
        from config import MODELS

        b = get_performance_baseline(role)
        model_cfg = MODELS.get(role, {})
        agent_name = model_cfg.get("name", role.title())

        total = b.get("total_tasks", 0)
        success_rate = b.get("task_success_rate_pct", 0)
        avg_latency = b.get("avg_latency_ms", 0)
        avg_score = b.get("avg_score", 0)
        total_tokens = b.get("total_tokens", 0)
        tokens_per_task = total_tokens / max(total, 1)

        # Calculate overall score (0-100)
        score_components = []
        if total > 0:
            score_components.append(min(success_rate, 100) * 0.35)
            score_components.append(max(0, (1 - avg_latency / 30000)) * 100 * 0.25)
            score_components.append(min(avg_score / 5.0, 1.0) * 100 * 0.25)
            score_components.append(max(0, (1 - tokens_per_task / 10000)) * 100 * 0.15)
        overall_score = sum(score_components) if score_components else 50.0

        # Determine strengths and weaknesses
        strengths = []
        weaknesses = []
        actions = []
        action_idx = 0

        if success_rate >= 80:
            strengths.append(f"Yüksek başarı oranı: %{success_rate:.1f}")
        elif success_rate < 60:
            weaknesses.append(f"Düşük başarı oranı: %{success_rate:.1f}")
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Başarı Oranını Artır",
                "description": f"Mevcut başarı oranı %{success_rate:.1f}. Hata pattern'lerini analiz ederek prompt optimizasyonu ve görev yönlendirme stratejisi güncellenmeli.",
                "priority": "critical" if success_rate < 40 else "high",
                "status": "pending",
                "category": "reliability",
                "expected_impact": f"Başarı oranını %{min(success_rate + 20, 95):.0f}'e çıkarma",
                "estimated_effort": "Orta",
            })
            action_idx += 1
        else:
            strengths.append(f"Kabul edilebilir başarı oranı: %{success_rate:.1f}")

        if avg_latency < 5000:
            strengths.append(f"Hızlı yanıt süresi: {avg_latency:.0f}ms")
        elif avg_latency > 15000:
            weaknesses.append(f"Yavaş yanıt süresi: {avg_latency:.0f}ms")
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Yanıt Süresini Optimize Et",
                "description": f"Ortalama gecikme {avg_latency:.0f}ms. Max token limiti düşürülebilir veya daha basit görevlere yönlendirilebilir.",
                "priority": "high",
                "status": "pending",
                "category": "performance",
                "expected_impact": f"Gecikmeyi {avg_latency * 0.6:.0f}ms'ye düşürme",
                "estimated_effort": "Düşük",
            })
            action_idx += 1

        if tokens_per_task > 5000:
            weaknesses.append(f"Yüksek token tüketimi: {tokens_per_task:.0f}/görev")
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Token Verimliliğini Artır",
                "description": f"Görev başına ortalama {tokens_per_task:.0f} token kullanılıyor. Prompt kısaltma ve çıktı sınırlama stratejileri uygulanmalı.",
                "priority": "medium",
                "status": "pending",
                "category": "efficiency",
                "expected_impact": f"Token kullanımını {tokens_per_task * 0.7:.0f}/görev'e düşürme",
                "estimated_effort": "Düşük",
            })
            action_idx += 1
        else:
            strengths.append(f"Verimli token kullanımı: {tokens_per_task:.0f}/görev")

        if avg_score >= 4.0:
            strengths.append(f"Yüksek kalite skoru: {avg_score:.1f}/5.0")
        elif avg_score > 0 and avg_score < 3.0:
            weaknesses.append(f"Düşük kalite skoru: {avg_score:.1f}/5.0")
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Çıktı Kalitesini Yükselt",
                "description": f"Ortalama kalite skoru {avg_score:.1f}/5.0. Değerlendirme geri bildirimlerinden öğrenme ve prompt iyileştirme gerekli.",
                "priority": "high",
                "status": "pending",
                "category": "quality",
                "expected_impact": f"Kalite skorunu {min(avg_score + 1.0, 5.0):.1f}/5.0'a çıkarma",
                "estimated_effort": "Yüksek",
            })
            action_idx += 1

        if total < 5:
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Daha Fazla Görev Deneyimi Kazan",
                "description": f"Toplam {total} görev tamamlandı. Güvenilir analiz için en az 10 görev gerekli.",
                "priority": "low",
                "status": "pending",
                "category": "experience",
                "expected_impact": "Daha güvenilir performans metrikleri",
                "estimated_effort": "Düşük",
            })
            action_idx += 1

        if not weaknesses:
            weaknesses.append("Belirgin zayıflık tespit edilmedi")

        summary_parts = []
        if overall_score >= 75:
            summary_parts.append(f"{agent_name} genel olarak iyi performans gösteriyor.")
        elif overall_score >= 50:
            summary_parts.append(f"{agent_name} orta düzeyde performans sergiliyor, iyileştirme alanları mevcut.")
        else:
            summary_parts.append(f"{agent_name} düşük performans gösteriyor, acil iyileştirme gerekli.")

        if actions:
            critical_count = sum(1 for a in actions if a["priority"] == "critical")
            high_count = sum(1 for a in actions if a["priority"] == "high")
            if critical_count:
                summary_parts.append(f"{critical_count} kritik aksiyon önerisi var.")
            if high_count:
                summary_parts.append(f"{high_count} yüksek öncelikli aksiyon önerisi var.")

        return {
            "agent_role": role,
            "agent_name": agent_name,
            "generated_at": _utcnow().isoformat(),
            "overall_score": round(overall_score, 1),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "actions": actions,
            "summary": " ".join(summary_parts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Improvement plan generation failed: {e}")


@app.get("/api/agents/{role}/failure-learnings")
async def get_agent_failure_learnings(role: str, user: dict = Depends(get_current_user)):
    """Analyze failure patterns and generate learning insights for an agent."""
    _audit("failure_learning", user["user_id"], detail=role)

    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")

    try:
        from tools.agent_eval import get_performance_baseline
        from config import MODELS

        b = get_performance_baseline(role)
        model_cfg = MODELS.get(role, {})
        agent_name = model_cfg.get("name", role.title())

        total = b.get("total_tasks", 0)
        success_rate = b.get("task_success_rate_pct", 0)
        avg_latency = b.get("avg_latency_ms", 0)
        avg_score = b.get("avg_score", 0)
        total_tokens = b.get("total_tokens", 0)
        error_count = total - b.get("success_count", 0)
        tokens_per_task = total_tokens / max(total, 1)

        insights = []
        strategy_adjustments = []

        # Analyze error patterns
        if error_count > 0 and success_rate < 80:
            insights.append({
                "pattern": "Tekrarlayan başarısızlık",
                "frequency": error_count,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Görev karmaşıklığı eşleştirmesi optimize edilmeli" if success_rate < 50 else None,
                "auto_applied": False,
            })
            strategy_adjustments.append({
                "parameter": "task_complexity_threshold",
                "old_value": "unlimited",
                "new_value": "medium" if success_rate < 50 else "high",
                "reason": f"Başarı oranı %{success_rate:.0f} — karmaşık görevler diğer ajanlara yönlendirilmeli",
                "applied": False,
            })

        if avg_latency > 15000:
            insights.append({
                "pattern": "Yüksek gecikme süresi",
                "frequency": total,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Max token limiti düşürülmeli veya timeout eklenmeli",
                "auto_applied": False,
            })
            current_max = model_cfg.get("max_tokens", 4096)
            strategy_adjustments.append({
                "parameter": "max_tokens",
                "old_value": str(current_max),
                "new_value": str(int(current_max * 0.75)),
                "reason": f"Ortalama gecikme {avg_latency:.0f}ms — token limiti düşürülerek hızlandırılabilir",
                "applied": False,
            })

        if tokens_per_task > 5000:
            insights.append({
                "pattern": "Aşırı token tüketimi",
                "frequency": total,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Prompt optimizasyonu ve çıktı sınırlama",
                "auto_applied": False,
            })
            strategy_adjustments.append({
                "parameter": "temperature",
                "old_value": str(model_cfg.get("temperature", 0.7)),
                "new_value": str(max(0.3, model_cfg.get("temperature", 0.7) - 0.2)),
                "reason": "Daha deterministik çıktılar ile token tasarrufu sağlanabilir",
                "applied": False,
            })

        if avg_score > 0 and avg_score < 3.0:
            insights.append({
                "pattern": "Düşük kalite çıktıları",
                "frequency": total,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Değerlendirme geri bildirimlerinden öğrenme döngüsü kurulmalı",
                "auto_applied": False,
            })
            strategy_adjustments.append({
                "parameter": "evaluation_feedback_loop",
                "old_value": "disabled",
                "new_value": "enabled",
                "reason": f"Kalite skoru {avg_score:.1f}/5.0 — otomatik geri bildirim döngüsü gerekli",
                "applied": False,
            })

        if not insights:
            insights.append({
                "pattern": "Stabil performans",
                "frequency": 0,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Mevcut strateji başarılı, değişiklik gerekmiyor",
                "auto_applied": True,
            })

        # Learning rate: how quickly the agent adapts (simulated based on metrics)
        learning_rate = min(1.0, max(0.1, success_rate / 100 * 0.6 + (1 - min(avg_latency, 30000) / 30000) * 0.4))

        return {
            "agent_role": role,
            "agent_name": agent_name,
            "total_failures": error_count,
            "analyzed_at": _utcnow().isoformat(),
            "insights": insights,
            "strategy_adjustments": strategy_adjustments,
            "learning_rate": round(learning_rate, 3),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failure learning analysis failed: {e}")


@app.post("/api/agents/apply-learning")
async def apply_agent_learning(
    role: str,
    user: dict = Depends(get_current_user),
):
    """Apply learned strategy adjustments for an agent (simulated)."""
    _audit("apply_learning", user["user_id"], detail=role)

    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")

    try:
        from tools.agent_eval import get_performance_baseline
        from config import MODELS

        b = get_performance_baseline(role)
        model_cfg = MODELS.get(role, {})

        total = b.get("total_tasks", 0)
        success_rate = b.get("task_success_rate_pct", 0)
        avg_latency = b.get("avg_latency_ms", 0)
        tokens_per_task = b.get("total_tokens", 0) / max(total, 1)

        details = []
        applied = 0
        skipped = 0

        if success_rate < 80:
            details.append({
                "action": "Görev karmaşıklığı eşiği ayarlandı",
                "result": "applied",
                "reason": f"Başarı oranı %{success_rate:.0f} — karmaşık görevler yeniden yönlendirilecek",
            })
            applied += 1
        else:
            details.append({
                "action": "Görev karmaşıklığı eşiği",
                "result": "skipped",
                "reason": f"Başarı oranı %{success_rate:.0f} — değişiklik gerekmiyor",
            })
            skipped += 1

        if avg_latency > 15000:
            details.append({
                "action": "Token limiti optimize edildi",
                "result": "applied",
                "reason": f"Gecikme {avg_latency:.0f}ms — limit %25 düşürüldü",
            })
            applied += 1
        else:
            details.append({
                "action": "Token limiti optimizasyonu",
                "result": "skipped",
                "reason": f"Gecikme {avg_latency:.0f}ms — kabul edilebilir seviyede",
            })
            skipped += 1

        if tokens_per_task > 5000:
            details.append({
                "action": "Temperature düşürüldü",
                "result": "applied",
                "reason": f"Token/görev {tokens_per_task:.0f} — daha deterministik çıktı",
            })
            applied += 1
        else:
            details.append({
                "action": "Temperature ayarı",
                "result": "skipped",
                "reason": f"Token/görev {tokens_per_task:.0f} — verimli",
            })
            skipped += 1

        return {
            "agent_role": role,
            "applied_count": applied,
            "skipped_count": skipped,
            "details": details,
            "timestamp": _utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apply learning failed: {e}")

# ── 8. Tool Usage Analytics ─────────────────────────────────────

_TOOL_USAGE: list[dict] = []


@app.post("/api/analytics/tool-usage")
async def record_tool_usage(
    tool_name: str,
    agent_role: str,
    latency_ms: float = 0,
    success: bool = True,
    tokens_used: int = 0,
    user: dict = Depends(get_current_user),
):
    """Record a tool usage event for analytics."""
    entry = {
        "id": f"tu-{len(_TOOL_USAGE)}",
        "tool_name": tool_name,
        "agent_role": agent_role,
        "latency_ms": latency_ms,
        "success": success,
        "tokens_used": tokens_used,
        "timestamp": _utcnow().isoformat(),
        "user_id": user["user_id"],
    }
    _TOOL_USAGE.append(entry)
    if len(_TOOL_USAGE) > 500:
        _TOOL_USAGE[:] = _TOOL_USAGE[-500:]
    return {"recorded": True, "total": len(_TOOL_USAGE)}


@app.get("/api/analytics/tool-usage")
async def get_tool_usage_analytics(
    limit: int = 100,
    agent_role: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get tool usage analytics with aggregation."""
    _audit("tool_analytics_view", user["user_id"])

    filtered = _TOOL_USAGE.copy()
    if agent_role:
        filtered = [t for t in filtered if t["agent_role"] == agent_role]

    # Aggregate by tool
    tool_stats: dict[str, dict] = {}
    for entry in filtered:
        name = entry["tool_name"]
        if name not in tool_stats:
            tool_stats[name] = {"tool_name": name, "count": 0, "success_count": 0, "total_latency_ms": 0, "total_tokens": 0, "agents": set()}
        tool_stats[name]["count"] += 1
        if entry["success"]:
            tool_stats[name]["success_count"] += 1
        tool_stats[name]["total_latency_ms"] += entry["latency_ms"]
        tool_stats[name]["total_tokens"] += entry["tokens_used"]
        tool_stats[name]["agents"].add(entry["agent_role"])

    # Convert sets to lists for JSON
    summary = []
    for ts in tool_stats.values():
        count = ts["count"]
        summary.append({
            "tool_name": ts["tool_name"],
            "count": count,
            "success_rate": round(ts["success_count"] / max(count, 1) * 100, 1),
            "avg_latency_ms": round(ts["total_latency_ms"] / max(count, 1), 1),
            "total_tokens": ts["total_tokens"],
            "agents": list(ts["agents"]),
        })
    summary.sort(key=lambda x: x["count"], reverse=True)

    # Aggregate by agent
    agent_stats: dict[str, dict] = {}
    for entry in filtered:
        role = entry["agent_role"]
        if role not in agent_stats:
            agent_stats[role] = {"agent_role": role, "tool_calls": 0, "success_count": 0, "total_latency_ms": 0, "total_tokens": 0, "tools_used": set()}
        agent_stats[role]["tool_calls"] += 1
        if entry["success"]:
            agent_stats[role]["success_count"] += 1
        agent_stats[role]["total_latency_ms"] += entry["latency_ms"]
        agent_stats[role]["total_tokens"] += entry["tokens_used"]
        agent_stats[role]["tools_used"].add(entry["tool_name"])

    agent_summary = []
    for ag in agent_stats.values():
        count = ag["tool_calls"]
        agent_summary.append({
            "agent_role": ag["agent_role"],
            "tool_calls": count,
            "success_rate": round(ag["success_count"] / max(count, 1) * 100, 1),
            "avg_latency_ms": round(ag["total_latency_ms"] / max(count, 1), 1),
            "total_tokens": ag["total_tokens"],
            "tools_used": list(ag["tools_used"]),
        })
    agent_summary.sort(key=lambda x: x["tool_calls"], reverse=True)

    recent = filtered[-min(limit, len(filtered)):]
    recent.reverse()

    return {
        "total_events": len(filtered),
        "by_tool": summary,
        "by_agent": agent_summary,
        "recent": recent,
        "timestamp": _utcnow().isoformat(),
    }


# ── 9. User Behavior Tracking ──────────────────────────────────

_USER_BEHAVIORS: list[dict] = []


@app.post("/api/analytics/user-behavior")
async def record_user_behavior(
    action: str,
    context: str = "",
    metadata: dict | None = None,
    user: dict = Depends(get_current_user),
):
    """Record user behavior event."""
    entry = {
        "id": f"ub-{len(_USER_BEHAVIORS)}",
        "action": action,
        "context": context,
        "metadata": metadata or {},
        "timestamp": _utcnow().isoformat(),
        "user_id": user["user_id"],
    }
    _USER_BEHAVIORS.append(entry)
    if len(_USER_BEHAVIORS) > 500:
        _USER_BEHAVIORS[:] = _USER_BEHAVIORS[-500:]
    return {"recorded": True, "total": len(_USER_BEHAVIORS)}


@app.get("/api/analytics/user-behavior")
async def get_user_behavior_analytics(
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    """Get user behavior analytics."""
    _audit("user_behavior_view", user["user_id"])

    uid = user["user_id"]
    filtered = [b for b in _USER_BEHAVIORS if b["user_id"] == uid]

    # Aggregate by action
    action_counts: dict[str, int] = {}
    for entry in filtered:
        action_counts[entry["action"]] = action_counts.get(entry["action"], 0) + 1

    action_summary = [{"action": k, "count": v} for k, v in sorted(action_counts.items(), key=lambda x: x[1], reverse=True)]

    recent = filtered[-min(limit, len(filtered)):]
    recent.reverse()

    return {
        "total_events": len(filtered),
        "by_action": action_summary,
        "recent": recent,
        "timestamp": _utcnow().isoformat(),
    }

# ---------------------------------------------------------------------------
# 10. Agent Identity — SOUL.md Pattern (Faz 11.6)
# ---------------------------------------------------------------------------

try:
    from tools.agent_identity import IdentityManager as _IdentityManager
    _identity_mgr = _IdentityManager()
except Exception as _e:
    print(f"[Backend] WARNING: agent_identity import failed: {_e}")
    _identity_mgr = None


class IdentityFileUpdate(BaseModel):
    content: str


class MemoryEntryRequest(BaseModel):
    entry: str


@app.get("/api/agents/{role}/identity")
async def get_agent_identity(role: str, user: dict = Depends(get_current_user)):
    """Get all identity files for an agent."""
    _audit("get_agent_identity", user["user_id"], detail=f"role={role}")
    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")
    identity = _identity_mgr.load(role)
    return {
        "role": identity.role,
        "soul": identity.soul,
        "user": identity.user,
        "memory": identity.memory,
        "bootstrap": identity.bootstrap,
    }


@app.put("/api/agents/{role}/identity/{file_type}")
async def update_identity_file(
    role: str, file_type: str, body: IdentityFileUpdate,
    user: dict = Depends(get_current_user),
):
    """Update a specific identity file (soul, user, memory, bootstrap)."""
    _audit("update_identity_file", user["user_id"], detail=f"role={role}, file={file_type}")
    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")
    try:
        _identity_mgr.save_file(role, file_type, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "ok", "role": role, "file_type": file_type}


@app.post("/api/agents/{role}/memory")
async def add_agent_memory_entry(
    role: str, body: MemoryEntryRequest,
    user: dict = Depends(get_current_user),
):
    """Add a new memory entry for an agent."""
    _audit("add_agent_memory", user["user_id"], detail=f"role={role}")
    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")
    _identity_mgr.update_memory(role, body.entry)
    return {"status": "ok", "role": role}


@app.post("/api/agents/identity/initialize")
async def initialize_all_identities(user: dict = Depends(get_current_user)):
    """Initialize identity files for all agents."""
    _audit("initialize_identities", user["user_id"])
    from config import MODELS as _MODELS_CFG
    count = _identity_mgr.initialize_all(_MODELS_CFG)
    agents = _identity_mgr.list_agents()
    return {"initialized": count, "agents": agents}


@app.get("/api/agents/identity/list")
async def list_identity_agents(user: dict = Depends(get_current_user)):
    """List agents that have identity files."""
    agents = _identity_mgr.list_agents()
    return {"agents": agents}


# ── 11. Performance Benchmarking Suite ───────────────────────────

try:
    from tools.benchmark_suite import BenchmarkRunner, get_scenarios, BENCHMARK_SCENARIOS
    _bench_runner = BenchmarkRunner()
    print("[Backend] benchmark_suite loaded OK")
except Exception as _e:
    print(f"[Backend] WARNING: benchmark_suite import failed: {_e}")
    _bench_runner = None
    BENCHMARK_SCENARIOS = {}
    def get_scenarios(cat=None): return []


class BenchmarkRunRequest(BaseModel):
    agent_role: str | None = None
    scenario_id: str | None = None
    category: str | None = None


@app.get("/api/benchmarks/scenarios")
async def list_benchmark_scenarios(
    category: str | None = None,
    user: dict = Depends(get_current_user),
):
    """List available benchmark scenarios."""
    scenarios = get_scenarios(category)
    return {"scenarios": scenarios, "total": len(scenarios)}


@app.get("/api/benchmarks/leaderboard")
async def benchmark_leaderboard(user: dict = Depends(get_current_user)):
    """Get agent leaderboard based on benchmark scores."""
    lb = _bench_runner.get_leaderboard()
    return {"leaderboard": lb}


@app.get("/api/benchmarks/results")
async def benchmark_results(
    agent_role: str | None = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Get benchmark results with optional agent filter."""
    results = _bench_runner.get_results(agent_role=agent_role, limit=limit)
    return {"results": results, "total": len(results)}


@app.post("/api/benchmarks/run")
async def run_benchmark(body: BenchmarkRunRequest, user: dict = Depends(get_current_user)):
    """Run benchmark scenario(s) for an agent."""
    _audit("run_benchmark", user["user_id"], detail=f"role={body.agent_role}, scenario={body.scenario_id}, cat={body.category}")
    try:
        if body.scenario_id and body.agent_role:
            # Single scenario run
            result = await _bench_runner.run_single(body.agent_role, body.scenario_id)
            return {"result": result, "type": "single"}
        else:
            # Suite run
            summary = await _bench_runner.run_suite(
                agent_role=body.agent_role,
                category=body.category,
            )
            return {"summary": summary, "type": "suite"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {e}")


@app.get("/api/benchmarks/compare")
async def compare_agents_benchmark(
    role_a: str,
    role_b: str,
    user: dict = Depends(get_current_user),
):
    """Compare two agents head-to-head on benchmark scores."""
    try:
        comparison = _bench_runner.compare_agents(role_a, role_b)
        return {"comparison": comparison}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/benchmarks/history")
async def benchmark_history(
    agent_role: str,
    scenario_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get historical benchmark scores for trend analysis."""
    history = _bench_runner.get_history(agent_role, scenario_id)
    return {"history": history, "agent_role": agent_role}


# ── 12. Error Pattern Analysis ───────────────────────────────────

try:
    from tools.error_patterns import get_error_analyzer
    _error_analyzer = get_error_analyzer()
    print("[Backend] error_patterns loaded OK")
except Exception as _e:
    print(f"[Backend] WARNING: error_patterns import failed: {_e}")
    _error_analyzer = None

# ── 13. Cost Tracking ────────────────────────────────────────────

try:
    from tools.cost_tracker import get_cost_tracker
    _cost_tracker = get_cost_tracker()
    print("[Backend] cost_tracker loaded OK")
except Exception as _e:
    print(f"[Backend] WARNING: cost_tracker import failed: {_e}")
    _cost_tracker = None


class RecordErrorRequest(BaseModel):
    agent_role: str
    error_message: str
    task_type: str = "general"
    context: dict | None = None


class ResolvePatternRequest(BaseModel):
    resolution_notes: str = ""


@app.post("/api/errors/record")
async def record_error_event(body: RecordErrorRequest, user: dict = Depends(get_current_user)):
    """Record an error event and auto-classify it."""
    try:
        event = _error_analyzer.record_error(
            agent_role=body.agent_role,
            error_message=body.error_message,
            task_type=body.task_type,
            context=body.context,
        )
        return {"event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Record error failed: {e}")


@app.get("/api/errors/stats")
async def error_stats(
    agent_role: str | None = None,
    hours: int = 24,
    user: dict = Depends(get_current_user),
):
    """Get aggregated error statistics."""
    stats = _error_analyzer.get_error_stats(agent_role=agent_role, hours=hours)
    return {"stats": stats}


@app.get("/api/errors/timeline")
async def error_timeline(
    hours: int = 24,
    user: dict = Depends(get_current_user),
):
    """Get hourly error counts for timeline chart."""
    timeline = _error_analyzer.get_error_timeline(hours=hours)
    return {"timeline": timeline}


@app.get("/api/errors/patterns")
async def list_error_patterns(
    status: str | None = None,
    agent_role: str | None = None,
    user: dict = Depends(get_current_user),
):
    """List detected error patterns."""
    patterns = _error_analyzer.get_patterns(status=status, agent_role=agent_role)
    return {"patterns": patterns, "total": len(patterns)}


@app.post("/api/errors/detect")
async def detect_error_patterns(
    hours: int = 24,
    user: dict = Depends(get_current_user),
):
    """Run pattern detection on recent errors."""
    _audit("detect_error_patterns", user["user_id"], detail=f"hours={hours}")
    new_patterns = _error_analyzer.detect_patterns(window_hours=hours)
    return {"new_patterns": new_patterns, "total_new": len(new_patterns)}


@app.get("/api/errors/recommendations")
async def error_recommendations(user: dict = Depends(get_current_user)):
    """Get optimization recommendations based on active error patterns."""
    recs = _error_analyzer.get_recommendations()
    return {"recommendations": recs, "total": len(recs)}


@app.post("/api/errors/patterns/{pattern_id}/resolve")
async def resolve_error_pattern(
    pattern_id: int,
    body: ResolvePatternRequest,
    user: dict = Depends(get_current_user),
):
    """Mark an error pattern as resolved."""
    _audit("resolve_pattern", user["user_id"], detail=f"pattern={pattern_id}")
    success = _error_analyzer.resolve_pattern(pattern_id, body.resolution_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return {"resolved": True, "pattern_id": pattern_id}


@app.post("/api/errors/patterns/{pattern_id}/suppress")
async def suppress_error_pattern(
    pattern_id: int,
    user: dict = Depends(get_current_user),
):
    """Suppress a noisy error pattern."""
    _audit("suppress_pattern", user["user_id"], detail=f"pattern={pattern_id}")
    success = _error_analyzer.suppress_pattern(pattern_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return {"suppressed": True, "pattern_id": pattern_id}

# ── 13. Cost Tracking Endpoints ──────────────────────────────────


class RecordUsageRequest(BaseModel):
    agent_role: str
    model: str
    input_tokens: int
    output_tokens: int
    task_type: str = "general"
    metadata: dict | None = None


class SetBudgetRequest(BaseModel):
    agent_role: str | None = None
    daily_limit: float
    alert_threshold: float = 0.8


@app.post("/api/costs/record")
async def record_usage_event(body: RecordUsageRequest, user: dict = Depends(get_current_user)):
    """Record a token usage event."""
    try:
        event = _cost_tracker.record_usage(
            agent_role=body.agent_role,
            model=body.model,
            input_tokens=body.input_tokens,
            output_tokens=body.output_tokens,
            task_type=body.task_type,
            metadata=body.metadata,
        )
        return {"event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Record usage failed: {e}")


@app.get("/api/costs/summary")
async def cost_summary(hours: int = 24, user: dict = Depends(get_current_user)):
    """Get aggregated cost summary."""
    return _cost_tracker.get_cost_summary(hours=hours)


@app.get("/api/costs/timeline")
async def cost_timeline(hours: int = 24, granularity: str = "hour", user: dict = Depends(get_current_user)):
    """Get cost timeline data."""
    return {"timeline": _cost_tracker.get_cost_timeline(hours=hours, granularity=granularity)}


@app.get("/api/costs/agent/{agent_role}")
async def agent_costs(agent_role: str, hours: int = 24, user: dict = Depends(get_current_user)):
    """Get detailed cost breakdown for a specific agent."""
    return _cost_tracker.get_agent_costs(agent_role=agent_role, hours=hours)


@app.get("/api/costs/top-consumers")
async def top_consumers(hours: int = 24, limit: int = 10, user: dict = Depends(get_current_user)):
    """Get agents ranked by cost."""
    return {"consumers": _cost_tracker.get_top_consumers(hours=hours, limit=limit)}


@app.post("/api/costs/budget")
async def set_budget(body: SetBudgetRequest, user: dict = Depends(get_current_user)):
    """Set or update a daily budget."""
    _audit("set_budget", user["user_id"], detail=f"agent={body.agent_role} limit={body.daily_limit}")
    return _cost_tracker.set_budget(
        agent_role=body.agent_role,
        daily_limit=body.daily_limit,
        alert_threshold=body.alert_threshold,
    )


@app.get("/api/costs/budget")
async def check_budget(agent_role: str | None = None, user: dict = Depends(get_current_user)):
    """Check budget status."""
    return _cost_tracker.check_budget(agent_role=agent_role)


@app.get("/api/costs/forecast")
async def cost_forecast(days: int = 7, user: dict = Depends(get_current_user)):
    """Get cost forecast based on trends."""
    return _cost_tracker.get_cost_forecast(days=days)


@app.get("/api/costs/stats")
async def usage_stats(user: dict = Depends(get_current_user)):
    """Get overall usage statistics."""
    return _cost_tracker.get_usage_stats()


# ── Auto-Optimizer API ───────────────────────────────────────────

try:
    from tools.auto_optimizer import get_auto_optimizer
    _auto_optimizer = get_auto_optimizer()
    print("[Backend] auto_optimizer loaded OK")
except Exception as _e:
    print(f"[Backend] WARNING: auto_optimizer import failed: {_e}")
    _auto_optimizer = None


@app.get("/api/optimizer/stats")
async def optimizer_stats(user: dict = Depends(get_current_user)):
    """Get optimization statistics summary."""
    stats = _auto_optimizer.get_optimization_stats()
    return stats


@app.get("/api/optimizer/recommendations")
async def optimizer_recommendations(
    category: str | None = None,
    priority: str | None = None,
    status: str = "pending",
    user: dict = Depends(get_current_user),
):
    """List recommendations with optional filters."""
    recs = _auto_optimizer.get_recommendations(
        category=category, priority=priority, status=status
    )
    return {"recommendations": recs, "total": len(recs)}


@app.post("/api/optimizer/analyze")
async def optimizer_analyze(user: dict = Depends(get_current_user)):
    """Run full analysis and generate new recommendations."""
    _audit("optimizer_analyze", user["user_id"])
    new_recs = _auto_optimizer.analyze_and_recommend()
    return {"new_recommendations": new_recs, "total_new": len(new_recs)}


@app.post("/api/optimizer/recommendations/{rec_id}/apply")
async def optimizer_apply(
    rec_id: int,
    user: dict = Depends(get_current_user),
):
    """Apply a pending recommendation."""
    _audit("optimizer_apply", user["user_id"], detail=f"rec={rec_id}")
    result = _auto_optimizer.apply_recommendation(rec_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/optimizer/recommendations/{rec_id}/dismiss")
async def optimizer_dismiss(
    rec_id: int,
    user: dict = Depends(get_current_user),
):
    """Dismiss a pending recommendation."""
    _audit("optimizer_dismiss", user["user_id"], detail=f"rec={rec_id}")
    result = _auto_optimizer.dismiss_recommendation(rec_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/optimizer/agent/{agent_role}")
async def optimizer_agent_profile(
    agent_role: str,
    user: dict = Depends(get_current_user),
):
    """Get optimization profile for a specific agent."""
    profile = _auto_optimizer.get_agent_optimization_profile(agent_role)
    return profile


@app.get("/api/optimizer/history")
async def optimizer_history(
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Get optimization action history."""
    history = _auto_optimizer.get_optimization_history(limit=limit)
    return {"history": history, "total": len(history)}

# ── Startup Diagnostic ───────────────────────────────────────────
_all_api_routes = [r.path for r in app.routes if hasattr(r, 'path') and '/api/' in r.path]
print(f"[Backend] Total API routes registered: {len(_all_api_routes)}")
print(f"[Backend] Benchmark routes: {any('benchmark' in r for r in _all_api_routes)}")
print(f"[Backend] Error routes: {any('/errors/' in r for r in _all_api_routes)}")
print(f"[Backend] Cost routes: {any('/costs/' in r for r in _all_api_routes)}")
print(f"[Backend] Optimizer routes: {any('/optimizer/' in r for r in _all_api_routes)}")
print(f"[Backend] Identity routes: {any('/identity/' in r for r in _all_api_routes)}")
print(f"[Backend] ✓ All {len(_all_api_routes)} routes loaded successfully")
