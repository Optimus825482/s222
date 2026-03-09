"""
Resilience API — Prometheus metrics, chaos engineering, knowledge moderation,
dynamic thresholds, Redis health, and OpenTelemetry status.

Endpoints:
  GET  /api/metrics              — Prometheus text exposition
  GET  /api/resilience/health    — Full system health (Redis, OTel, PG)
  GET  /api/resilience/thresholds — Dynamic threshold values
  POST /api/resilience/thresholds/invalidate — Clear threshold cache
  GET  /api/chaos/report         — Chaos engineering report
  POST /api/chaos/inject         — Inject fault scenario
  POST /api/chaos/toggle         — Enable/disable chaos engine
  GET  /api/moderate/queue       — Pending knowledge moderation queue
  POST /api/moderate/solution    — Submit solution for moderation
  POST /api/moderate/review      — Human review decision
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic Models ──────────────────────────────────────────────

class ChaosInjectRequest(BaseModel):
    scenario: str
    target: str = ""
    duration_s: float = 5.0
    intensity: float = 0.5


class ChaosToggleRequest(BaseModel):
    enabled: bool


class SolutionSubmitRequest(BaseModel):
    solution: str
    confidence: float = 0.0
    source_agents: list[str] = []
    context: dict[str, Any] = {}


class ReviewRequest(BaseModel):
    queue_id: int
    approved: bool
    reviewer: str = "human"
    note: str = ""


class ThresholdRequest(BaseModel):
    metric_name: str
    agent_role: str = ""
    window_days: int = 7


# ── Prometheus Metrics ───────────────────────────────────────────

@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus scrape endpoint — text exposition format."""
    try:
        from tools.prometheus_metrics import get_metrics
        m = get_metrics()
        return PlainTextResponse(m.generate_text_metrics(), media_type="text/plain")
    except Exception as e:
        logger.error(f"Metrics generation failed: {e}")
        return PlainTextResponse(f"# Error: {e}\n", status_code=500)


# ── System Health ────────────────────────────────────────────────

@router.get("/resilience/health")
async def resilience_health():
    """Full system health check — Redis, OTel, PG, EventBus."""
    health: dict[str, Any] = {"status": "healthy", "components": {}}

    # Redis
    try:
        from tools.redis_client import redis_health
        health["components"]["redis"] = redis_health()
    except Exception as e:
        health["components"]["redis"] = {"status": "unavailable", "error": str(e)}

    # PostgreSQL
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        release_conn(conn)
        health["components"]["postgres"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["postgres"] = {"status": "unhealthy", "error": str(e)}

    # EventBus
    try:
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        stats = bus.get_stats()
        health["components"]["event_bus"] = {
            "status": "running" if stats.get("running") else "stopped",
            "channels": stats.get("channel_count", 0),
            "dlq_size": stats.get("dlq_size", 0),
        }
    except Exception as e:
        health["components"]["event_bus"] = {"status": "error", "error": str(e)}

    # OpenTelemetry
    try:
        from tools.otel_integration import _otel_available, _tracer
        health["components"]["opentelemetry"] = {
            "sdk_installed": _otel_available,
            "tracer_active": _tracer is not None,
        }
    except Exception:
        health["components"]["opentelemetry"] = {"sdk_installed": False}

    # Chaos engine
    try:
        from tools.chaos_engine import get_chaos_engine
        ce = get_chaos_engine()
        health["components"]["chaos_engine"] = {"enabled": ce.is_enabled}
    except Exception:
        health["components"]["chaos_engine"] = {"enabled": False}

    # Overall status
    pg_ok = health["components"].get("postgres", {}).get("status") == "healthy"
    if not pg_ok:
        health["status"] = "degraded"

    return health


# ── Dynamic Thresholds ───────────────────────────────────────────

@router.get("/resilience/thresholds")
async def get_thresholds(metric_name: str = "latency_ms", agent_role: str = "", window_days: int = 7):
    """Get dynamic thresholds for a metric."""
    try:
        from tools.dynamic_thresholds import get_threshold_engine
        engine = get_threshold_engine()
        return engine.compute(metric_name, agent_role, window_days)
    except Exception as e:
        raise HTTPException(500, f"Threshold computation failed: {e}")


@router.post("/resilience/thresholds/invalidate")
async def invalidate_thresholds(metric_name: str = "", agent_role: str = ""):
    """Clear threshold cache."""
    try:
        from tools.dynamic_thresholds import get_threshold_engine
        engine = get_threshold_engine()
        cleared = engine.invalidate_cache(metric_name, agent_role)
        return {"cleared": cleared}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Chaos Engineering ────────────────────────────────────────────

@router.get("/chaos/report")
async def chaos_report():
    """Get chaos engineering report."""
    try:
        from tools.chaos_engine import get_chaos_engine
        return get_chaos_engine().get_report()
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/chaos/inject")
async def chaos_inject(req: ChaosInjectRequest):
    """Inject a fault scenario."""
    try:
        from tools.chaos_engine import get_chaos_engine
        ce = get_chaos_engine()
        if not ce.is_enabled:
            raise HTTPException(400, "Chaos engine is not enabled. POST /api/chaos/toggle first.")
        result = await ce.inject(req.scenario, req.target, req.duration_s, req.intensity)
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/chaos/toggle")
async def chaos_toggle(req: ChaosToggleRequest):
    """Enable or disable chaos engine."""
    try:
        from tools.chaos_engine import get_chaos_engine
        ce = get_chaos_engine()
        if req.enabled:
            ce.enable()
        else:
            ce.disable()
        return {"enabled": ce.is_enabled}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Knowledge Moderation ─────────────────────────────────────────

@router.get("/moderate/queue")
async def moderation_queue(limit: int = 20):
    """Get pending solutions awaiting human review."""
    try:
        from tools.knowledge_moderator import get_moderator
        return get_moderator().get_pending_queue(limit)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/moderate/solution")
async def submit_solution(req: SolutionSubmitRequest):
    """Submit a solution for moderation."""
    if not req.solution.strip():
        raise HTTPException(400, "Solution text is required")
    try:
        from tools.knowledge_moderator import get_moderator
        result = await get_moderator().submit(
            solution=req.solution,
            confidence=req.confidence,
            source_agents=req.source_agents,
            context=req.context,
        )
        return result.model_dump()
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/moderate/review")
async def review_solution(req: ReviewRequest):
    """Human reviews a queued solution."""
    try:
        from tools.knowledge_moderator import get_moderator
        success = get_moderator().review(req.queue_id, req.approved, req.reviewer, req.note)
        if not success:
            raise HTTPException(404, "Queue item not found or already reviewed")
        return {"success": True, "queue_id": req.queue_id, "approved": req.approved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
