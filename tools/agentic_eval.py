"""
Agentic Evaluation — Evaluator-Optimizer patterns for agent self-improvement.

Implements three core patterns:
1. Basic Reflection: Agent evaluates and improves its own output
2. Evaluator-Optimizer: Separate generation and evaluation components
3. Rubric-Based Scoring: Weighted multi-dimensional evaluation

Integrates with existing reflexion.py and agent_eval.py infrastructure.
Adds convergence detection, iteration history, and pipeline-specific rubrics.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Rubric Definitions ───────────────────────────────────────────

RUBRICS: dict[str, dict[str, dict[str, float]]] = {
    "general": {
        "accuracy": {"weight": 0.25},
        "completeness": {"weight": 0.25},
        "clarity": {"weight": 0.20},
        "actionability": {"weight": 0.15},
        "coherence": {"weight": 0.15},
    },
    "code": {
        "correctness": {"weight": 0.30},
        "completeness": {"weight": 0.20},
        "readability": {"weight": 0.15},
        "efficiency": {"weight": 0.15},
        "error_handling": {"weight": 0.10},
        "documentation": {"weight": 0.10},
    },
    "analysis": {
        "accuracy": {"weight": 0.25},
        "depth": {"weight": 0.25},
        "evidence": {"weight": 0.20},
        "clarity": {"weight": 0.15},
        "actionability": {"weight": 0.15},
    },
    "prd": {
        "completeness": {"weight": 0.25},
        "clarity": {"weight": 0.20},
        "feasibility": {"weight": 0.20},
        "user_focus": {"weight": 0.15},
        "measurability": {"weight": 0.10},
        "prioritization": {"weight": 0.10},
    },
    "architecture": {
        "scalability": {"weight": 0.20},
        "maintainability": {"weight": 0.20},
        "correctness": {"weight": 0.20},
        "completeness": {"weight": 0.15},
        "security": {"weight": 0.15},
        "cost_efficiency": {"weight": 0.10},
    },
}


def get_rubric(task_type: str) -> dict[str, dict[str, float]]:
    """Get evaluation rubric for a task type. Falls back to 'general'."""
    return RUBRICS.get(task_type, RUBRICS["general"])


def detect_eval_task_type(query: str) -> str:
    """Detect task type for rubric selection from query text."""
    q = (query or "").lower()
    if any(k in q for k in ("kod", "code", "function", "class", "implement", "fix", "bug")):
        return "code"
    if any(k in q for k in ("prd", "product requirement", "gereksinim", "user story")):
        return "prd"
    if any(k in q for k in ("architecture", "mimari", "system design", "tech stack")):
        return "architecture"
    if any(k in q for k in ("analiz", "analysis", "report", "rapor", "research")):
        return "analysis"
    return "general"


# ── Convergence Detection ────────────────────────────────────────

@dataclass
class ConvergenceTracker:
    """Track score history and detect convergence/stagnation.

    Convergence is detected when:
    - Score improvement drops below min_delta for N consecutive rounds
    - Score oscillates (goes up then down then up)
    - Maximum iterations reached
    """
    min_delta: float = 0.05
    stagnation_limit: int = 2
    _history: list[float] = field(default_factory=list)

    def record(self, score: float) -> None:
        self._history.append(score)

    @property
    def best_score(self) -> float:
        return max(self._history) if self._history else 0.0

    @property
    def latest_score(self) -> float:
        return self._history[-1] if self._history else 0.0

    @property
    def round_count(self) -> int:
        return len(self._history)

    def is_converged(self) -> bool:
        """Check if scores have converged (no meaningful improvement)."""
        if len(self._history) < 2:
            return False

        # Check stagnation: last N rounds had < min_delta improvement
        stagnation_count = 0
        for i in range(1, len(self._history)):
            delta = self._history[i] - self._history[i - 1]
            if delta < self.min_delta:
                stagnation_count += 1
            else:
                stagnation_count = 0

        if stagnation_count >= self.stagnation_limit:
            return True

        # Check oscillation: score went up, then down, then up
        if len(self._history) >= 3:
            deltas = [
                self._history[i] - self._history[i - 1]
                for i in range(1, len(self._history))
            ]
            sign_changes = sum(
                1 for i in range(1, len(deltas))
                if (deltas[i] > 0) != (deltas[i - 1] > 0)
            )
            if sign_changes >= 2:
                return True

        return False

    def get_summary(self) -> dict[str, Any]:
        return {
            "rounds": self.round_count,
            "best_score": self.best_score,
            "latest_score": self.latest_score,
            "converged": self.is_converged(),
            "history": list(self._history),
        }


# ── Iteration History ────────────────────────────────────────────

@dataclass
class EvalIteration:
    """Single evaluation iteration record."""
    round_num: int
    score: float
    dimensions: dict[str, float]
    weaknesses: list[str]
    improvements: list[str]
    approved: bool
    timestamp_ms: float


@dataclass
class EvalHistory:
    """Full evaluation history for debugging and analysis."""
    task_type: str
    rubric_used: str
    iterations: list[EvalIteration] = field(default_factory=list)
    final_score: float = 0.0
    total_duration_ms: float = 0.0

    def add_iteration(self, iteration: EvalIteration) -> None:
        self.iterations.append(iteration)
        self.final_score = max(self.final_score, iteration.score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "rubric_used": self.rubric_used,
            "iterations": [
                {
                    "round": it.round_num,
                    "score": it.score,
                    "dimensions": it.dimensions,
                    "weaknesses": it.weaknesses,
                    "approved": it.approved,
                }
                for it in self.iterations
            ],
            "final_score": self.final_score,
            "total_rounds": len(self.iterations),
            "total_duration_ms": self.total_duration_ms,
        }


# ── Rubric-Based Evaluation ─────────────────────────────────────

def build_rubric_eval_prompt(
    output: str,
    task: str,
    rubric: dict[str, dict[str, float]],
) -> str:
    """Build evaluation prompt with rubric dimensions and weights."""
    dimensions = list(rubric.keys())
    dim_list = "\n".join(
        f"  - {dim}: weight={info['weight']:.0%}" for dim, info in rubric.items()
    )
    return (
        f"Evaluate this output against the following rubric.\n\n"
        f"TASK: {task[:500]}\n\n"
        f"OUTPUT:\n{output[:3000]}\n\n"
        f"RUBRIC DIMENSIONS:\n{dim_list}\n\n"
        f"Rate each dimension 1-5 and provide overall assessment.\n"
        f"Return ONLY JSON:\n"
        '{{"dimensions": {' + ", ".join(f'"{d}": N' for d in dimensions) + '}, '
        f'"overall_score": N, "approved": boolean, '
        f'"weaknesses": ["..."], "improvements": ["..."]}}'
    )


def compute_weighted_score(
    dimension_scores: dict[str, float],
    rubric: dict[str, dict[str, float]],
) -> float:
    """Compute weighted score from dimension scores and rubric weights."""
    total = 0.0
    weight_sum = 0.0
    for dim, info in rubric.items():
        score = dimension_scores.get(dim, 3.0)  # default neutral
        weight = info.get("weight", 0.0)
        total += score * weight
        weight_sum += weight

    if weight_sum == 0:
        return 0.0
    # Normalize to 0-1 scale (scores are 1-5)
    return (total / weight_sum) / 5.0


# ── Evaluator-Optimizer Pattern ──────────────────────────────────

async def evaluator_optimizer_loop(
    agent,
    task: str,
    output: str,
    task_type: str | None = None,
    max_iterations: int = 3,
    score_threshold: float = 0.8,
    min_delta: float = 0.05,
) -> tuple[str, EvalHistory]:
    """Run evaluator-optimizer loop with convergence detection.

    This is the main entry point for agentic evaluation.
    Uses rubric-based scoring, convergence tracking, and iteration history.

    Args:
        agent: Agent instance with call_llm() method
        task: Original task/question
        output: Initial output to evaluate
        task_type: Override task type detection
        max_iterations: Max refinement rounds
        score_threshold: Score to consider "good enough" (0-1)
        min_delta: Minimum improvement to continue

    Returns:
        Tuple of (best_output, evaluation_history)
    """
    t0 = time.monotonic()
    effective_type = task_type or detect_eval_task_type(task)
    rubric = get_rubric(effective_type)
    tracker = ConvergenceTracker(min_delta=min_delta)
    history = EvalHistory(task_type=effective_type, rubric_used=effective_type)

    best_output = output
    best_score = 0.0

    for round_num in range(1, max_iterations + 1):
        # Evaluate
        eval_prompt = build_rubric_eval_prompt(output, task, rubric)
        try:
            eval_result = await agent.call_llm([{"role": "user", "content": eval_prompt}])
            eval_text = _extract_content(eval_result)
            parsed = _parse_eval_json(eval_text)
        except Exception as e:
            logger.warning(f"Agentic eval round {round_num} failed: {e}")
            break

        if not parsed:
            logger.warning(f"Agentic eval round {round_num}: parse failed")
            break

        dimensions = parsed.get("dimensions", {})
        score = compute_weighted_score(dimensions, rubric)
        approved = parsed.get("approved", False)
        weaknesses = parsed.get("weaknesses", [])
        improvements = parsed.get("improvements", [])

        # Record
        iteration = EvalIteration(
            round_num=round_num,
            score=score,
            dimensions=dimensions,
            weaknesses=weaknesses,
            improvements=improvements,
            approved=approved or score >= score_threshold,
            timestamp_ms=(time.monotonic() - t0) * 1000,
        )
        history.add_iteration(iteration)
        tracker.record(score)

        if score > best_score:
            best_score = score
            best_output = output

        # Check exit conditions
        if approved or score >= score_threshold:
            logger.info(f"Agentic eval: approved at round {round_num} (score={score:.2f})")
            break

        if tracker.is_converged():
            logger.info(f"Agentic eval: converged at round {round_num}")
            break

        # Optimize
        weakness_text = "\n".join(f"- {w}" for w in weaknesses) if weaknesses else "- General improvement needed"
        improve_text = "\n".join(f"- {i}" for i in improvements) if improvements else "- Improve clarity and completeness"

        refine_prompt = (
            f"IMPROVE your output based on this feedback.\n\n"
            f"Original task: {task[:500]}\n\n"
            f"Current output:\n{output[:3000]}\n\n"
            f"Weaknesses:\n{weakness_text}\n\n"
            f"Suggested improvements:\n{improve_text}\n\n"
            f"Write an improved version. Keep correct parts, fix weak parts."
        )

        try:
            improve_result = await agent.call_llm([{"role": "user", "content": refine_prompt}])
            output = _extract_content(improve_result)
        except Exception as e:
            logger.warning(f"Agentic eval optimize round {round_num} failed: {e}")
            break

    history.total_duration_ms = (time.monotonic() - t0) * 1000
    return best_output, history


# ── Helpers ──────────────────────────────────────────────────────

def _extract_content(result: Any) -> str:
    """Extract text content from LLM result."""
    if isinstance(result, dict):
        content = result.get("content")
        return content if isinstance(content, str) else str(content or "")
    return str(result or "")


def _parse_eval_json(text: str) -> dict[str, Any] | None:
    """Parse evaluation JSON from LLM output."""
    if not text:
        return None
    text = text.strip()

    # Direct parse
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, TypeError):
        pass

    # Extract from markdown fence
    import re
    fences = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    for block in fences:
        try:
            obj = json.loads(block)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, TypeError):
            continue

    # Balanced brace extraction
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start:end + 1])
            return obj if isinstance(obj, dict) else None
        except (json.JSONDecodeError, TypeError):
            pass

    return None
