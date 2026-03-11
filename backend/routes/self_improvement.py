"""
Self-Improvement API Routes — Faz 16.
Metrics, A/B experiments, prompt strategies, routing weights, dashboard.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("self_improvement")
router = APIRouter(tags=["self-improvement"])


def _row_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {}


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

    collector: Any = get_performance_collector()
    return collector.get_agent_stats(agent_role)


@router.get("/api/metrics/skills/{skill_id}")
def get_skill_metrics(skill_id: str):
    """Skill usage stats."""
    from tools.performance_collector import get_performance_collector

    collector: Any = get_performance_collector()
    return collector.get_skill_stats(skill_id)


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
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM performance_metrics")
            overview["total_metrics"] = int(
                _row_dict(cur.fetchone()).get("cnt", 0) or 0
            )
            cur.execute("SELECT COUNT(*) as cnt FROM ab_experiments")
            overview["total_experiments"] = int(
                _row_dict(cur.fetchone()).get("cnt", 0) or 0
            )
            cur.execute("SELECT COUNT(*) as cnt FROM ab_experiments WHERE status = 'active'")
            overview["active_experiments"] = int(
                _row_dict(cur.fetchone()).get("cnt", 0) or 0
            )
            cur.execute("SELECT COUNT(*) as cnt FROM prompt_strategies")
            overview["total_strategies"] = int(
                _row_dict(cur.fetchone()).get("cnt", 0) or 0
            )
            cur.execute("SELECT COUNT(*) as cnt FROM prompt_strategies WHERE is_active = TRUE")
            overview["active_strategies"] = int(
                _row_dict(cur.fetchone()).get("cnt", 0) or 0
            )
            cur.execute("SELECT COUNT(*) as cnt FROM optimization_history")
            overview["total_optimizations"] = int(
                _row_dict(cur.fetchone()).get("cnt", 0) or 0
            )
        release_conn(conn)
    except Exception as e:
        overview["error"] = str(e)
    return overview


@router.get("/api/dashboard/agents/{agent_role}/history")
def agent_history(
    agent_role: str,
    granularity: str = Query("hour", pattern="^(hour|day|week)$"),
    limit: int = Query(50, ge=1, le=500),
):
    """Time-series performance data for an agent."""
    trunc_map = {"hour": "hour", "day": "day", "week": "week"}
    trunc = trunc_map.get(granularity, "hour")
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
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
        release_conn(conn)
        data = []
        for row in rows:
            row_data = _row_dict(row)
            period_value = row_data.get("period")
            period_str = (
                period_value.isoformat()
                if period_value is not None and hasattr(period_value, "isoformat")
                else str(period_value)
            )
            data.append(
                {
                    "period": period_str,
                    "task_count": int(row_data.get("task_count", 0) or 0),
                    "avg_score": round(float(row_data.get("avg_score", 0) or 0), 2),
                    "avg_latency_ms": round(
                        float(row_data.get("avg_latency", 0) or 0), 1
                    ),
                    "total_tokens": int(row_data.get("total_tokens", 0) or 0),
                }
            )
        return {
            "agent_role": agent_role,
            "granularity": granularity,
            "data": data,
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
