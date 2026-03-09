"""
Workflow Optimizer Engine for multi-agent system.

Analyzes workflow execution history and performance data to automatically
optimize workflow templates and suggest improvements based on patterns.

Functions:
- WorkflowPerformanceAnalyzer: Analyzes historical workflow performance
- PatternBasedOptimizer: Identifies optimization patterns
- SuggestionEngine: Generates improvement suggestions
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

_SLOW_WORKFLOW_MS = 10000.0
_LOW_SUCCESS_RATE_PCT = 60.0
_HIGH_ERROR_COUNT = 3
_REPEATING_PATTERN_MIN = 3
_MAX_OPTIMIZED_STEPS = 8


@dataclass
class WorkflowPattern:
    pattern_id: str
    name: str
    description: str
    type: str
    frequency: int
    optimization_suggestion: str
    affected_workflows: list[str]



@dataclass
class OptimizationSuggestion:
    suggestion_id: str
    workflow_id: str
    workflow_name: str
    type: str
    current_state: str
    suggested_change: str
    estimated_impact: str
    confidence: float
    automated: bool = False


class WorkflowPerformanceAnalyzer:
    """Analyzes workflow execution history for performance patterns."""

    def __init__(self):
        self._db_initialized = False
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Mark DB as initialized (schema handled by migration SQL)."""
        if self._db_initialized:
            return
        self._db_initialized = True

    def record_execution(self, result: dict[str, Any]) -> None:
        """Record a workflow execution result."""
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO workflow_executions
                    (workflow_id, workflow_name, template_name, status, duration_ms,
                     step_count, error_count, variables_json, step_results_json, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    result.get("workflow_id", "unknown"),
                    result.get("workflow_name", "unknown"),
                    result.get("template_name", "custom"),
                    result.get("status", "unknown"),
                    result.get("duration_ms", 0),
                    result.get("step_count", 0),
                    result.get("error_count", 0),
                    json.dumps(result.get("variables", {})),
                    json.dumps(result.get("step_results", {})),
                ))
            conn.commit()
        finally:
            release_conn(conn)

    def get_workflow_stats(self, workflow_id: str | None = None,
                           limit: int = 100) -> dict[str, Any]:
        """Get statistics for workflow executions."""
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                if workflow_id:
                    cur.execute("""
                        SELECT * FROM workflow_executions
                        WHERE workflow_id = %s
                        ORDER BY created_at DESC LIMIT %s
                    """, (workflow_id, limit))
                    name = "unknown"
                else:
                    cur.execute("""
                        SELECT * FROM workflow_executions
                        ORDER BY created_at DESC LIMIT %s
                    """, (limit,))
                    name = None
                rows = cur.fetchall()
        finally:
            release_conn(conn)
        if not rows:
            return {"name": name or workflow_id, "executions": [], "stats": {}}
        stats = self._calculate_stats(rows)
        return {"name": name or workflow_id, "executions": [dict(r) for r in rows], "stats": stats}

    def _calculate_stats(self, rows: list) -> dict[str, Any]:
        durations = [float(r["duration_ms"]) for r in rows if r["duration_ms"]]
        errors = [r for r in rows if r["error_count"] and int(r["error_count"]) > 0]
        return {
            "total_executions": len(rows),
            "success_count": len([r for r in rows if r["status"] == "completed"]),
            "failure_count": len([r for r in rows if r["status"] in ("failed", "rolled_back")]),
            "avg_duration_ms": round(sum(durations) / len(durations), 0) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "error_rate_pct": round((len(errors) / len(rows)) * 100, 1) if rows else 0,
        }

    def get_slow_workflows(self, threshold_ms: float = _SLOW_WORKFLOW_MS,
                           limit: int = 20) -> list[dict[str, Any]]:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT workflow_name, template_name, AVG(duration_ms) as avg_ms,
                           COUNT(*) as execution_count
                    FROM workflow_executions WHERE duration_ms > %s
                    GROUP BY workflow_name, template_name
                    HAVING COUNT(*) >= 2 ORDER BY avg_ms DESC LIMIT %s
                """, (threshold_ms, limit))
                rows = cur.fetchall()
        finally:
            release_conn(conn)
        return [{"name": r["workflow_name"], "template": r["template_name"],
                 "avg_ms": round(float(r["avg_ms"]), 0),
                 "count": r["execution_count"]} for r in rows]

    def get_error_patterns(self, limit: int = 20) -> list[dict[str, Any]]:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT workflow_name, template_name, SUM(error_count) as total_errors,
                           COUNT(*) as execution_count
                    FROM workflow_executions WHERE error_count > 0
                    GROUP BY workflow_name, template_name
                    HAVING SUM(error_count) >= %s
                    ORDER BY total_errors DESC LIMIT %s
                """, (_HIGH_ERROR_COUNT, limit))
                rows = cur.fetchall()
        finally:
            release_conn(conn)
        return [{"name": r["workflow_name"], "template": r["template_name"],
                 "total_errors": r["total_errors"],
                 "error_rate_pct": round((r["total_errors"] / r["execution_count"]) * 100, 1)}
                for r in rows]



