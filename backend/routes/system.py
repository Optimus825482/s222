"""System routes: cache, circuit breaker, confidence, overview, sandbox, PII, health."""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from config import MODELS, RUNTIME_EVENT_SCHEMA_VERSION, get_feature_flags, get_model_capabilities, get_provider_registry_summary
from core.models import PipelineType

router = APIRouter()


# ── Cache Management ─────────────────────────────────────────────

@router.get("/api/cache/stats")
async def api_cache_stats(user: dict = Depends(get_current_user)):
    """Get response cache statistics."""
    from tools.cache import cache_stats
    return cache_stats()


@router.post("/api/cache/clear")
async def api_cache_clear(user: dict = Depends(get_current_user)):
    """Clear the response cache."""
    from tools.cache import clear_cache
    cleared = await clear_cache()
    _audit("cache_clear", user["user_id"], f"Cleared {cleared} entries")
    return {"cleared": cleared}


# ── Circuit Breaker ──────────────────────────────────────────────

@router.get("/api/circuit-breaker/status")
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


@router.post("/api/circuit-breaker/reset")
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

@router.post("/api/confidence/analyze")
async def api_confidence_analyze(
    text: str,
    agent_role: str = "general",
    task_type: str = "general",
    user: dict = Depends(get_current_user),
):
    """Analyze confidence of a text output."""
    from tools.confidence import score_confidence
    return score_confidence(text, agent_role, task_type)


# ── Agent tools (role → allowed tool names) ───────────────────────

@router.get("/api/agents/tools")
async def api_agents_tools(user: dict = Depends(get_current_user)):
    """List tools each agent role is allowed to use (for UI display)."""
    from tools.sandbox import ROLE_ALLOWLIST
    return {
        role: sorted(list(tools))
        for role, tools in ROLE_ALLOWLIST.items()
    }


# ── System Overview ──────────────────────────────────────────────

@router.get("/api/system/overview")
async def api_system_overview(user: dict = Depends(get_current_user)):
    """Comprehensive system overview: agents, cache, circuit breakers."""
    from tools.cache import cache_stats
    from tools.circuit_breaker import get_circuit_breaker

    cb = get_circuit_breaker()
    cb_status = cb.status()

    queueing: dict = {"available": False}
    scheduled_info: dict = {"available": False}
    sandbox_info: dict = {"available": False}

    try:
        from core.event_bus import get_event_bus
        from core.task_delegation import get_task_delegation_manager

        event_bus = get_event_bus()
        delegation = get_task_delegation_manager()
        queueing = {
            "available": True,
            "event_bus": event_bus.get_stats(),
            "delegation": delegation.get_stats(),
        }
    except Exception as e:
        queueing = {"available": False, "error": str(e)}

    try:
        from tools.scheduled_tasks import get_scheduled_task_scheduler, get_execution_history

        scheduler = get_scheduled_task_scheduler()
        scheduled_tasks = await scheduler.list_tasks()
        recent_executions = get_execution_history(limit=20)
        scheduled_info = {
            "available": True,
            "total": len(scheduled_tasks),
            "enabled": sum(1 for task in scheduled_tasks if getattr(task, "enabled", False)),
            "recent_execution_count": len(recent_executions),
            "recent_executions": recent_executions[:5],
        }
    except Exception as e:
        scheduled_info = {"available": False, "error": str(e)}

    try:
        from tools.code_executor import get_executor_capabilities

        sandbox_info = {
            "available": True,
            **get_executor_capabilities(),
        }
    except Exception as e:
        sandbox_info = {"available": False, "error": str(e)}

    available_agents = sum(1 for s in cb_status.values() if s["state"] == "closed")
    total_tracked = len(cb_status)
    rollout_ready = bool(queueing.get("available") and scheduled_info.get("available") and sandbox_info.get("available"))

    return {
        "cache": cache_stats(),
        "circuit_breakers": cb_status,
        "agents": {
            "available": available_agents,
            "total_tracked": total_tracked,
            "all_healthy": all(s["state"] == "closed" for s in cb_status.values()) if cb_status else True,
        },
        "runtime": {
            "schema_version": RUNTIME_EVENT_SCHEMA_VERSION,
            "feature_flags": get_feature_flags(),
            "rollout_ready": rollout_ready,
            "provider_registry": get_provider_registry_summary(),
            "capabilities": {
                role: get_model_capabilities(role)
                for role in sorted({cfg["role"] for cfg in MODELS.values()})
            },
        },
        "queueing": queueing,
        "scheduled_tasks": scheduled_info,
        "sandbox": sandbox_info,
    }


@router.get("/api/sandbox/audit")
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


@router.get("/api/pii/stats")
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

@router.get("/api/health")
async def health():
    flags = get_feature_flags()
    queueing_ready = scheduled_ready = sandbox_ready = True

    try:
        from core.event_bus import get_event_bus
        from core.task_delegation import get_task_delegation_manager

        get_event_bus().get_stats()
        get_task_delegation_manager().get_stats()
    except Exception:
        queueing_ready = False

    try:
        from tools.scheduled_tasks import get_scheduled_task_scheduler

        await get_scheduled_task_scheduler().list_tasks()
    except Exception:
        scheduled_ready = False

    try:
        from tools.code_executor import get_executor_capabilities

        get_executor_capabilities()
    except Exception:
        sandbox_ready = False

    telemetry_ready = flags.get("runtime_telemetry", False) and flags.get("provider_registry", False)
    rollout_ready = queueing_ready and scheduled_ready and sandbox_ready and telemetry_ready

    return {
        "status": "ok" if rollout_ready else "degraded",
        "agents": len(MODELS),
        "pipelines": len(PipelineType),
        "runtime_schema_version": RUNTIME_EVENT_SCHEMA_VERSION,
        "feature_flags": flags,
        "queueing_ready": queueing_ready,
        "scheduled_tasks_ready": scheduled_ready,
        "sandbox_ready": sandbox_ready,
        "rollout_ready": rollout_ready,
        "telemetry_ready": telemetry_ready,
    }
