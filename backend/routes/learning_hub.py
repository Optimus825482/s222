"""Learning Hub — Unified API for all adaptive learning mechanisms."""

import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["learning-hub"])


# ── Lazy singletons (tolerate missing modules) ──────────────────

def _get_auto_optimizer():
    try:
        from tools.auto_optimizer import get_auto_optimizer
        return get_auto_optimizer()
    except Exception:
        return None


def _get_error_analyzer():
    try:
        from tools.error_patterns import get_error_analyzer
        return get_error_analyzer()
    except Exception:
        return None


def _get_tool_selector():
    try:
        from tools.adaptive_tool_selector import get_adaptive_tool_selector
        return get_adaptive_tool_selector()
    except Exception:
        return None


def _get_workflow_optimizer():
    try:
        from tools.workflow_optimizer import get_workflow_optimizer
        return get_workflow_optimizer()
    except Exception:
        return None


def _get_benchmark_runner():
    try:
        from tools.benchmark_suite import BenchmarkRunner
        return BenchmarkRunner()
    except Exception:
        return None


# ── Helpers ──────────────────────────────────────────────────────

def _normalize_recommendation(r: dict, idx: int = 0) -> dict:
    """Normalize optimizer recommendation to frontend Recommendation shape."""
    return {
        "id": r.get("id", idx),
        "type": r.get("type", r.get("check_type", "reliability")),
        "title": r.get("title", r.get("description", "Öneri")[:60]),
        "description": r.get("description", r.get("message", "")),
        "affected_agents": r.get("affected_agents", []),
        "confidence": r.get("confidence", r.get("priority_score", 0.5)),
        "status": r.get("status", "pending"),
        "created_at": r.get("created_at", datetime.now(timezone.utc).isoformat()),
    }


def _normalize_error_pattern(p: dict, idx: int = 0) -> dict:
    """Normalize error pattern to frontend ErrorPattern shape."""
    return {
        "id": str(p.get("id", p.get("pattern_id", idx))),
        "pattern": p.get("pattern", p.get("description", p.get("error_type", "Unknown"))),
        "count": p.get("count", p.get("occurrence_count", 1)),
        "severity": p.get("severity", "medium"),
        "first_seen": p.get("first_seen", p.get("detected_at", "")),
        "last_seen": p.get("last_seen", p.get("last_occurrence", "")),
        "status": p.get("status", "active"),
    }


def _normalize_teaching(t: dict) -> dict:
    """Normalize teaching to frontend Teaching shape."""
    return {
        "id": t.get("id", 0),
        "category": t.get("category", "general"),
        "instruction": t.get("instruction", t.get("content", "")),
        "trigger_text": t.get("trigger_text", t.get("trigger", "")),
        "use_count": t.get("use_count", t.get("times_used", 0)),
        "active": t.get("active", True) if isinstance(t.get("active"), bool) else bool(t.get("active", 1)),
        "created_at": t.get("created_at", ""),
    }


# ── Request Models ───────────────────────────────────────────────

class TeachingCreate(BaseModel):
    instruction: str
    trigger_text: str = ""
    category: str = "general"
    context: str | None = None


# ── 1. Unified Dashboard ────────────────────────────────────────
# Frontend expects: LearningDashboard interface


