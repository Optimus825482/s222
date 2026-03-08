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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
OPTIMIZER_DB = DATA_DIR / "workflow_optimization.db"

# ── Thresholds ────────────────────────────────────────────────────

_SLOW_WORKFLOW_MS = 10000.0          # above this → consider optimization
_LOW_SUCCESS_RATE_PCT = 60.0         # below this → high priority
_HIGH_ERROR_COUNT = 3                # above this → flag workflow
_REPEATING_PATTERN_MIN = 3           # minimum occurrences to identify pattern
_MAX_OPTIMIZED_STEPS = 8             # max steps after optimization


# ── Data Models ──────────────────────────────────────────────────

@dataclass
class WorkflowPattern:
    """Represents a recurring pattern in workflow execution."""
    pattern_id: str
    name: str
    description: str
    type: str  # "sequential-bottleneck", "redundant-tool", "parallel-opportunity"
    frequency: int
    optimization_suggestion: str
    affected_workflows: list[str]


@dataclass
class OptimizationSuggestion:
    """A suggested workflow optimization."""
    suggestion_id: str
    workflow_id: str
    workflow_name: str
    type: str  # "merge-steps", "add-parallel", "remove-redundant", "optimize-tool"
    current_state: str
    suggested_change: str
    estimated_impact: str  # e.g., "reduce by 30%", "save 2 toxic calls"
    confidence: float
    automated: bool = False  # if True, can be applied automatically


# ── Workflow Performance Analyzer ─────────────────────────────────

