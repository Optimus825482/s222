"""Analytics route module — agent health, leaderboard, monitoring, coordination, ecosystem."""

import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from config import MODELS
from core.state import list_threads, load_thread
from shared_state import _AGENT_ROLES, _AUDIT_LOG, _utcnow, _APP_START_TIME

router = APIRouter()


# ── 1. Agent Performance Analytics ───────────────────────────────


@router.get("/api/agents/health")
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


@router.get("/api/agents/{role}/performance")
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


@router.get("/api/agents/leaderboard")
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
# NOTE: /api/skills/auto-discover endpoint lives in auth_and_tools.py (single source of truth).
# Removed duplicate from here to prevent FastAPI route conflict.


# ── 3. Security & Monitoring ────────────────────────────────────


@router.get("/api/security/audit-log")
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


@router.get("/api/monitoring/system-stats")
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


@router.get("/api/monitoring/anomalies")
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


@router.get("/api/threads/{thread_id}/analytics")
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


@router.post("/api/coordination/assign")
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


@router.get("/api/coordination/matrix")
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


@router.get("/api/coordination/rotation-history")
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


@router.get("/api/agents/ecosystem")
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