@router.get("/api/learning-hub/dashboard")
async def learning_hub_dashboard(user: dict = Depends(get_current_user)):
    """Unified dashboard — returns shape matching frontend LearningDashboard."""
    _audit("learning_hub_dashboard", user["user_id"])

    # Teachability
    raw_teachings: list[dict] = []
    try:
        from tools.teachability import get_all_teachings
        raw_teachings = get_all_teachings()
    except Exception as e:
        logger.warning("Dashboard: teachability failed: %s", e)

    teachings = [_normalize_teaching(t) for t in raw_teachings]
    active_teachings = [t for t in teachings if t["active"]]
    top_used = sorted(active_teachings, key=lambda x: x["use_count"], reverse=True)[:5]

    # AutoOptimizer
    optimizer_recs: list[dict] = []
    optimizer_stats: dict[str, Any] = {}
    try:
        opt = _get_auto_optimizer()
        if opt:
            optimizer_recs = opt.get_recommendations()
            optimizer_stats = opt.get_optimization_stats()
    except Exception as e:
        logger.warning("Dashboard: auto_optimizer failed: %s", e)

    normalized_recs = [_normalize_recommendation(r, i) for i, r in enumerate(optimizer_recs)]
    pending_recs = [r for r in normalized_recs if r["status"] == "pending"]
    applied_count = sum(1 for r in normalized_recs if r["status"] == "applied")
    dismissed_count = sum(1 for r in normalized_recs if r["status"] == "dismissed")

    # Error patterns
    raw_patterns: list[dict] = []
    try:
        ea = _get_error_analyzer()
        if ea:
            raw_patterns = ea.get_patterns()
    except Exception as e:
        logger.warning("Dashboard: error_patterns failed: %s", e)

    patterns = [_normalize_error_pattern(p, i) for i, p in enumerate(raw_patterns)]
    active_patterns = [p for p in patterns if p["status"] == "active"]
    critical_patterns = [p for p in active_patterns if p["severity"] == "critical"]

    # Tool selector stats
    tool_stats: dict[str, Any] = {}
    try:
        ts = _get_tool_selector()
        if ts:
            tool_stats = ts.get_statistics()
    except Exception as e:
        logger.warning("Dashboard: adaptive_tool_selector failed: %s", e)

    # Workflow optimizer stats
    workflow_stats: dict[str, Any] = {}
    try:
        wo = _get_workflow_optimizer()
        if wo:
            workflow_stats = wo.get_statistics()
    except Exception as e:
        logger.warning("Dashboard: workflow_optimizer failed: %s", e)

    # Benchmark leaderboard
    leaderboard: list[dict] = []
    try:
        br = _get_benchmark_runner()
        if br:
            raw_lb = br.get_leaderboard()
            leaderboard = [
                {
                    "agent_role": e.get("agent_role", "?"),
                    "avg_score": e.get("avg_score", e.get("score", 0)),
                    "total_runs": e.get("total_runs", e.get("runs", 0)),
                }
                for e in raw_lb
            ]
    except Exception as e:
        logger.warning("Dashboard: benchmark_suite failed: %s", e)

    health_avg = optimizer_stats.get("health_score", optimizer_stats.get("avg_health", 0))

    # User behavior stats from PostgreSQL
    behavior_stats: dict[str, Any] = {
        "total_events": 0,
        "by_action": [],
        "recent_actions": [],
        "insights": [],
    }
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                # Total events
                cur.execute(
                    "SELECT COUNT(*) as total FROM user_behavior WHERE user_id = %s",
                    (user["user_id"],),
                )
                row = cur.fetchone()
                behavior_stats["total_events"] = row["total"] if row else 0

                # By action breakdown
                cur.execute(
                    """SELECT action, COUNT(*) as cnt
                       FROM user_behavior WHERE user_id = %s
                       GROUP BY action ORDER BY cnt DESC""",
                    (user["user_id"],),
                )
                behavior_stats["by_action"] = [
                    {"action": r["action"], "count": r["cnt"]} for r in cur.fetchall()
                ]

                # Recent 10 actions
                cur.execute(
                    """SELECT action, context, metadata, timestamp
                       FROM user_behavior WHERE user_id = %s
                       ORDER BY timestamp DESC LIMIT 10""",
                    (user["user_id"],),
                )
                behavior_stats["recent_actions"] = [
                    {
                        "action": r["action"],
                        "context": (r["context"] or "")[:100],
                        "metadata": json.loads(r["metadata"]) if r["metadata"] and isinstance(r["metadata"], str) else (r["metadata"] or {}),
                        "timestamp": r["timestamp"] if isinstance(r["timestamp"], str) else str(r["timestamp"]),
                    }
                    for r in cur.fetchall()
                ]

                # Insights: pipeline preference
                cur.execute(
                    """SELECT metadata::text as meta_text FROM user_behavior
                       WHERE user_id = %s AND action = 'task_submit'
                       ORDER BY timestamp DESC LIMIT 50""",
                    (user["user_id"],),
                )
                pipeline_counts: dict[str, int] = {}
                for r in cur.fetchall():
                    try:
                        raw_meta = r["meta_text"]
                        meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
                        p = meta.get("pipeline", "unknown")
                        pipeline_counts[p] = pipeline_counts.get(p, 0) + 1
                    except Exception:
                        pass
                if pipeline_counts:
                    fav = max(pipeline_counts, key=pipeline_counts.get)  # type: ignore[arg-type]
                    behavior_stats["insights"].append({
                        "type": "pipeline_preference",
                        "label": f"En çok kullanılan pipeline: {fav}",
                        "data": pipeline_counts,
                    })

                # Insights: avg tokens per completed task (from agent side)
                cur.execute(
                    """SELECT metadata::text as meta_text FROM user_behavior
                       WHERE user_id = %s AND action = 'agent_task_complete'
                       ORDER BY timestamp DESC LIMIT 50""",
                    (user["user_id"],),
                )
                token_vals: list[int] = []
                cost_vals: list[float] = []
                agent_counts: dict[str, int] = {}
                for r in cur.fetchall():
                    try:
                        raw_meta = r["meta_text"]
                        meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
                        if meta.get("tokens"):
                            token_vals.append(int(meta["tokens"]))
                        if meta.get("cost_usd"):
                            cost_vals.append(float(meta["cost_usd"]))
                        ag = meta.get("agent", "unknown")
                        agent_counts[ag] = agent_counts.get(ag, 0) + 1
                    except Exception:
                        pass
                if token_vals:
                    avg_tok = sum(token_vals) // len(token_vals)
                    behavior_stats["insights"].append({
                        "type": "avg_tokens",
                        "label": f"Ortalama token/görev: {avg_tok:,}",
                        "data": {"avg": avg_tok, "min": min(token_vals), "max": max(token_vals)},
                    })
                if cost_vals:
                    total_cost = sum(cost_vals)
                    behavior_stats["insights"].append({
                        "type": "total_cost",
                        "label": f"Toplam maliyet: ${total_cost:.4f}",
                        "data": {"total": round(total_cost, 6), "avg": round(total_cost / len(cost_vals), 6)},
                    })
                if agent_counts:
                    behavior_stats["insights"].append({
                        "type": "agent_usage",
                        "label": "Agent kullanım dağılımı",
                        "data": agent_counts,
                    })

                # Insights: hourly activity pattern
                cur.execute(
                    """SELECT EXTRACT(HOUR FROM timestamp::timestamp) as hr, COUNT(*) as cnt
                       FROM user_behavior WHERE user_id = %s
                       GROUP BY hr ORDER BY hr""",
                    (user["user_id"],),
                )
                hourly = {int(r["hr"]): r["cnt"] for r in cur.fetchall()}
                if hourly:
                    peak_hr = max(hourly, key=hourly.get)  # type: ignore[arg-type]
                    behavior_stats["insights"].append({
                        "type": "peak_hours",
                        "label": f"En aktif saat: {peak_hr:02d}:00",
                        "data": hourly,
                    })
        finally:
            release_conn(conn)
    except Exception as e:
        logger.warning("Dashboard: user_behavior failed: %s", e)

    return {
        "teachings": {
            "total": len(teachings),
            "active": len(active_teachings),
            "top_used": top_used,
        },
        "recommendations": {
            "pending": pending_recs[:20],
            "applied": applied_count,
            "dismissed": dismissed_count,
            "total": len(normalized_recs),
        },
        "error_patterns": {
            "active": len(active_patterns),
            "critical": len(critical_patterns),
            "patterns": patterns[:20],
        },
        "optimizer_stats": {
            "total_recommendations": len(normalized_recs),
            "health_avg": health_avg,
        },
        "tool_stats": {
            "total_analyses": tool_stats.get("total_analyses", tool_stats.get("total_selections", 0)),
        },
        "workflow_stats": {
            "total_executions": workflow_stats.get("total_executions", workflow_stats.get("total_workflows", 0)),
        },
        "benchmark": {"leaderboard": leaderboard},
        "user_behavior": behavior_stats,
    }


