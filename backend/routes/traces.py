"""Execution trace endpoints — view, query, and analyze agent traces."""

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user
from tools.observability import (
    get_agent_traces,
    get_recent_traces,
    get_trace_stats,
    get_traces,
)

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("")
async def list_recent_traces(
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Get recent execution traces grouped by trace_id."""
    traces = get_recent_traces(limit=limit)
    return {"traces": traces, "count": len(traces)}


@router.get("/stats")
async def trace_statistics(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Aggregate trace statistics: avg latency, error rate, top tools."""
    return get_trace_stats()


@router.get("/{trace_id}")
async def trace_detail(
    trace_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all steps for a specific trace."""
    steps = get_traces(trace_id)
    if not steps:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"trace_id": trace_id, "steps": steps, "step_count": len(steps)}


@router.get("/agent/{agent_role}")
async def agent_traces(
    agent_role: str,
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Get traces for a specific agent role."""
    traces = get_agent_traces(agent_role, limit=limit)
    return {"agent_role": agent_role, "traces": traces, "count": len(traces)}