class WorkflowPerformanceAnalyzer:
    """Analyzes workflow execution history for performance patterns."""

    def __init__(self):
        self._db_initialized = False
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create database tables if they don't exist."""
        if self._db_initialized:
            return

        conn = sqlite3.connect(str(OPTIMIZER_DB))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                workflow_name TEXT,
                template_name TEXT,
                status TEXT,
                duration_ms REAL,
                step_count INTEGER,
                error_count INTEGER,
                variables_json TEXT,
                step_results_json TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wfe_workflow
                ON workflow_executions(workflow_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wfe_created
                ON workflow_executions(created_at DESC)
        """)
        conn.commit()
        conn.close()

        self._db_initialized = True

    def record_execution(self, result: dict[str, Any]) -> None:
        """Record a workflow execution result."""
        conn = sqlite3.connect(str(OPTIMIZER_DB))
        conn.execute("""
            INSERT INTO workflow_executions
            (workflow_id, workflow_name, template_name, status, duration_ms,
             step_count, error_count, variables_json, step_results_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            datetime.now(timezone.utc).isoformat(),
        ))
        conn.commit()
        conn.close()

    def get_workflow_stats(self, workflow_id: str | None = None,
                           limit: int = 100) -> dict[str, Any]:
        """Get statistics for workflow executions."""
        conn = sqlite3.connect(str(OPTIMIZER_DB))
        conn.row_factory = sqlite3.Row

        if workflow_id:
            rows = conn.execute("""
                SELECT * FROM workflow_executions
                WHERE workflow_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (workflow_id, limit)).fetchall()
            name = "unknown"
        else:
            rows = conn.execute("""
                SELECT * FROM workflow_executions
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            name = None

        conn.close()

        if not rows:
            return {"name": name or workflow_id, "executions": [], "stats": {}}

        stats = self._calculate_stats(rows)
        return {"name": name or workflow_id, "executions": [dict(r) for r in rows], "stats": stats}

    def _calculate_stats(self, rows: list) -> dict[str, Any]:
        """Calculate statistics from execution rows."""
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
        """Get workflows with execution times above threshold."""
        conn = sqlite3.connect(str(OPTIMIZER_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT workflow_name, template_name, AVG(duration_ms) as avg_ms,
                   COUNT(*) as execution_count
            FROM workflow_executions
            WHERE duration_ms > ?
            GROUP BY workflow_name, template_name
            HAVING COUNT(*) >= 2
            ORDER BY avg_ms DESC
            LIMIT ?
        """, (threshold_ms, limit)).fetchall()
        conn.close()

        return [{"name": r["workflow_name"], "template": r["template_name"],
                 "avg_ms": round(float(r["avg_ms"]), 0),
                 "count": r["execution_count"]} for r in rows]

    def get_error_patterns(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get workflows with recurring errors."""
        conn = sqlite3.connect(str(OPTIMIZER_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT workflow_name, template_name, SUM(error_count) as total_errors,
                   COUNT(*) as execution_count
            FROM workflow_executions
            WHERE error_count > 0
            GROUP BY workflow_name, template_name
            HAVING total_errors >= ?
            ORDER BY total_errors DESC
            LIMIT ?
        """, (_HIGH_ERROR_COUNT, limit)).fetchall()
        conn.close()

        return [{"name": r["workflow_name"], "template": r["template_name"],
                 "total_errors": r["total_errors"],
                 "error_rate_pct": round((r["total_errors"] / r["execution_count"]) * 100, 1)}
                for r in rows]


# ── Pattern Based Optimizer ───────────────────────────────────────

class PatternBasedOptimizer:
    """Identifies optimization patterns in workflow executions."""

    def __init__(self):
        self.analyzer = WorkflowPerformanceAnalyzer()

    def analyze_workflow(self, workflow_id: str, workflow_name: str,
                         steps: list[dict]) -> list[dict[str, Any]]:
        """Analyze a specific workflow for optimization opportunities."""
        suggestions = []

        # Get execution history for this workflow
        stats = self.analyzer.get_workflow_stats(workflow_id)

        # Check for slow execution
        if stats["stats"].get("avg_duration_ms", 0) > _SLOW_WORKFLOW_MS:
            suggestions.append({
                "type": "performance-slow",
                "severity": "high" if stats["stats"]["avg_duration_ms"] > 30000 else "medium",
                "current": f"{stats['stats']['avg_duration_ms']:.0f}ms avg",
                "suggestion": "Consider parallelizing sequential steps or using faster agents",
                "affected_steps": self._find_bottleneck_steps(steps),
            })

        # Check for low success rate
        if stats["stats"].get("error_rate_pct", 0) > (100 - _LOW_SUCCESS_RATE_PCT):
            suggestions.append({
                "type": "reliability-low",
                "severity": "high",
                "current": f"{stats['stats']['error_rate_pct']:.1f}% failure rate",
                "suggestion": "Add error handling, retries, or fallback steps",
                "affected_steps": self._find_error_prone_steps(steps, stats["executions"]),
            })

        # Check for tool call chains that could be consolidated
        tool_calls = [s for s in steps if s.get("step_type") == "tool_call"]
        if len(tool_calls) >= 3:
            suggestions.append({
                "type": "redundant-tools",
                "severity": "medium",
                "current": f"{len(tool_calls)} sequential tool calls",
                "suggestion": "Combine related tool calls into a custom tool or use spawn_subagent",
                "affected_steps": [t.get("step_id") for t in tool_calls[:3]],
            })

        # Check for sequential steps that could be parallel
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
        """Find potential bottleneck steps based on type."""
        bottleneck_types = ["agent_call", "condition", "parallel"]
        return [s.get("step_id") for s in steps if s.get("step_type") in bottleneck_types]

    def _find_error_prone_steps(self, steps: list, executions: list) -> list[str]:
        """Find steps that frequently fail."""
        # Simple heuristic: agent_call steps are more prone to errors
        return [s.get("step_id") for s in steps if s.get("step_type") == "agent_call"]

    def find_global_patterns(self, limit: int = 20) -> list[dict[str, Any]]:
        """Find patterns across all workflows."""
        patterns = []

        # Pattern 1: Sequential tool calls
        stats = self.analyzer.get_workflow_stats(limit=500)
        if stats.get("executions"):
            # Count tool call sequences in history
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

        # Pattern 2: High latency template
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


# ── Suggestion Engine ─────────────────────────────────────────────

class SuggestionEngine:
    """Generates and manages workflow optimization suggestions."""

    def __init__(self):
        self.pattern_optimizer = PatternBasedOptimizer()

    def generate_suggestions(self, template_name: str | None = None) -> list[dict[str, Any]]:
        """Generate optimization suggestions."""
        suggestions = []

        # Get global patterns
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

        # Get template-specific suggestions if specified
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
        """Estimate the improvement from an optimization."""
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
        """Attempt to auto-apply suggestions that are marked as automated."""
        applied = []
        skipped = []

        for s in suggestions:
            if s.get("automated", False):
                applied.append(s["suggestion_id"])
            else:
                skipped.append(s["suggestion_id"])

        return {"applied": applied, "skipped": skipped, "total": len(suggestions)}


# ── Main Optimizer Engine ─────────────────────────────────────────

class WorkflowOptimizer:
    """Main engine combining all optimization components."""

    def __init__(self):
        self.analyzer = WorkflowPerformanceAnalyzer()
        self.pattern_optimizer = PatternBasedOptimizer()
        self.suggestion_engine = SuggestionEngine()

    def record_execution(self, result: dict[str, Any]) -> None:
        """Record a workflow execution for future optimization."""
        self.analyzer.record_execution(result)

    def get_statistics(self) -> dict[str, Any]:
        """Get overall optimization statistics."""
        return {
            "total_executions_analyzed": self._get_total_executions(),
            "slow_workflows": len(self.analyzer.get_slow_workflows()),
            "error_workflows": len(self.analyzer.get_error_patterns()),
            "global_patterns": self.pattern_optimizer.find_global_patterns()[:10],
        }

    def _get_total_executions(self) -> int:
        """Get total number of executions analyzed."""
        conn = sqlite3.connect(str(OPTIMIZER_DB))
        count = conn.execute("SELECT COUNT(*) FROM workflow_executions").fetchone()[0]
        conn.close()
        return count

    def get_workflow_stats(self, workflow_id: str) -> dict[str, Any]:
        """Get detailed statistics for a specific workflow."""
        return self.analyzer.get_workflow_stats(workflow_id)

    def analyze_workflow(self, workflow_id: str, workflow_name: str,
                         steps: list[dict]) -> list[dict[str, Any]]:
        """Analyze a specific workflow for optimization."""
        return self.pattern_optimizer.analyze_workflow(workflow_id, workflow_name, steps)

    def generate_suggestions(self, template_name: str | None = None) -> list[dict[str, Any]]:
        """Generate optimization suggestions."""
        return self.suggestion_engine.generate_suggestions(template_name)

    def optimize_workflow(self, workflow_id: str, steps: list[dict],
                          auto_apply: bool = False) -> dict[str, Any]:
        """Optimize a workflow and return the optimized version."""
        suggestions = self.analyzer.analyze_workflow(workflow_id, "optimized", steps)
        optimized = {
            "original_steps": steps,
            "suggestions": suggestions,
            "optimized_steps": steps,  # Default: no automatic changes
            "applied": [],
            "recommendations": [],
        }

        # If auto_apply is enabled, apply non-high-severity suggestions
        if auto_apply:
            for s in suggestions:
                if s.get("severity") != "high":
                    optimized["applied"].append(s["type"])
                    # Apply the optimization
                    optimized["steps"] = self._apply_optimization(
                        optimized["steps"], s["type"]
                    )

        return optimized

    def _apply_optimization(self, steps: list[dict], opt_type: str) -> list[dict]:
        """Apply an optimization to workflow steps."""
        if opt_type == "parallel-opportunity":
            # Convert first 2 sequential steps to parallel
            if len(steps) >= 2:
                parallel_step = {
                    "step_id": "parallel-1",
                    "step_type": "parallel",
                    "parallel_steps": [steps[0].get("step_id"), steps[1].get("step_id")],
                    "timeout_seconds": 120,
                }
                return [parallel_step] + steps[2:]

        return steps


# ── Module-level Singleton ────────────────────────────────────────

_optimizer: WorkflowOptimizer | None = None


def get_workflow_optimizer() -> WorkflowOptimizer:
    """Get the global WorkflowOptimizer singleton."""
    global _optimizer
    if _optimizer is None:
        _optimizer = WorkflowOptimizer()
    return _optimizer


# ─── Import fix for dataclasses ───────────────────────────────────

from dataclasses import dataclass

# Re-import after definition
import sqlite3