# ── 2. Trigger Analysis ─────────────────────────────────────────
# Frontend expects: AnalysisResult { new_recommendations, new_patterns, new_suggestions, details }


@router.post("/api/learning-hub/trigger-analysis")
async def trigger_analysis(user: dict = Depends(get_current_user)):
    """Manually trigger the full analysis cycle."""
    _audit("learning_hub_trigger_analysis", user["user_id"])

    new_recommendations = 0
    new_patterns = 0
    new_suggestions = 0
    details: dict[str, Any] = {}

    try:
        opt = _get_auto_optimizer()
        if opt:
            recs = opt.analyze_and_recommend()
            new_recommendations = len(recs) if isinstance(recs, list) else 0
            details["optimizer"] = {"count": new_recommendations}
    except Exception as e:
        logger.warning("Trigger analysis: auto_optimizer failed: %s", e)
        details["optimizer"] = {"error": str(e)}

    try:
        ea = _get_error_analyzer()
        if ea:
            pats = ea.detect_patterns()
            new_patterns = len(pats) if isinstance(pats, list) else 0
            details["error_patterns"] = {"count": new_patterns}
    except Exception as e:
        logger.warning("Trigger analysis: error_patterns failed: %s", e)
        details["error_patterns"] = {"error": str(e)}

    try:
        wo = _get_workflow_optimizer()
        if wo:
            sugs = wo.generate_suggestions()
            new_suggestions = len(sugs) if isinstance(sugs, list) else 0
            details["workflow"] = {"count": new_suggestions}
    except Exception as e:
        logger.warning("Trigger analysis: workflow_optimizer failed: %s", e)
        details["workflow"] = {"error": str(e)}

    return {
        "new_recommendations": new_recommendations,
        "new_patterns": new_patterns,
        "new_suggestions": new_suggestions,
        "details": details,
    }