class PatternBasedOptimizer:
    """Identifies optimization patterns in workflow executions."""

    def __init__(self):
        self.analyzer = WorkflowPerformanceAnalyzer()

    def analyze_workflow(self, workflow_id: str, workflow_name: str,
                         steps: list[dict]) -> list[dict[str, Any]]:
        suggestions = []
        stats = self.analyzer.get_workflow_stats(workflow_id)
        if stats["stats"].get("avg_duration_ms", 0) > _SLOW_WORKFLOW_MS:
            suggestions.append({
                "type": "performance-slow",
                "severity": "high" if stats["stats"]["avg_duration_ms"] > 30000 else "medium",
                "current": f"{stats['stats']['avg_duration_ms']:.0f}ms avg",
                "suggestion": "Consider parallelizing sequential steps or using faster agents",
                "affected_steps": self._find_bottleneck_steps(steps),
            })
        if stats["stats"].get("error_rate_pct", 0) > (100 - _LOW_SUCCESS_RATE_PCT):
            suggestions.append({
                "type": "reliability-low",
                "severity": "high",
                "current": f"{stats['stats']['error_rate_pct']:.1f}% failure rate",
                "suggestion": "Add error handling, retries, or fallback steps",
                "affected_steps": self._find_error_prone_steps(steps, stats["executions"]),
            })
        tool_calls = [s for s in steps if s.get("step_type") == "tool_call"]
        if len(tool_calls) >= 3:
            suggestions.append({
                "type": "redundant-tools",
                "severity": "medium",
                "current": f"{len(tool_calls)} sequential tool calls",
                "suggestion": "Combine related tool calls into a custom tool or use spawn_subagent",
                "affected_steps": [t.get("step_id") for t in tool_calls[:3]],
            })
        sequential_count = sum(1 for s in steps if s.get("step_type") in ("tool_call", "agent_call"))
        if sequential_count >= 4:
            suggestions.append({
                "type": "parallel-opportunity",
                "severity": "medium",
                "current": f"{sequential_count} sequential steps",
                "suggestion": "Review if steps are independent and can run in parallel",
                "affected_steps": [s.get("step_id") for s in steps[:4]],
            })
        return suggestions

    def _find_bottleneck_steps(self, steps: list) -> list[str]:
        bottleneck_types = ["agent_call", "condition", "parallel"]
        return [s.get("step_id") for s in steps if s.get("step_type") in bottleneck_types]

    def _find_error_prone_steps(self, steps: list, executions: list) -> list[str]:
        return [s.get("step_id") for s in steps if s.get("step_type") == "agent_call"]

    def find_global_patterns(self, limit: int = 20) -> list[dict[str, Any]]:
        patterns = []
        stats = self.analyzer.get_workflow_stats(limit=500)
        if stats.get("executions"):
            tool_call_sequences = defaultdict(int)
            for exec in stats["executions"]:
                step_results = json.loads(exec.get("step_results_json", "{}"))
                tool_count = sum(1 for k, v in step_results.items()
                                if isinstance(v, str) and len(v) > 10)
                key = f"{tool_count} tool calls"
                tool_call_sequences[key] += 1
            for key, count in sorted(tool_call_sequences.items(), key=lambda x: -x[1])[:5]:
                if count >= 3:
                    patterns.append({
                        "type": "sequential-tool-count",
                        "pattern": key,
                        "occurrence_count": count,
                        "suggestion": "Consider consolidating tool calls into a single agent task",
                    })
        slow = self.analyzer.get_slow_workflows(limit=10)
        for s in slow:
            if s["count"] >= 2:
                patterns.append({
                    "type": "slow-template",
                    "template": s["template"],
                    "avg_ms": s["avg_ms"],
                    "suggestion": "Review workflow steps for optimization opportunities",
                })
        return patterns[:limit]



