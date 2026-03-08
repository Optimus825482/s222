"""Monitoring, benchmarking, error analysis, cost tracking, and optimizer endpoints."""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from shared_state import _AGENT_ROLES, _utcnow


router = APIRouter()


# ── 8. Tool Usage Analytics — PostgreSQL Persistence ─────────────


@router.post("/api/analytics/tool-usage")
async def record_tool_usage(
    tool_name: str,
    agent_role: str,
    latency_ms: float = 0,
    success: bool = True,
    tokens_used: int = 0,
    user: dict = Depends(get_current_user),
):
    """Record a tool usage event for analytics."""
    from tools.pg_connection import get_conn, release_conn

    uid = user["user_id"]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tool_usage
                   (tool_name, agent_role, latency_ms, success, tokens_used, user_id, timestamp)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    tool_name,
                    agent_role,
                    latency_ms,
                    1 if success else 0,
                    tokens_used,
                    uid,
                    _utcnow().isoformat(),
                ),
            )
        conn.commit()
    finally:
        release_conn(conn)
    return {"recorded": True}


@router.get("/api/analytics/tool-usage")
async def get_tool_usage_analytics(
    limit: int = 100,
    agent_role: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get tool usage analytics with aggregation."""
    from tools.pg_connection import get_conn, release_conn

    _audit("tool_analytics_view", user["user_id"])
    uid = user["user_id"]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Aggregate by tool
            if agent_role:
                cur.execute(
                    """SELECT tool_name, COUNT(*) as count,
                              SUM(success) as success_count,
                              SUM(latency_ms) as total_latency_ms,
                              SUM(tokens_used) as total_tokens,
                              STRING_AGG(DISTINCT agent_role, ',') as agents
                       FROM tool_usage WHERE user_id = %s AND agent_role = %s
                       GROUP BY tool_name ORDER BY count DESC LIMIT %s""",
                    (uid, agent_role, limit),
                )
            else:
                cur.execute(
                    """SELECT tool_name, COUNT(*) as count,
                              SUM(success) as success_count,
                              SUM(latency_ms) as total_latency_ms,
                              SUM(tokens_used) as total_tokens,
                              STRING_AGG(DISTINCT agent_role, ',') as agents
                       FROM tool_usage WHERE user_id = %s
                       GROUP BY tool_name ORDER BY count DESC LIMIT %s""",
                    (uid, limit),
                )
            tool_rows = cur.fetchall()

            tool_stats = []
            for row in tool_rows:
                count = row[1]
                tool_stats.append(
                    {
                        "tool_name": row[0],
                        "count": count,
                        "success_rate": round(row[2] / max(count, 1) * 100, 1),
                        "avg_latency_ms": round(row[3] / max(count, 1), 1),
                        "total_tokens": row[4],
                        "agents": row[5].split(",") if row[5] else [],
                    }
                )

            # Aggregate by agent
            cur.execute(
                """SELECT agent_role, COUNT(*) as tool_calls,
                          SUM(success) as success_count,
                          SUM(latency_ms) as total_latency_ms,
                          SUM(tokens_used) as total_tokens,
                          STRING_AGG(DISTINCT tool_name, ',') as tools_used
                   FROM tool_usage WHERE user_id = %s
                   GROUP BY agent_role ORDER BY tool_calls DESC LIMIT %s""",
                (uid, limit),
            )
            agent_rows = cur.fetchall()

            agent_stats = []
            for row in agent_rows:
                count = row[1]
                agent_stats.append(
                    {
                        "agent_role": row[0],
                        "tool_calls": count,
                        "success_rate": round(row[2] / max(count, 1) * 100, 1),
                        "avg_latency_ms": round(row[3] / max(count, 1), 1),
                        "total_tokens": row[4],
                        "tools_used": row[5].split(",") if row[5] else [],
                    }
                )

            # Recent entries
            cur.execute(
                """SELECT * FROM tool_usage WHERE user_id = %s
                   ORDER BY timestamp DESC LIMIT %s""",
                (uid, limit),
            )
            recent_rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]
            recent = [dict(zip(col_names, row)) for row in recent_rows]

            # Total count
            cur.execute("SELECT COUNT(*) FROM tool_usage WHERE user_id = %s", (uid,))
            total = cur.fetchone()[0]

    finally:
        release_conn(conn)

    return {
        "total_events": total,
        "by_tool": tool_stats,
        "by_agent": agent_stats,
        "recent": recent,
        "timestamp": _utcnow().isoformat(),
    }


# ── 9. User Behavior Tracking — PostgreSQL Persistence ───────────


@router.post("/api/analytics/user-behavior")
async def record_user_behavior(
    action: str,
    context: str = "",
    metadata: dict | None = None,
    user: dict = Depends(get_current_user),
):
    """Record user behavior event."""
    from tools.pg_connection import get_conn, release_conn

    uid = user["user_id"]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO user_behavior
                   (action, context, metadata, user_id, timestamp)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    action,
                    context,
                    json.dumps(metadata or {}),
                    uid,
                    _utcnow().isoformat(),
                ),
            )
        conn.commit()
    finally:
        release_conn(conn)
    return {"recorded": True}


@router.get("/api/analytics/user-behavior")
async def get_user_behavior_analytics(
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    """Get user behavior analytics."""
    from tools.pg_connection import get_conn, release_conn

    _audit("user_behavior_view", user["user_id"])
    uid = user["user_id"]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Aggregate by action
            cur.execute(
                """SELECT action, COUNT(*) as count
                   FROM user_behavior WHERE user_id = %s
                   GROUP BY action ORDER BY count DESC""",
                (uid,),
            )
            action_rows = cur.fetchall()
            action_summary = [
                {"action": row[0], "count": row[1]} for row in action_rows
            ]

            # Recent entries
            cur.execute(
                """SELECT * FROM user_behavior WHERE user_id = %s
                   ORDER BY timestamp DESC LIMIT %s""",
                (uid, limit),
            )
            recent_rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]
            recent = [dict(zip(col_names, row)) for row in recent_rows]

            # Total count (RealDictCursor returns dict)
            cur.execute(
                "SELECT COUNT(*) AS total FROM user_behavior WHERE user_id = %s", (uid,)
            )
            row = cur.fetchone()
            total = (row.get("total", row.get("count", 0)) or 0) if row else 0

    finally:
        release_conn(conn)

    return {
        "total_events": total,
        "by_action": action_summary,
        "recent": recent,
        "timestamp": _utcnow().isoformat(),
    }


# ── 11. Performance Benchmarking Suite ───────────────────────────

try:
    from tools.benchmark_suite import (
        BenchmarkRunner,
        get_scenarios,
        BENCHMARK_SCENARIOS,
    )

    _bench_runner = BenchmarkRunner()
    print("[Backend] benchmark_suite loaded OK (monitoring)")
except Exception as _e:
    print(f"[Backend] WARNING: benchmark_suite import failed: {_e}")
    _bench_runner = None
    BENCHMARK_SCENARIOS = {}

    def get_scenarios(cat=None):
        return []


class BenchmarkRunRequest(BaseModel):
    agent_role: str | None = None
    scenario_id: str | None = None
    category: str | None = None


@router.get("/api/benchmarks/scenarios")
async def list_benchmark_scenarios(
    category: str | None = None,
    user: dict = Depends(get_current_user),
):
    """List available benchmark scenarios."""
    scenarios = get_scenarios(category)
    return {"scenarios": scenarios, "total": len(scenarios)}


def _require_bench_runner():
    if _bench_runner is None:
        raise HTTPException(
            status_code=503,
            detail="Benchmark modülü yüklenemedi. Logları kontrol edin.",
        )


@router.get("/api/benchmarks/leaderboard")
async def benchmark_leaderboard(user: dict = Depends(get_current_user)):
    """Get agent leaderboard based on benchmark scores."""
    _require_bench_runner()
    lb = _bench_runner.get_leaderboard()
    return {"leaderboard": lb}


@router.get("/api/benchmarks/results")
async def benchmark_results(
    agent_role: str | None = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Get benchmark results with optional agent filter."""
    _require_bench_runner()
    results = _bench_runner.get_results(agent_role=agent_role, limit=limit)
    return {"results": results, "total": len(results)}


@router.post("/api/benchmarks/run")
async def run_benchmark(
    body: BenchmarkRunRequest, user: dict = Depends(get_current_user)
):
    """Run benchmark scenario(s) for an agent."""
    _require_bench_runner()
    _audit(
        "run_benchmark",
        user["user_id"],
        detail=f"role={body.agent_role}, scenario={body.scenario_id}, cat={body.category}",
    )
    try:
        if body.scenario_id and body.agent_role:
            result = await _bench_runner.run_single(body.agent_role, body.scenario_id)
            return {"result": result, "type": "single"}
        else:
            summary = await _bench_runner.run_suite(
                agent_role=body.agent_role,
                category=body.category,
            )
            return {"summary": summary, "type": "suite"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {e}")


@router.get("/api/benchmarks/compare")
async def compare_agents_benchmark(
    role_a: str,
    role_b: str,
    user: dict = Depends(get_current_user),
):
    """Compare two agents head-to-head on benchmark scores."""
    _require_bench_runner()
    try:
        comparison = _bench_runner.compare_agents(role_a, role_b)
        return {"comparison": comparison}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/benchmarks/history")
async def benchmark_history(
    agent_role: str,
    scenario_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get historical benchmark scores for trend analysis."""
    _require_bench_runner()
    history = _bench_runner.get_history(agent_role, scenario_id)
    return {"history": history, "agent_role": agent_role}


# ── 12. Error Pattern Analysis ───────────────────────────────────

try:
    from tools.error_patterns import get_error_analyzer

    _error_analyzer = get_error_analyzer()
    print("[Backend] error_patterns loaded OK (monitoring)")
except Exception as _e:
    print(f"[Backend] WARNING: error_patterns import failed: {_e}")
    _error_analyzer = None


class RecordErrorRequest(BaseModel):
    agent_role: str
    error_message: str
    task_type: str = "general"
    context: dict | None = None


class ResolvePatternRequest(BaseModel):
    resolution_notes: str = ""


@router.post("/api/errors/record")
async def record_error_event(
    body: RecordErrorRequest, user: dict = Depends(get_current_user)
):
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


@router.get("/api/errors/stats")
async def error_stats(
    agent_role: str | None = None,
    hours: int = 24,
    user: dict = Depends(get_current_user),
):
    """Get aggregated error statistics."""
    stats = _error_analyzer.get_error_stats(agent_role=agent_role, hours=hours)
    return {"stats": stats}


@router.get("/api/errors/timeline")
async def error_timeline(
    hours: int = 24,
    user: dict = Depends(get_current_user),
):
    """Get hourly error counts for timeline chart."""
    timeline = _error_analyzer.get_error_timeline(hours=hours)
    return {"timeline": timeline}


@router.get("/api/errors/patterns")
async def list_error_patterns(
    status: str | None = None,
    agent_role: str | None = None,
    user: dict = Depends(get_current_user),
):
    """List detected error patterns."""
    patterns = _error_analyzer.get_patterns(status=status, agent_role=agent_role)
    return {"patterns": patterns, "total": len(patterns)}


@router.post("/api/errors/detect")
async def detect_error_patterns(
    hours: int = 24,
    user: dict = Depends(get_current_user),
):
    """Run pattern detection on recent errors."""
    _audit("detect_error_patterns", user["user_id"], detail=f"hours={hours}")
    new_patterns = _error_analyzer.detect_patterns(window_hours=hours)
    return {"new_patterns": new_patterns, "total_new": len(new_patterns)}


@router.get("/api/errors/recommendations")
async def error_recommendations(user: dict = Depends(get_current_user)):
    """Get optimization recommendations based on active error patterns."""
    recs = _error_analyzer.get_recommendations()
    return {"recommendations": recs, "total": len(recs)}


@router.post("/api/errors/patterns/{pattern_id}/resolve")
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


@router.post("/api/errors/patterns/{pattern_id}/suppress")
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


# ── 13. Cost Tracking ────────────────────────────────────────────

try:
    from tools.cost_tracker import get_cost_tracker

    _cost_tracker = get_cost_tracker()
    print("[Backend] cost_tracker loaded OK (monitoring)")
except Exception as _e:
    print(f"[Backend] WARNING: cost_tracker import failed: {_e}")
    _cost_tracker = None


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


@router.post("/api/costs/record")
async def record_usage_event(
    body: RecordUsageRequest, user: dict = Depends(get_current_user)
):
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


@router.get("/api/costs/summary")
async def cost_summary(hours: int = 24, user: dict = Depends(get_current_user)):
    """Get aggregated cost summary."""
    return _cost_tracker.get_cost_summary(hours=hours)


@router.get("/api/costs/timeline")
async def cost_timeline(
    hours: int = 24, granularity: str = "hour", user: dict = Depends(get_current_user)
):
    """Get cost timeline data."""
    return {
        "timeline": _cost_tracker.get_cost_timeline(
            hours=hours, granularity=granularity
        )
    }


@router.get("/api/costs/agent/{agent_role}")
async def agent_costs(
    agent_role: str, hours: int = 24, user: dict = Depends(get_current_user)
):
    """Get detailed cost breakdown for a specific agent."""
    return _cost_tracker.get_agent_costs(agent_role=agent_role, hours=hours)


@router.get("/api/costs/top-consumers")
async def top_consumers(
    hours: int = 24, limit: int = 10, user: dict = Depends(get_current_user)
):
    """Get agents ranked by cost."""
    return {"consumers": _cost_tracker.get_top_consumers(hours=hours, limit=limit)}


@router.post("/api/costs/budget")
async def set_budget(body: SetBudgetRequest, user: dict = Depends(get_current_user)):
    """Set or update a daily budget."""
    _audit(
        "set_budget",
        user["user_id"],
        detail=f"agent={body.agent_role} limit={body.daily_limit}",
    )
    return _cost_tracker.set_budget(
        agent_role=body.agent_role,
        daily_limit=body.daily_limit,
        alert_threshold=body.alert_threshold,
    )


@router.get("/api/costs/budget")
async def check_budget(
    agent_role: str | None = None, user: dict = Depends(get_current_user)
):
    """Check budget status."""
    return _cost_tracker.check_budget(agent_role=agent_role)


@router.get("/api/costs/forecast")
async def cost_forecast(days: int = 7, user: dict = Depends(get_current_user)):
    """Get cost forecast based on trends."""
    return _cost_tracker.get_cost_forecast(days=days)


@router.get("/api/costs/stats")
async def usage_stats(user: dict = Depends(get_current_user)):
    """Get overall usage statistics."""
    return _cost_tracker.get_usage_stats()


# ── Auto-Optimizer API ───────────────────────────────────────────

try:
    from tools.auto_optimizer import get_auto_optimizer

    _auto_optimizer = get_auto_optimizer()
    print("[Backend] auto_optimizer loaded OK (monitoring)")
except Exception as _e:
    print(f"[Backend] WARNING: auto_optimizer import failed: {_e}")
    _auto_optimizer = None


@router.get("/api/optimizer/stats")
async def optimizer_stats(user: dict = Depends(get_current_user)):
    """Get optimization statistics summary."""
    stats = _auto_optimizer.get_optimization_stats()
    return stats


@router.get("/api/optimizer/recommendations")
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


@router.post("/api/optimizer/analyze")
async def optimizer_analyze(user: dict = Depends(get_current_user)):
    """Run full analysis and generate new recommendations."""
    _audit("optimizer_analyze", user["user_id"])
    new_recs = _auto_optimizer.analyze_and_recommend()
    return {"new_recommendations": new_recs, "total_new": len(new_recs)}


@router.post("/api/optimizer/recommendations/{rec_id}/apply")
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


@router.post("/api/optimizer/recommendations/{rec_id}/dismiss")
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


@router.get("/api/optimizer/agent/{agent_role}")
async def optimizer_agent_profile(
    agent_role: str,
    user: dict = Depends(get_current_user),
):
    """Get optimization profile for a specific agent."""
    profile = _auto_optimizer.get_agent_optimization_profile(agent_role)
    return profile


@router.get("/api/optimizer/history")
async def optimizer_history(
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Get optimization action history."""
    history = _auto_optimizer.get_optimization_history(limit=limit)
    return {"history": history, "total": len(history)}


# ── Adaptive Tool Selection API ──────────────────────────────────

try:
    from tools.adaptive_tool_selector import get_adaptive_tool_selector

    _tool_selector = get_adaptive_tool_selector()
    print("[Backend] adaptive_tool_selector loaded OK (monitoring)")
except Exception as _e:
    print(f"[Backend] WARNING: adaptive_tool_selector import failed: {_e}")
    _tool_selector = None


@router.get("/api/optimizer/tool-patterns")
async def tool_pattern_analysis(user: dict = Depends(get_current_user)):
    """Get tool usage patterns across all agents."""
    if _tool_selector is None:
        raise HTTPException(status_code=503, detail="Tool selector not available")
    stats = _tool_selector.get_statistics()
    return stats


@router.get("/api/optimizer/suggested-tools")
async def get_suggested_tools(
    task_context: str,
    user: dict = Depends(get_current_user),
):
    """Get tool recommendations based on task context."""
    if _tool_selector is None:
        raise HTTPException(status_code=503, detail="Tool selector not available")
    recommendation = _tool_selector.analyze_task(task_context)
    return {"recommendation": recommendation}


@router.post("/api/optimizer/apply-tool-suggestion")
async def apply_tool_suggestion(
    task_input: str,
    tool_name: str,
    agent_role: str,
    success: bool = True,
    user: dict = Depends(get_current_user),
):
    """Apply a tool suggestion and learn from the outcome."""
    if _tool_selector is None:
        raise HTTPException(status_code=503, detail="Tool selector not available")
    if success:
        _tool_selector.record_success(agent_role, tool_name, task_input)
    else:
        _tool_selector.record_failure(
            agent_role, tool_name, task_input, "User feedback"
        )
    return {"status": "learned", "recorded": success}


@router.get("/api/optimizer/agent-tool-matrix")
async def get_agent_tool_matrix(user: dict = Depends(get_current_user)):
    """Get agent-to-tool effectiveness matrix."""
    if _tool_selector is None:
        raise HTTPException(status_code=503, detail="Tool selector not available")
    stats = _tool_selector.get_statistics()
    return {
        "matrix": stats.get("pattern_matrix", {}),
        "categories": stats.get("context_categories", []),
    }


# ── Adaptive Tools Panel API (Faz 9 — 4-tab UI) ──────────────────


@router.get("/api/adaptive-tools/usage")
async def adaptive_tools_usage(user: dict = Depends(get_current_user)):
    """Tool usage list for Adaptif Araç Seçimi panel (Kullanım sekmesi)."""
    if _tool_selector is None:
        return []
    stats = _tool_selector.get_statistics()
    matrix = stats.get("pattern_matrix", {}) or {}
    # Aggregate per-tool across agents
    by_tool: dict[str, dict] = {}
    for _agent, data in matrix.items():
        for item in data.get("top_tools", []) if isinstance(data, dict) else []:
            if isinstance(item, dict):
                tool = item.get("tool") or item.get("tool_name")
                if not tool:
                    continue
                if tool not in by_tool:
                    by_tool[tool] = {"usage_count": 0, "success": 0}
                by_tool[tool]["usage_count"] += item.get("count", 0)
                by_tool[tool]["success"] += item.get("success", 0)
    result = [
        {
            "tool_name": tool,
            "usage_count": agg["usage_count"],
            "success_rate": round(100 * agg["success"] / agg["usage_count"], 1)
            if agg["usage_count"]
            else 0,
            "avg_latency_ms": 0,
            "last_used": "",
        }
        for tool, agg in by_tool.items()
    ]
    result.sort(key=lambda x: x["usage_count"], reverse=True)
    return result


@router.get("/api/adaptive-tools/recommendations")
async def adaptive_tools_recommendations(user: dict = Depends(get_current_user)):
    """Tool recommendations for Adaptif Araç Seçimi panel (Öneriler sekmesi)."""
    if _tool_selector is None:
        return []
    try:
        scores = _tool_selector.context_scorer.get_best_tools("general", 10)
    except Exception:
        return []
    items = (scores or []) if isinstance(scores, list) else []
    return [
        {
            "tool_name": item.get("tool") or item.get("tool_name", ""),
            "score": round(float(item.get("score", 50)), 1),
            "reason": "Bağlam ve kullanım örüntüsüne göre öneri",
            "context": "general",
        }
        for item in items
    ]


@router.get("/api/adaptive-tools/preferences")
async def adaptive_tools_preferences(user: dict = Depends(get_current_user)):
    """User tool preferences for Adaptif Araç Seçimi panel (Tercihler sekmesi)."""
    if _tool_selector is None:
        return []
    prefs = _tool_selector.user_behavior.get_preferences() or {}
    uid = user.get("user_id", "")
    result = []
    for key, val in prefs.items():
        if not isinstance(val, dict):
            continue
        for tool in val.get("tools", []):
            result.append(
                {
                    "tool_name": tool,
                    "preference_score": 1,
                    "user_id": uid,
                }
            )
    return result


# ── Workflow Optimizer API ───────────────────────────────────────

try:
    from tools.workflow_optimizer import get_workflow_optimizer

    _workflow_optimizer = get_workflow_optimizer()
    print("[Backend] workflow_optimizer loaded OK (monitoring)")
except Exception as _e:
    print(f"[Backend] WARNING: workflow_optimizer import failed: {_e}")
    _workflow_optimizer = None


@router.get("/api/workflow-optimizer/stats")
async def workflow_optimizer_stats(user: dict = Depends(get_current_user)):
    """Get workflow optimization statistics."""
    if _workflow_optimizer is None:
        raise HTTPException(status_code=503, detail="Workflow optimizer not available")
    return _workflow_optimizer.get_statistics()


@router.get("/api/workflow-optimizer/suggestions")
async def workflow_optimizer_suggestions(
    template_name: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get workflow optimization suggestions."""
    if _workflow_optimizer is None:
        raise HTTPException(status_code=503, detail="Workflow optimizer not available")
    suggestions = _workflow_optimizer.generate_suggestions(template_name=template_name)
    return {"suggestions": suggestions, "total": len(suggestions)}


@router.get("/api/workflow-optimizer/workflow/{workflow_id}")
async def workflow_optimizer_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
):
    """Get detailed stats for a specific workflow."""
    if _workflow_optimizer is None:
        raise HTTPException(status_code=503, detail="Workflow optimizer not available")
    return _workflow_optimizer.get_workflow_stats(workflow_id)


@router.post("/api/workflow-optimizer/optimize-template")
async def optimize_workflow_template(
    template_name: str,
    auto_apply: bool = False,
    user: dict = Depends(get_current_user),
):
    """Analyze and optimize a workflow template."""
    if _workflow_optimizer is None:
        raise HTTPException(status_code=503, detail="Workflow optimizer not available")

    from tools.workflow_engine import WORKFLOW_TEMPLATES

    if template_name not in WORKFLOW_TEMPLATES:
        raise HTTPException(
            status_code=404, detail=f"Template '{template_name}' not found"
        )

    wf = WORKFLOW_TEMPLATES[template_name]
    steps = [{"step_id": s.step_id, "step_type": s.step_type} for s in wf.steps]

    result = _workflow_optimizer.optimize_workflow(
        wf.workflow_id, steps, auto_apply=auto_apply
    )
    return result


@router.post("/api/workflow-optimizer/record-execution")
async def record_workflow_execution(
    execution: dict[str, Any],
    user: dict = Depends(get_current_user),
):
    """Record a workflow execution for optimization learning."""
    if _workflow_optimizer is None:
        raise HTTPException(status_code=503, detail="Workflow optimizer not available")
    _workflow_optimizer.record_execution(execution)
    return {"status": "recorded"}