# ── 3. Agent Profile ────────────────────────────────────────────
# Frontend expects: AgentProfile { agent_role, health_score, eval_stats, error_stats, benchmark_stats, pending_recommendations, recommendations }


@router.get("/api/learning-hub/agent-profile/{agent_role}")
async def agent_learning_profile(agent_role: str, user: dict = Depends(get_current_user)):
    """Unified learning profile for a specific agent."""
    _audit("learning_hub_agent_profile", user["user_id"], detail=agent_role)

    health_score = 0
    eval_stats: dict[str, int] = {}
    error_stats: dict[str, int] = {}
    benchmark_stats: dict[str, int] = {}
    recommendations: list[dict] = []

    # AutoOptimizer profile
    try:
        opt = _get_auto_optimizer()
        if opt:
            profile = opt.get_agent_optimization_profile(agent_role)
            health_score = profile.get("health_score", profile.get("score", 0))
            eval_stats = {
                "total_evaluations": profile.get("total_evaluations", profile.get("eval_count", 0)),
                "avg_score": profile.get("avg_score", 0),
                "success_rate": profile.get("success_rate", 0),
            }
            recs = opt.get_recommendations()
            agent_recs = [
                _normalize_recommendation(r, i)
                for i, r in enumerate(recs)
                if agent_role in r.get("affected_agents", [])
                or r.get("agent_role") == agent_role
            ]
            recommendations = agent_recs
    except Exception as e:
        logger.warning("Agent profile: auto_optimizer failed: %s", e)

    # Error patterns for this agent
    try:
        ea = _get_error_analyzer()
        if ea:
            agent_errors = ea.get_patterns(agent_role=agent_role) if hasattr(ea.get_patterns, '__code__') and 'agent_role' in ea.get_patterns.__code__.co_varnames else ea.get_patterns()
            agent_error_list = [p for p in agent_errors if p.get("agent_role") == agent_role] if not hasattr(ea.get_patterns, '__code__') or 'agent_role' not in ea.get_patterns.__code__.co_varnames else agent_errors
            error_stats = {
                "total_errors": len(agent_error_list),
                "critical": sum(1 for p in agent_error_list if p.get("severity") == "critical"),
                "active": sum(1 for p in agent_error_list if p.get("status") == "active"),
            }
    except Exception as e:
        logger.warning("Agent profile: error_patterns failed: %s", e)

    # Benchmark stats
    try:
        br = _get_benchmark_runner()
        if br:
            lb = br.get_leaderboard()
            for entry in lb:
                if entry.get("agent_role") == agent_role:
                    benchmark_stats = {
                        "avg_score": entry.get("avg_score", entry.get("score", 0)),
                        "total_runs": entry.get("total_runs", entry.get("runs", 0)),
                        "rank": lb.index(entry) + 1,
                    }
                    break
    except Exception as e:
        logger.warning("Agent profile: benchmark failed: %s", e)

    pending_recs = [r for r in recommendations if r.get("status") == "pending"]

    return {
        "agent_role": agent_role,
        "health_score": health_score,
        "eval_stats": eval_stats,
        "error_stats": error_stats,
        "benchmark_stats": benchmark_stats,
        "pending_recommendations": len(pending_recs),
        "recommendations": pending_recs[:10],
    }


