"""
Multi-Agent Ops Center — FastAPI Backend (Modular).
App setup, middleware, lifespan + router includes.
All endpoints live in backend/routes/*.py modules.
"""
# RELOAD_TRIGGER: force uvicorn reload — 2026-03-07

import os
import sys
import time
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent dir so we can import existing modules (agents, pipelines, tools, core, config)
_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import _validate_signed_token, rate_limiter as _rate_limiter


# ── Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Structured logging — must be first so all subsequent logs are JSON
    try:
        from tools.observability import setup_structured_logging
        setup_structured_logging()
    except Exception as e:
        print(f"[Backend] Structured logging init failed: {e}")

    pg_available = False
    try:
        from tools.pg_connection import init_database, postgres_available
        pg_available = postgres_available()
        if pg_available:
            init_database()
            print("[Backend] PostgreSQL initialized successfully")
        else:
            print("[Backend] PostgreSQL unavailable; running in degraded DB-less mode")
    except Exception as e:
        print(f"[Backend] PostgreSQL init failed (SQLite fallback): {e}")

    # Create execution_traces table
    try:
        if pg_available:
            from tools.observability import init_traces_table
            init_traces_table()
            print("[Backend] execution_traces table initialized")
        else:
            print("[Backend] execution_traces init skipped (PostgreSQL unavailable)")
    except Exception as e:
        print(f"[Backend] execution_traces init failed (non-critical): {e}")

    # Run migration 005: agent_metrics_log + skills schema extension
    if pg_available:
        try:
            from tools.pg_connection import get_conn, release_conn
            import pathlib
            _mig_path = pathlib.Path(__file__).parent / "migrations" / "005_performance_metrics.sql"
            if _mig_path.exists():
                _mig_sql = _mig_path.read_text(encoding="utf-8")
                _mig_conn = get_conn()
                try:
                    with _mig_conn.cursor() as cur:
                        for stmt in _mig_sql.split(";"):
                            stmt = stmt.strip()
                            if stmt and not stmt.startswith("--"):
                                cur.execute(stmt)
                    _mig_conn.commit()
                    print("[Backend] Migration 005 (agent_metrics_log) applied", flush=True)
                except Exception as e:
                    _mig_conn.rollback()
                    print(f"[Backend] Migration 005 failed: {e}", flush=True)
                finally:
                    release_conn(_mig_conn)
        except Exception as e:
            print(f"[Backend] Migration 005 load failed: {e}", flush=True)
    else:
        print("[Backend] Migration 005 skipped (PostgreSQL unavailable)", flush=True)

    # Run migration 006: SQLite → PostgreSQL (schedules, benchmarks, evaluations, etc.)
    if pg_available:
        try:
            from tools.pg_connection import get_conn, release_conn
            import pathlib
            _mig006_path = pathlib.Path(__file__).parent / "migrations" / "006_sqlite_to_pg_migration.sql"
            if _mig006_path.exists():
                _mig006_sql = _mig006_path.read_text(encoding="utf-8")
                _mig006_conn = get_conn()
                try:
                    with _mig006_conn.cursor() as cur:
                        for stmt in _mig006_sql.split(";"):
                            stmt = stmt.strip()
                            if stmt and not stmt.startswith("--"):
                                cur.execute(stmt)
                    _mig006_conn.commit()
                    print("[Backend] Migration 006 (SQLite→PG) applied", flush=True)
                except Exception as e:
                    _mig006_conn.rollback()
                    print(f"[Backend] Migration 006 failed: {e}", flush=True)
                finally:
                    release_conn(_mig006_conn)
        except Exception as e:
            print(f"[Backend] Migration 006 load failed: {e}", flush=True)
    else:
        print("[Backend] Migration 006 skipped (PostgreSQL unavailable)", flush=True)

    # Create analytics tables
    if pg_available:
        try:
            from tools.pg_connection import get_conn, release_conn
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tool_usage (
                        id SERIAL PRIMARY KEY,
                        tool_name TEXT NOT NULL,
                        agent_role TEXT NOT NULL,
                        latency_ms REAL DEFAULT 0,
                        success INTEGER DEFAULT 1,
                        tokens_used INTEGER DEFAULT 0,
                        user_id TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_behavior (
                        id SERIAL PRIMARY KEY,
                        action TEXT NOT NULL,
                        context TEXT DEFAULT '',
                        metadata JSONB DEFAULT '{}',
                        user_id TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tool_usage_user_id
                    ON tool_usage(user_id, timestamp DESC)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_behavior_user_id
                    ON user_behavior(user_id, timestamp DESC)
                """)
            conn.commit()
            release_conn(conn)
            print("[Backend] Analytics tables initialized")
        except Exception as e:
            print(f"[Backend] Analytics tables init failed: {e}")
    else:
        print("[Backend] Analytics tables init skipped (PostgreSQL unavailable)")

    # Seed default MCP servers for orchestration + discover tools
    try:
        from tools.mcp_client import seed_default_servers, list_servers, discover_tools
        seeded = seed_default_servers()
        if seeded:
            print(f"[Backend] Seeded {seeded} default MCP servers")
        # Auto-discover tools from all active servers (background, non-blocking)
        servers = list_servers(active_only=True)
        discovered_total = 0
        for srv in servers:
            try:
                tools = await discover_tools(srv["id"])
                discovered_total += len(tools)
            except Exception:
                pass  # Individual server failures are non-critical
        if discovered_total:
            print(f"[Backend] Discovered {discovered_total} MCP tools from {len(servers)} servers")
        else:
            print(f"[Backend] MCP tool discovery: 0 tools (servers may not be installed locally)")
    except Exception as e:
        print(f"[Backend] MCP seed/discovery failed (non-critical): {e}")

    # Workflow cron scheduler (APScheduler + SQLite)
    try:
        from tools.workflow_scheduler import init_scheduler
        await init_scheduler()
        print("[Backend] Workflow scheduler initialized")
    except Exception as e:
        print(f"[Backend] Workflow scheduler failed (non-critical): {e}")

    # Agent identity (SOUL.md) — ensure default profiles exist if none present
    try:
        from tools.agent_identity import IdentityManager
        from config import MODELS as _MODELS
        mgr = IdentityManager()
        agents = mgr.list_agents()
        if not agents and _MODELS:
            n = mgr.initialize_all(_MODELS)
            if n:
                print(f"[Backend] Agent identity initialized for {n} agents (SOUL.md)")
    except Exception as e:
        print(f"[Backend] Agent identity init skipped (non-critical): {e}")

    # Register tool schemas with pi-gateway (Faz 14.3)
    try:
        from tools.tool_schema_registry import register_with_gateway
        gw_result = await register_with_gateway()
        gw_status = gw_result.get("status", gw_result.get("registered", "?"))
        print(f"[Backend] Tool schema registration: {gw_status}")
    except Exception as e:
        print(f"[Backend] Tool schema registration skipped (non-critical): {e}")

    # Heartbeat scheduler (Faz 11.2 — proaktif agent görevleri)
    try:
        from tools.heartbeat import get_heartbeat_scheduler, HeartbeatTask, HeartbeatFrequency
        scheduler = get_heartbeat_scheduler()
        
        # Evolution task: periodic auto-optimizer analysis
        async def run_evolution_analysis():
            try:
                from tools.auto_optimizer import get_auto_optimizer
                opt = get_auto_optimizer()
                new_recs = opt.analyze_and_recommend()
                auto_result = opt.auto_apply_safe_recommendations(confidence_threshold=0.85)
                return {
                    "new_recommendations": len(new_recs),
                    "auto_applied": auto_result.get("applied_count", 0),
                    "skipped": auto_result.get("skipped_count", 0),
                }
            except Exception as e:
                return {"error": str(e)}
        
        scheduler.register(HeartbeatTask(
            name="evolution_analysis",
            frequency=HeartbeatFrequency.HOURLY,
            handler=run_evolution_analysis,
            enabled=True,
        ))
        
        await scheduler.start()
        print("[Backend] Heartbeat scheduler started (with evolution task)")
    except Exception as e:
        print(f"[Backend] Heartbeat scheduler failed (non-critical): {e}")

    # Scheduled Tasks scheduler (APScheduler-based cron tasks)
    try:
        from tools.scheduled_tasks import init_scheduled_tasks
        await init_scheduled_tasks()
        print("[Backend] Scheduled tasks scheduler initialized")
    except Exception as e:
        print(f"[Backend] Scheduled tasks init failed (non-critical): {e}")

    # Autonomous chat background scheduler (messaging module)
    # Auto-start disabled — manual trigger only via POST /api/agents/autonomous-chat/trigger
    try:
        from routes.messaging import start_auto_chat_scheduler  # noqa: F401
        print("[Backend] Autonomous chat scheduler available (manual trigger only)")
    except Exception as e:
        print(f"[Backend] Autonomous chat auto-start failed (non-critical): {e}")

    # Cleanup expired working memory entries
    try:
        from tools.memory import cleanup_expired_working_memory
        cleaned = cleanup_expired_working_memory()
        if cleaned:
            print(f"[Backend] Cleaned {cleaned} expired working memory entries")
    except Exception as e:
        print(f"[Backend] Working memory cleanup failed (non-critical): {e}")

    # Faz 16: Start Self-Improvement Feedback Loop
    try:
        from tools.feedback_loop import get_feedback_loop
        await get_feedback_loop().start()
        print("[Backend] Self-Improvement Feedback Loop started")
    except Exception as e:
        print(f"[Backend] Feedback Loop start failed (non-critical): {e}")

    # Initialize OpenTelemetry (optional — requires SDK)
    try:
        from tools.otel_integration import init_otel
        otel_ok = init_otel()
        if otel_ok:
            print("[Backend] OpenTelemetry initialized")
        else:
            print("[Backend] OpenTelemetry SDK not available (non-critical)")
    except Exception as e:
        print(f"[Backend] OpenTelemetry init failed (non-critical): {e}")

    # Initialize Redis client (optional — falls back to in-memory)
    try:
        from tools.redis_client import get_redis, redis_health
        r = get_redis()
        rh = redis_health()
        print(f"[Backend] Redis: {rh.get('status', 'unknown')} (mode={rh.get('mode', 'fallback')})")
    except Exception as e:
        print(f"[Backend] Redis init failed (in-memory fallback): {e}")

    # Initialize Knowledge Moderator tables
    try:
        from tools.knowledge_moderator import get_moderator
        get_moderator()._ensure_table()
        print("[Backend] Knowledge moderation tables initialized")
    except Exception as e:
        print(f"[Backend] Knowledge moderation init failed (non-critical): {e}")

    # Install inter-agent monitor middleware on EventBus at startup
    try:
        from routes.inter_agent import _install_bus_middleware
        _install_bus_middleware()
        print("[Backend] Inter-agent monitor middleware installed on EventBus")
    except Exception as e:
        print(f"[Backend] Inter-agent monitor middleware failed (non-critical): {e}")

    yield

    # Shutdown: stop autonomous chat scheduler
    try:
        from routes.messaging import stop_auto_chat_scheduler
        await stop_auto_chat_scheduler()
    except Exception:
        pass

    # Shutdown: stop heartbeat
    try:
        from tools.heartbeat import get_heartbeat_scheduler
        await get_heartbeat_scheduler().stop()
    except Exception:
        pass

    # Shutdown: stop scheduled tasks
    try:
        from tools.scheduled_tasks import shutdown_scheduled_tasks
        await shutdown_scheduled_tasks()
    except Exception:
        pass


# ── App Creation ─────────────────────────────────────────────────

app = FastAPI(title="Multi-Agent Ops Center API", version="3.0.0", lifespan=lifespan)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
if _cors_origins == ["*"]:
    import logging as _log
    _log.getLogger("backend").warning(
        "CORS allow_origins=['*'] — restrict to specific origins in production via CORS_ORIGINS env var"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id"],
)


# ── Middleware ────────────────────────────────────────────────────

@app.middleware("http")
async def trace_id_middleware(request, call_next):
    """Inject trace_id into every request for end-to-end tracing."""
    from tools.observability import new_trace_id, get_trace_id
    tid = new_trace_id()
    response = await call_next(request)
    response.headers["X-Trace-Id"] = tid
    return response


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
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# ── Router Includes ──────────────────────────────────────────────

from routes.auth_and_tools import router as auth_router
from routes.skills_and_workflows import router as skills_router
from routes.analytics import router as analytics_router
from routes.messaging import router as messaging_router
from routes.monitoring import router as monitoring_router
from routes.collaboration import router as collab_router
from routes.memory_and_export import router as memory_router
from routes.system import router as system_router
from routes.identity import router as identity_router
from routes.social import router as social_router
from routes.heartbeat_routes import router as heartbeat_router
from routes.chat_ws import router as chat_ws_router
from routes.learning_hub import router as learning_hub_router
from routes.gateway import router as gateway_router
from routes.documents import router as documents_router
from routes.mcp_management import router as mcp_router
from routes.rag_pipeline import router as rag_pipeline_router
from routes.traces import router as traces_router
from routes.agent_comm import router as agent_comm_router
from routes.marketplace import router as marketplace_router
from routes.self_improvement import router as self_improvement_router
from routes.presentations import router as presentations_router
from routes.metrics import router as metrics_router
from routes.resilience import router as resilience_router
from routes.federated import router as federated_router
from routes.inter_agent import router as inter_agent_router
from routes.ocr import router as ocr_router
from routes.youtube import router as youtube_router
from routes.workspace import router as workspace_router

app.include_router(auth_router)
app.include_router(skills_router)
app.include_router(analytics_router)
app.include_router(messaging_router)
app.include_router(monitoring_router)
app.include_router(collab_router)
app.include_router(memory_router)
app.include_router(system_router)
app.include_router(identity_router)
app.include_router(social_router)
app.include_router(heartbeat_router)
app.include_router(chat_ws_router)
app.include_router(learning_hub_router)
app.include_router(gateway_router)
app.include_router(documents_router)
app.include_router(mcp_router)
app.include_router(rag_pipeline_router)
app.include_router(traces_router)
app.include_router(agent_comm_router)
app.include_router(marketplace_router)
app.include_router(self_improvement_router)
app.include_router(presentations_router)
app.include_router(metrics_router)
app.include_router(resilience_router)
app.include_router(federated_router)
app.include_router(inter_agent_router)
app.include_router(ocr_router)
app.include_router(youtube_router)
app.include_router(workspace_router)

print("[Backend] All route modules loaded successfully")
print(f"[Backend] Modules: auth_and_tools, skills_and_workflows, analytics, messaging, monitoring, collaboration, memory_and_export, system, identity, social, heartbeat, chat_ws, learning_hub, gateway, documents, mcp_management, rag_pipeline, traces, agent_comm, marketplace, self_improvement, presentations, resilience, federated, inter_agent, ocr, youtube, workspace")
