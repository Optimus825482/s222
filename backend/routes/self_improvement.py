"""
Self-Improvement API Routes — Faz 16.
Metrics, A/B experiments, prompt strategies, routing weights, dashboard.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("self_improvement")
router = APIRouter(tags=["self-improvement"])


# ── Request Models ───────────────────────────────────────────────

class ExperimentRequest(BaseModel):
    experiment_id: str
    agent_role: str
    task_type: str
    control_strategy_id: int
    variant_strategy_id: int
    traffic_split: float = Field(0.5, ge=0, le=1)


class PromptStrategyRequest(BaseModel):
    agent_role: str
    task_type: str
    name: str
    system_prompt: str
    few_shot_examples: list = Field(default_factory=list)
    cot_instructions: str = ""
    metadata: dict = Field(default_factory=dict)


# ── Metrics Endpoints ────────────────────────────────────────────

@router.get("/api/metrics/agents/{agent_role}")
def get_agent_metrics(agent_role: str):
    """Aggregated agent performance stats."""
    from tools.performance_collector import get_performance_collector
    return get_performance_collector().get_agent_stats(agent_role)


@router.get("/api/metrics/skills/{skill_id}")
def get_skill_metrics(skill_id: str):
    """Skill usage stats."""
    from tools.performance_collector import get_performance_collector
    return get_performance_collector().get_skill_stats(skill_id)


# ── Experiment Endpoints ─────────────────────────────────────────

@router.post("/api/experiments")
def create_experiment(req: ExperimentRequest):
    """Create A/B experiment."""
    from tools.ab_testing import get_ab_test_manager
    try:
        return get_ab_test_manager().create_experiment(
            experiment_id=req.experiment_id,
            agent_role=req.agent_role,
            task_type=req.task_type,
            control_strategy_id=req.control_strategy_id,
            variant_strategy_id=req.variant_strategy_id,
            traffic_split=req.traffic_split,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/api/experiments")
def list_experiments(status: str | None = None):
    """List experiments with optional status filter."""
    from tools.ab_testing import get_ab_test_manager
    return {"experiments": get_ab_test_manager().list_experiments(status=status)}


@router.post("/api/prompt-strategies")
def create_prompt_strategy(req: PromptStrategyRequest):
    """Create new prompt strategy."""
    from tools.prompt_strategies import get_prompt_strategy_manager
    return get_prompt_strategy_manager().create(
        agent_role=req.agent_role,
        task_type=req.task_type,
        name=req.name,
        system_prompt=req.system_prompt,
        few_shot_examples=req.few_shot_examples,
        cot_instructions=req.cot_instructions,
        metadata=req.metadata,
    )


@router.get("/api/prompt-strategies")
def list_prompt_strategies(
    agent_role: str | None = None,
    task_type: str | None = None,
):
    """List prompt strategies with optional filters."""
    from tools.prompt_strategies import get_prompt_strategy_manager
    return {"strategies": get_prompt_strategy_manager().list_strategies(agent_role=agent_role, task_type=task_type)}


@router.post("/api/prompt-strategies/{strategy_id}/activate")
def activate_prompt_strategy(strategy_id: int):
    """Activate a prompt strategy. Returns 409 if active A/B experiment conflicts."""
    from tools.prompt_strategies import get_prompt_strategy_manager
    try:
        return get_prompt_strategy_manager().activate(strategy_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/api/routing/weights")
def get_routing_weights():
    """Current routing weights for all task types."""
    from tools.dynamic_router import get_dynamic_router
    return {"weights": get_dynamic_router().get_weights()}


@router.get("/api/dashboard/overview")
def dashboard_overview():
    """System overview: total metrics, experiments, strategies."""
    overview = {}
    try:
        from tools.pg_connection import get_pg_connection
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM performance_metrics")
            overview["total_metrics"] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM ab_experiments")
            overview["total_experiments"] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM ab_experiments WHERE status = 'active'")
            overview["active_experiments"] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM prompt_strategies")
            overview["total_strategies"] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM prompt_strategies WHERE is_active = TRUE")
            overview["active_strategies"] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM optimization_history")
            overview["total_optimizations"] = cur.fetchone()["cnt"]
        conn.close()
    except Exception as e:
        overview["error"] = str(e)
    return overview


@router.get("/api/dashboard/agents/{agent_role}/history")
def agent_history(
    agent_role: str,
    granularity: str = Query("hour", regex="^(hour|day|week)$"),
    limit: int = Query(50, ge=1, le=500),
):
    """Time-series performance data for an agent."""
    trunc_map = {"hour": "hour", "day": "day", "week": "week"}
    trunc = trunc_map.get(granularity, "hour")
    try:
        from tools.pg_connection import get_pg_connection
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT date_trunc('{trunc}', created_at) as period,
                       COUNT(*) as task_count,
                       AVG(score) as avg_score,
                       AVG(latency_ms) as avg_latency,
                       SUM(tokens_used) as total_tokens
                FROM performance_metrics
                WHERE agent_role = %s
                GROUP BY period
                ORDER BY period DESC
                LIMIT %s
            """, (agent_role, limit))
            rows = cur.fetchall()
        conn.close()
        return {
            "agent_role": agent_role,
            "granularity": granularity,
            "data": [
                {
                    "period": r["period"].isoformat() if hasattr(r["period"], "isoformat") else str(r["period"]),
                    "task_count": r["task_count"],
                    "avg_score": round(float(r["avg_score"] or 0), 2),
                    "avg_latency_ms": round(float(r["avg_latency"] or 0), 1),
                    "total_tokens": int(r["total_tokens"] or 0),
                }
                for r in rows
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/dashboard/optimization-log")
def optimization_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Paginated optimization history."""
    from tools.feedback_loop import get_feedback_loop
    return {"log": get_feedback_loop().get_optimization_log(limit=limit, offset=offset)}


@router.get("/api/dashboard/skill-leaderboard")
def skill_leaderboard(top_n: int = Query(20, ge=1, le=100)):
    """Skills ranked by Skill_Score."""
    from tools.optimization_engine import get_optimization_engine
    return {"leaderboard": get_optimization_engine().get_skill_leaderboard(top_n=top_n)}
