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


def save_reflection_result(agent_role: str, question: str, evaluation: dict, improved: bool) -> None:
    """Save reflexion result to JSON file for UI display."""
    import os
    from pathlib import Path
    from datetime import datetime, timezone
    
    try:
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        results_file = data_dir / "reflexion_results.json"
        
        # Load existing results
        results = []
        if results_file.exists():
            try:
                results = json.loads(results_file.read_text()).get("results", [])
            except Exception:
                results = []
        
        # Calculate score
        scores = evaluation.get("scores", {})
        values = [v for v in scores.values() if isinstance(v, (int, float))]
        avg_score = sum(values) / len(values) if values else 0
        
        # Add new result
        results.append({
            "agent_role": agent_role,
            "score": round(avg_score / 5, 2),  # Normalize to 0-1
            "issues": evaluation.get("weaknesses", [])[:3],
            "improvements": evaluation.get("improvements", [])[:3],
            "improved": improved,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Keep last 100 results
        results = results[-100:]
        
        # Save
        results_file.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2))
        
    except Exception as e:
        logger.warning(f"Failed to save reflexion result: {e}")


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


async def evaluate_and_improve(
    agent,
    question: str,
    response: str,
    threshold: float = 3.5,
    max_iterations: int = 1,
) -> tuple[str, dict[str, Any] | None]:
    """Evaluate response and optionally improve it.
    
    Args:
        agent: The agent instance (has _call_llm method)
        question: Original question/input
        response: Agent's response to evaluate
        threshold: Score threshold for improvement (1-5 scale)
        max_iterations: Max improvement iterations
        
    Returns:
        Tuple of (final_response, evaluation_dict or None)
    """
    import config
    
    if not config.REFLEXION_ENABLED:
        return response, None
    
    # Check if this agent should use reflexion
    if config.REFLEXION_AGENTS and agent.role.value not in config.REFLEXION_AGENTS:
        return response, None
    
    iteration = 0
    current_response = response
    evaluation = None
    
    while iteration < max_iterations:
        # Build evaluation prompt
        eval_prompt = build_evaluation_prompt(question, current_response)
        
        try:
            # Call LLM for evaluation
            eval_response = await agent._call_llm([{"role": "user", "content": eval_prompt}])
            evaluation = parse_evaluation(eval_response)
            
            if not evaluation:
                logger.warning("Failed to parse evaluation JSON")
                break
            
            # Check if improvement needed
            if not should_improve(evaluation, threshold):
                logger.info(f"Reflexion: Response passed (avg score >= {threshold})")
                break
            
            if not config.REFLEXION_AUTO_IMPROVE:
                logger.info(f"Reflexion: Score below threshold but auto-improve disabled")
                break
            
            # Build improvement prompt
            weaknesses = evaluation.get("weaknesses", [])
            improvements = evaluation.get("improvements", [])
            
            improve_prompt = build_improvement_prompt(
                question=question,
                response=current_response,
                weaknesses=weaknesses,
                improvements=improvements,
            )
            
            # Get improved response
            current_response = await agent._call_llm([{"role": "user", "content": improve_prompt}])
            iteration += 1
            
            logger.info(f"Reflexion: Improved response (iteration {iteration})")
            
            # Save insight
            save_reflection_insight(question, evaluation, improved=True)
            
            # Save result for UI
            save_reflection_result(agent.role.value, question, evaluation, improved=True)
            
        except Exception as e:
            logger.error(f"Reflexion error: {e}")
            break
    
    # Save final evaluation result for UI (even if no improvement)
    if evaluation:
        save_reflection_result(agent.role.value, question, evaluation, improved=iteration > 0)
    
    return current_response, evaluation