class SuggestionEngine:
    """Generates and manages workflow optimization suggestions."""

    def __init__(self):
        self.pattern_optimizer = PatternBasedOptimizer()

    def generate_suggestions(self, template_name: str | None = None) -> list[dict[str, Any]]:
        suggestions = []
        global_patterns = self.pattern_optimizer.find_global_patterns(limit=10)
        for p in global_patterns:
            suggestions.append({
                "suggestion_id": f"global-{p['type']}",
                "workflow_id": "all",
                "workflow_name": "All Workflows",
                "type": p["type"],
                "current_state": f"{p['pattern'] if 'pattern' in p else 'High occurrence'}",
                "suggested_change": p["suggestion"],
                "estimated_impact": self._estimate_impact(p["type"]),
                "confidence": 75.0 if p["type"] == "sequential-tool-count" else 60.0,
                "automated": False,
            })
        if template_name:
            from tools.workflow_engine import WORKFLOW_TEMPLATES
            if template_name in WORKFLOW_TEMPLATES:
                wf = WORKFLOW_TEMPLATES[template_name]
                workflow_stats = self.pattern_optimizer.analyzer.get_workflow_stats(
                    workflow_id=wf.workflow_id, limit=50
                )
                template_suggestions = self.pattern_optimizer.analyze_workflow(
                    wf.workflow_id, wf.name, [s for s in wf.steps]
                )
                for s in template_suggestions:
                    suggestions.append({
                        "suggestion_id": f"template-{template_name}-{s['type']}",
                        "workflow_id": wf.workflow_id,
                        "workflow_name": wf.name,
                        "type": s["type"],
                        "current_state": s["current"],
                        "suggested_change": s["suggestion"],
                        "estimated_impact": self._estimate_impact(s["type"]),
                        "confidence": 80.0 if s["severity"] == "high" else 65.0,
                        "automated": s["severity"] != "high",
                    })
        return suggestions

    def _estimate_impact(self, suggestion_type: str) -> str:
        impacts = {
            "performance-slow": "Reduce execution time by 30-50%",
            "reliability-low": "Improve success rate by 15-25%",
            "redundant-tools": "Reduce tokens by 20-40%",
            "parallel-opportunity": "Reduce execution time by 40-60%",
            "sequential-tool-count": "Reduce overhead by 25-35%",
            "slow-template": "Variable improvement based on optimization",
        }
        return impacts.get(suggestion_type, "Unknown improvement")

    def auto_apply_suggestions(self, suggestions: list[dict]) -> dict[str, Any]:
        applied = []
        skipped = []
        for s in suggestions:
            if s.get("automated", False):
                applied.append(s["suggestion_id"])
            else:
                skipped.append(s["suggestion_id"])
        return {"applied": applied, "skipped": skipped, "total": len(suggestions)}



class WorkflowOptimizer:
    """Main engine combining all optimization components."""

    def __init__(self):
        self.analyzer = WorkflowPerformanceAnalyzer()
        self.pattern_optimizer = PatternBasedOptimizer()
        self.suggestion_engine = SuggestionEngine()

    def record_execution(self, result: dict[str, Any]) -> None:
        self.analyzer.record_execution(result)

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_executions_analyzed": self._get_total_executions(),
            "slow_workflows": len(self.analyzer.get_slow_workflows()),
            "error_workflows": len(self.analyzer.get_error_patterns()),
            "global_patterns": self.pattern_optimizer.find_global_patterns()[:10],
        }

    def _get_total_executions(self) -> int:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM workflow_executions")
                row = cur.fetchone()
                return row["count"] if row else 0
        finally:
            release_conn(conn)

    def get_workflow_stats(self, workflow_id: str) -> dict[str, Any]:
        return self.analyzer.get_workflow_stats(workflow_id)

    def analyze_workflow(self, workflow_id: str, workflow_name: str,
                         steps: list[dict]) -> list[dict[str, Any]]:
        return self.pattern_optimizer.analyze_workflow(workflow_id, workflow_name, steps)

    def generate_suggestions(self, template_name: str | None = None) -> list[dict[str, Any]]:
        return self.suggestion_engine.generate_suggestions(template_name)

    def optimize_workflow(self, workflow_id: str, steps: list[dict],
                          auto_apply: bool = False) -> dict[str, Any]:
        suggestions = self.analyzer.analyze_workflow(workflow_id, "optimized", steps)
        optimized = {
            "original_steps": steps,
            "suggestions": suggestions,
            "optimized_steps": steps,
            "applied": [],
            "recommendations": [],
        }
        if auto_apply:
            for s in suggestions:
                if s.get("severity") != "high":
                    optimized["applied"].append(s["type"])
                    optimized["steps"] = self._apply_optimization(
                        optimized["steps"], s["type"]
                    )
        return optimized

    def _apply_optimization(self, steps: list[dict], opt_type: str) -> list[dict]:
        if opt_type == "parallel-opportunity":
            if len(steps) >= 2:
                parallel_step = {
                    "step_id": "parallel-1",
                    "step_type": "parallel",
                    "parallel_steps": [steps[0].get("step_id"), steps[1].get("step_id")],
                    "timeout_seconds": 120,
                }
                return [parallel_step] + steps[2:]
        return steps


_optimizer: WorkflowOptimizer | None = None


def get_workflow_optimizer() -> WorkflowOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = WorkflowOptimizer()
    return _optimizer
