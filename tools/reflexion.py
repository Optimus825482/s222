"""
Reflexion — Agent self-evaluation and improvement loop.
Inspired by Langgraph Reflexion Agent pattern.

Agent evaluates its own output, scores quality, identifies weaknesses,
and iteratively improves. Stores reflection insights in memory.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Reflection Prompts ───────────────────────────────────────────

SELF_EVALUATE_PROMPT = (
    "SELF-EVALUATION: Rate your previous response on these criteria (1-5 each):\n\n"
    "1. ACCURACY: Are facts correct? Any hallucinations?\n"
    "2. COMPLETENESS: Did you address all parts of the question?\n"
    "3. CLARITY: Is the response well-structured and easy to understand?\n"
    "4. ACTIONABILITY: Can the user act on this immediately?\n"
    "5. DEPTH: Is the analysis sufficiently thorough?\n\n"
    "Previous response to evaluate:\n{response}\n\n"
    "Original question: {question}\n\n"
    "Output JSON: {{\"scores\": {{\"accuracy\": N, \"completeness\": N, \"clarity\": N, "
    "\"actionability\": N, \"depth\": N}}, \"total\": N, \"weaknesses\": [\"...\"], "
    "\"improvements\": [\"...\"]}}"
)

IMPROVE_PROMPT = (
    "REFLEXION IMPROVEMENT: Your previous response had these weaknesses:\n"
    "{weaknesses}\n\n"
    "Suggested improvements:\n{improvements}\n\n"
    "Original question: {question}\n\n"
    "Previous response:\n{response}\n\n"
    "Write an IMPROVED response that addresses ALL weaknesses. "
    "Be specific about what you changed and why."
)


def build_evaluation_prompt(question: str, response: str) -> str:
    """Build self-evaluation prompt for an agent."""
    return SELF_EVALUATE_PROMPT.format(
        response=response[:3000],
        question=question[:500],
    )


def build_improvement_prompt(
    question: str,
    response: str,
    weaknesses: list[str],
    improvements: list[str],
) -> str:
    """Build improvement prompt based on self-evaluation."""
    return IMPROVE_PROMPT.format(
        question=question[:500],
        response=response[:3000],
        weaknesses="\n".join(f"- {w}" for w in weaknesses),
        improvements="\n".join(f"- {i}" for i in improvements),
    )


def parse_evaluation(eval_text: str) -> dict[str, Any] | None:
    """Parse self-evaluation JSON from agent response."""
    try:
        # Try to find JSON in the response
        import re
        json_match = re.search(r'\{[^{}]*"scores"[^{}]*\{[^{}]*\}[^{}]*\}', eval_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        # Try parsing the whole thing
        return json.loads(eval_text)
    except (json.JSONDecodeError, AttributeError):
        return None


def should_improve(evaluation: dict[str, Any], threshold: float = 3.5) -> bool:
    """Determine if response needs improvement based on scores."""
    scores = evaluation.get("scores", {})
    if not scores:
        return False

    values = [v for v in scores.values() if isinstance(v, (int, float))]
    if not values:
        return False

    avg = sum(values) / len(values)
    return avg < threshold


def save_reflection_insight(question: str, evaluation: dict, improved: bool) -> None:
    """Save reflection insight to memory for future learning."""
    try:
        from tools.memory import save_memory

        scores = evaluation.get("scores", {})
        weaknesses = evaluation.get("weaknesses", [])

        content = (
            f"Reflexion insight — Question type: {question[:100]}\n"
            f"Scores: {json.dumps(scores)}\n"
            f"Weaknesses found: {', '.join(weaknesses[:3])}\n"
            f"Improved: {improved}"
        )

        save_memory(
            content=content,
            category="pattern",
            tags=["reflexion", "self-improvement"] + weaknesses[:2],
            source_agent="reflexion",
        )
    except Exception:
        pass  # Silent — never break execution