# ── 4 & 5. Apply / Dismiss Recommendation ───────────────────────
# Frontend calls: POST /api/learning-hub/recommendations/{id}/apply
# Frontend calls: POST /api/learning-hub/recommendations/{id}/dismiss


@router.post("/api/learning-hub/recommendations/{rec_id}/apply")
async def apply_recommendation(rec_id: int, user: dict = Depends(get_current_user)):
    """Apply a pending optimization recommendation."""
    _audit("learning_hub_apply_rec", user["user_id"], detail=str(rec_id))
    opt = _get_auto_optimizer()
    if not opt:
        raise HTTPException(status_code=503, detail="Auto optimizer not available")
    result = opt.apply_recommendation(rec_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/api/learning-hub/recommendations/{rec_id}/dismiss")
async def dismiss_recommendation(rec_id: int, user: dict = Depends(get_current_user)):
    """Dismiss a pending optimization recommendation."""
    _audit("learning_hub_dismiss_rec", user["user_id"], detail=str(rec_id))
    opt = _get_auto_optimizer()
    if not opt:
        raise HTTPException(status_code=503, detail="Auto optimizer not available")
    result = opt.dismiss_recommendation(rec_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── 6, 7, 8. Teachings CRUD ─────────────────────────────────────
# Frontend expects: GET /teachings → Teaching[] (array directly)
# Frontend expects: POST /teachings → Teaching
# Frontend expects: POST /teachings/{id}/deactivate


@router.get("/api/learning-hub/teachings")
async def list_teachings(user: dict = Depends(get_current_user)):
    """List all active teachings — returns flat array for frontend."""
    _audit("learning_hub_teachings_list", user["user_id"])
    try:
        from tools.teachability import get_all_teachings
        raw = get_all_teachings(active_only=True)
        return [_normalize_teaching(t) for t in raw]
    except Exception as e:
        logger.error("List teachings failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list teachings: {e}")


@router.post("/api/learning-hub/teachings")
async def create_teaching(body: TeachingCreate, user: dict = Depends(get_current_user)):
    """Save a new teaching manually — returns Teaching shape."""
    _audit("learning_hub_teaching_create", user["user_id"], detail=body.instruction[:80])
    try:
        from tools.teachability import save_teaching
        result = save_teaching(
            instruction=body.instruction,
            trigger_text=body.trigger_text,
            category=body.category,
            context=body.context,
        )
        return _normalize_teaching(result) if isinstance(result, dict) else result
    except Exception as e:
        logger.error("Create teaching failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save teaching: {e}")


@router.post("/api/learning-hub/teachings/{teaching_id}/deactivate")
async def deactivate_teaching(teaching_id: int, user: dict = Depends(get_current_user)):
    """Deactivate (soft-delete) a teaching — POST for frontend compatibility."""
    _audit("learning_hub_teaching_deactivate", user["user_id"], detail=str(teaching_id))
    try:
        from tools.teachability import deactivate_teaching as _deactivate
        success = _deactivate(teaching_id)
        if not success:
            raise HTTPException(status_code=404, detail="Teaching not found")
        return {"deactivated": True, "teaching_id": teaching_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Deactivate teaching failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to deactivate teaching: {e}")


# ── 9. Error Pattern Resolve ────────────────────────────────────
# Frontend calls: POST /api/learning-hub/error-patterns/{id}/resolve


@router.post("/api/learning-hub/error-patterns/{pattern_id}/resolve")
async def resolve_error_pattern(pattern_id: str, user: dict = Depends(get_current_user)):
    """Mark an error pattern as resolved."""
    _audit("learning_hub_resolve_pattern", user["user_id"], detail=pattern_id)
    ea = _get_error_analyzer()
    if not ea:
        raise HTTPException(status_code=503, detail="Error analyzer not available")
    try:
        if hasattr(ea, "resolve_pattern"):
            result = ea.resolve_pattern(pattern_id)
        elif hasattr(ea, "update_pattern_status"):
            result = ea.update_pattern_status(pattern_id, "resolved")
        else:
            raise HTTPException(status_code=501, detail="Resolve not supported")
        return {"resolved": True, "pattern_id": pattern_id, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Resolve pattern failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to resolve pattern: {e}")


# ── 10. Unified Timeline ────────────────────────────────────────
# Frontend expects: TimelineEvent[] { id, type, description, timestamp, source }


@router.get("/api/learning-hub/timeline")
async def learning_timeline(hours: int = 24, user: dict = Depends(get_current_user)):
    """Unified timeline — returns flat array of TimelineEvent."""
    _audit("learning_hub_timeline", user["user_id"])
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    events: list[dict[str, Any]] = []
    counter = 0

    def _make_id():
        nonlocal counter
        counter += 1
        return f"evt-{counter}"

    def _parse_ts(raw: str) -> datetime | None:
        if not raw:
            return None
        try:
            ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts if ts >= cutoff else None
        except (ValueError, TypeError):
            return None

    # Recent teachings
    try:
        from tools.teachability import get_all_teachings
        for t in get_all_teachings():
            ts = _parse_ts(t.get("created_at", ""))
            if ts:
                events.append({
                    "id": _make_id(),
                    "type": "teaching",
                    "description": t.get("instruction", t.get("content", ""))[:120],
                    "timestamp": ts.isoformat(),
                    "source": "teachability",
                })
    except Exception as e:
        logger.warning("Timeline: teachability failed: %s", e)

    # Recent optimizer recommendations
    try:
        opt = _get_auto_optimizer()
        if opt:
            for r in opt.get_recommendations():
                ts = _parse_ts(r.get("created_at", ""))
                if ts:
                    events.append({
                        "id": _make_id(),
                        "type": "recommendation",
                        "description": r.get("title", r.get("description", ""))[:120],
                        "timestamp": ts.isoformat(),
                        "source": "auto_optimizer",
                    })
    except Exception as e:
        logger.warning("Timeline: auto_optimizer failed: %s", e)

    # Recent error patterns
    try:
        ea = _get_error_analyzer()
        if ea:
            for p in ea.get_patterns():
                ts = _parse_ts(p.get("first_seen", p.get("detected_at", "")))
                if ts:
                    events.append({
                        "id": _make_id(),
                        "type": "error_pattern",
                        "description": p.get("pattern", p.get("description", ""))[:120],
                        "timestamp": ts.isoformat(),
                        "source": "error_patterns",
                    })
    except Exception as e:
        logger.warning("Timeline: error_patterns failed: %s", e)

    # Recent benchmark results
    try:
        br = _get_benchmark_runner()
        if br:
            results = br.get_results(limit=20) if hasattr(br, "get_results") else []
            for r in results:
                ts = _parse_ts(r.get("ran_at", r.get("timestamp", "")))
                if ts:
                    events.append({
                        "id": _make_id(),
                        "type": "analysis",
                        "description": f"{r.get('agent_role', '?')} benchmark: {r.get('score', 0)}/100",
                        "timestamp": ts.isoformat(),
                        "source": "benchmark_suite",
                    })
    except Exception as e:
        logger.warning("Timeline: benchmark_suite failed: %s", e)

    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events


# ── 11. User Behavior Insights for Learning ─────────────────────


@router.get("/api/learning-hub/behavior-insights")
async def behavior_insights(hours: int = 168, user: dict = Depends(get_current_user)):
    """Deep behavior insights for agent self-improvement learning."""
    _audit("learning_hub_behavior_insights", user["user_id"])
    uid = user["user_id"]

    result: dict[str, Any] = {
        "action_flow": [],
        "pipeline_effectiveness": [],
        "agent_performance": [],
        "time_patterns": [],
        "learning_signals": [],
    }

    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

                # Action flow: what users do in sequence
                cur.execute(
                    """SELECT action, context, metadata::text, timestamp
                       FROM user_behavior WHERE user_id = %s AND timestamp >= %s
                       ORDER BY timestamp DESC LIMIT 200""",
                    (uid, cutoff),
                )
                rows = cur.fetchall()
                result["action_flow"] = [
                    {
                        "action": r["action"],
                        "context": (r["context"] or "")[:120],
                        "metadata": json.loads(r["metadata"]) if r["metadata"] and isinstance(r["metadata"], str) else (r["metadata"] or {}),
                        "timestamp": r["timestamp"] if isinstance(r["timestamp"], str) else str(r["timestamp"]),
                    }
                    for r in rows
                ]

                # Pipeline effectiveness: completion rate + avg tokens per pipeline
                cur.execute(
                    """SELECT metadata::text as meta_text FROM user_behavior
                       WHERE user_id = %s AND action IN ('task_submit', 'task_complete', 'agent_task_complete')
                       AND timestamp >= %s""",
                    (uid, cutoff),
                )
                pipe_submit: dict[str, int] = {}
                pipe_complete: dict[str, int] = {}
                pipe_tokens: dict[str, list[int]] = {}
                pipe_latency: dict[str, list[float]] = {}
                for r in cur.fetchall():
                    raw_meta = r["meta_text"]
                    try:
                        meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
                        p = meta.get("pipeline", "unknown")
                        if meta.get("tokens"):
                            pipe_complete[p] = pipe_complete.get(p, 0) + 1
                            pipe_tokens.setdefault(p, []).append(int(meta["tokens"]))
                        if meta.get("latency_ms"):
                            pipe_latency.setdefault(p, []).append(float(meta["latency_ms"]))
                        if not meta.get("tokens") and not meta.get("cost_usd"):
                            pipe_submit[p] = pipe_submit.get(p, 0) + 1
                    except Exception:
                        pass

                all_pipes = set(list(pipe_submit.keys()) + list(pipe_complete.keys()))
                for p in all_pipes:
                    sub = pipe_submit.get(p, 0)
                    comp = pipe_complete.get(p, 0)
                    toks = pipe_tokens.get(p, [])
                    lats = pipe_latency.get(p, [])
                    result["pipeline_effectiveness"].append({
                        "pipeline": p,
                        "submitted": sub,
                        "completed": comp,
                        "completion_rate": round(100 * comp / max(sub, 1), 1),
                        "avg_tokens": sum(toks) // max(len(toks), 1) if toks else 0,
                        "avg_latency_ms": round(sum(lats) / max(len(lats), 1), 1) if lats else 0,
                    })

                # Agent performance from behavior data
                cur.execute(
                    """SELECT metadata::text as meta_text FROM user_behavior
                       WHERE user_id = %s AND action = 'agent_task_complete'
                       AND timestamp >= %s""",
                    (uid, cutoff),
                )
                agent_data: dict[str, dict[str, Any]] = {}
                for r in cur.fetchall():
                    raw_meta = r["meta_text"]
                    try:
                        meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
                        ag = meta.get("agent", "unknown")
                        if ag not in agent_data:
                            agent_data[ag] = {"tasks": 0, "tokens": [], "costs": [], "steps": []}
                        agent_data[ag]["tasks"] += 1
                        if meta.get("tokens"):
                            agent_data[ag]["tokens"].append(int(meta["tokens"]))
                        if meta.get("cost_usd"):
                            agent_data[ag]["costs"].append(float(meta["cost_usd"]))
                        if meta.get("steps"):
                            agent_data[ag]["steps"].append(int(meta["steps"]))
                    except Exception:
                        pass

                for ag, d in agent_data.items():
                    result["agent_performance"].append({
                        "agent": ag,
                        "tasks": d["tasks"],
                        "avg_tokens": sum(d["tokens"]) // max(len(d["tokens"]), 1) if d["tokens"] else 0,
                        "total_cost": round(sum(d["costs"]), 6),
                        "avg_steps": round(sum(d["steps"]) / max(len(d["steps"]), 1), 1) if d["steps"] else 0,
                    })

                # Time patterns: daily activity
                cur.execute(
                    """SELECT DATE(timestamp::timestamp) as day, COUNT(*) as cnt
                       FROM user_behavior WHERE user_id = %s AND timestamp >= %s
                       GROUP BY day ORDER BY day""",
                    (uid, cutoff),
                )
                result["time_patterns"] = [
                    {"date": str(r["day"]), "count": r["cnt"]} for r in cur.fetchall()
                ]

                # Learning signals: patterns that agents should learn from
                # e.g. user frequently changes pipeline → auto pipeline not working well
                cur.execute(
                    """SELECT COUNT(*) as cnt FROM user_behavior
                       WHERE user_id = %s AND action = 'pipeline_change'
                       AND timestamp >= %s""",
                    (uid, cutoff),
                )
                pipe_changes = (cur.fetchone() or {}).get("cnt", 0) or 0
                cur.execute(
                    """SELECT COUNT(*) as cnt FROM user_behavior
                       WHERE user_id = %s AND action = 'task_submit'
                       AND timestamp >= %s""",
                    (uid, cutoff),
                )
                task_submits = (cur.fetchone() or {}).get("cnt", 0) or 0

                if task_submits > 0 and pipe_changes > task_submits * 0.3:
                    result["learning_signals"].append({
                        "signal": "high_pipeline_change_rate",
                        "severity": "medium",
                        "message": f"Kullanıcı görevlerin %{round(100*pipe_changes/task_submits)}inde pipeline değiştiriyor — auto routing iyileştirilmeli",
                        "data": {"changes": pipe_changes, "submits": task_submits},
                    })

                # Signal: report downloads → user values exportable results
                cur.execute(
                    """SELECT COUNT(*) as cnt FROM user_behavior
                       WHERE user_id = %s AND action = 'report_download'
                       AND timestamp >= %s""",
                    (uid, cutoff),
                )
                downloads = (cur.fetchone() or {}).get("cnt", 0) or 0
                if downloads > 3:
                    result["learning_signals"].append({
                        "signal": "frequent_report_downloads",
                        "severity": "info",
                        "message": f"Kullanıcı {downloads} rapor indirdi — sonuç kalitesi önemli",
                        "data": {"downloads": downloads},
                    })

                # Signal: thread deletions → user not satisfied
                cur.execute(
                    """SELECT COUNT(*) as cnt FROM user_behavior
                       WHERE user_id = %s AND action = 'thread_delete'
                       AND timestamp >= %s""",
                    (uid, cutoff),
                )
                deletions = (cur.fetchone() or {}).get("cnt", 0) or 0
                if task_submits > 0 and deletions > task_submits * 0.2:
                    result["learning_signals"].append({
                        "signal": "high_deletion_rate",
                        "severity": "high",
                        "message": f"Kullanıcı görevlerin %{round(100*deletions/task_submits)}ini siliyor — sonuç kalitesi düşük olabilir",
                        "data": {"deletions": deletions, "submits": task_submits},
                    })

        finally:
            release_conn(conn)
    except Exception as e:
        logger.warning("Behavior insights failed: %s", e)

    return result
