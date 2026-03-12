"""
Reflexion — Agent self-evaluation and improvement loop.
Inspired by Langgraph Reflexion Agent pattern.

Agent evaluates its own output, scores quality, identifies weaknesses,
and iteratively improves. Stores reflection insights in memory.
"""

from __future__ import annotations

import json
import logging
import re
import ast
from typing import Any

logger = logging.getLogger(__name__)


# ── Reflection Prompts ───────────────────────────────────────────

SELF_EVALUATE_PROMPT = (
    "SELF-EVALUATION: Rate your previous response on these criteria (1-5 each):\n\n"
    "1. ACCURACY: Are facts correct? Any hallucinations?\n"
    "2. COMPLETENESS: Did you address all parts of the question?\n"
    "3. CLARITY: Is the response well-structured and easy to understand?\n"
    "4. ACTIONABILITY: Can the user act on this immediately?\n"
    "5. DEPTH: Is the analysis sufficiently thorough?\n"
    "6. COHERENCE: Does the response flow logically without contradictions?\n\n"
    "Previous response to evaluate:\n{response}\n\n"
    "Original question: {question}\n\n"
    "Output JSON: {{\"scores\": {{\"accuracy\": N, \"completeness\": N, \"clarity\": N, "
    "\"actionability\": N, \"depth\": N, \"coherence\": N}}, \"total\": N, \"weaknesses\": [\"...\"], "
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
    """Parse self-evaluation JSON from agent response.

    Handles raw JSON, markdown code fences, and prose-wrapped JSON snippets.
    """
    if not isinstance(eval_text, str) or not eval_text.strip():
        return None

    text = eval_text.strip()

    # 1) Direct JSON parse first
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError):
        pass

    # 1.5) Python-dict-like payloads (single quotes, True/False) are common in LLM output.
    try:
        parsed = ast.literal_eval(text)
        return parsed if isinstance(parsed, dict) else None
    except (ValueError, SyntaxError):
        pass

    # 2) Markdown code fence blocks (```json ... ``` or ``` ... ```)
    fence_blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    for block in fence_blocks:
        try:
            parsed = json.loads(block)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            try:
                parsed = ast.literal_eval(block)
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, SyntaxError):
                continue

    # 3) Balanced JSON object extraction (best-effort)
    starts = [m.start() for m in re.finditer(r"\{", text)]
    for start in starts:
        depth = 0
        for idx in range(start, len(text)):
            char = text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : idx + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict) and "scores" in parsed:
                            return parsed
                    except (json.JSONDecodeError, TypeError):
                        try:
                            parsed = ast.literal_eval(candidate)
                            if isinstance(parsed, dict) and "scores" in parsed:
                                return parsed
                        except (ValueError, SyntaxError):
                            break

    return None


def _fallback_evaluation(reason: str) -> dict[str, Any]:
    """Safe fallback evaluation to prevent reflexion flow from crashing."""
    return {
        "scores": {
            "accuracy": 5,
            "completeness": 5,
            "clarity": 5,
            "actionability": 5,
            "depth": 5,
            "coherence": 5,
        },
        "total": 30,
        "weaknesses": [f"evaluation_parse_failed:{reason}"],
        "improvements": [],
        "fallback_used": True,
    }


def _is_valid_evaluation(evaluation: Any) -> bool:
    """Minimal structural validation for parsed reflexion payload."""
    if not isinstance(evaluation, dict):
        return False
    scores = evaluation.get("scores")
    if not isinstance(scores, dict) or not scores:
        return False
    numeric_scores = [v for v in scores.values() if isinstance(v, (int, float))]
    return bool(numeric_scores)


def _extract_llm_content(result: Any) -> str:
    """Extract content from BaseAgent.call_llm() result safely."""
    if isinstance(result, dict):
        content = result.get("content")
        return content if isinstance(content, str) else str(content or "")
    return str(result or "")


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
        
        # Normalize to 0-1: agentic_eval already uses 0-1 scale, reflexion uses 0-5
        if evaluation.get("agentic_eval"):
            normalized_score = round(avg_score, 2)
        else:
            normalized_score = round(avg_score / 5, 2)
        
        # Add new result
        results.append({
            "agent_role": agent_role,
            "score": normalized_score,
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
    except Exception as e:
        logger.warning(f"Failed to save reflexion insight: {e}")


async def evaluate_and_improve(
    agent,
    question: str,
    response: str,
    threshold: float = 3.5,
    max_iterations: int = 1,
) -> tuple[str, dict[str, Any] | None]:
    """Evaluate response and optionally improve it.

    When max_iterations > 1 and agentic_eval is available, delegates to the
    evaluator-optimizer loop for rubric-based multi-dimensional scoring with
    convergence detection.  Falls back to the simple reflexion flow otherwise.

    Args:
        agent: The agent instance (has call_llm method)
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

    # Enhanced path: use evaluator_optimizer_loop for multi-iteration quality-critical tasks
    if max_iterations > 1 and config.REFLEXION_AUTO_IMPROVE:
        try:
            from tools.agentic_eval import evaluator_optimizer_loop

            # Convert 1-5 threshold to 0-1 scale for agentic_eval
            score_threshold_01 = min(1.0, threshold / 5.0)
            best_output, eval_history = await evaluator_optimizer_loop(
                agent=agent,
                task=question,
                output=response,
                max_iterations=max_iterations,
                score_threshold=score_threshold_01,
            )
            # Build evaluation dict compatible with reflexion format
            history_dict = eval_history.to_dict()
            evaluation: dict[str, Any] = {
                "scores": {},
                "total": int(eval_history.final_score * 30),  # scale to /30
                "weaknesses": [],
                "improvements": [],
                "agentic_eval": True,
                "history": history_dict,
            }
            if eval_history.iterations:
                last_iter = eval_history.iterations[-1]
                evaluation["weaknesses"] = last_iter.weaknesses
                evaluation["improvements"] = last_iter.improvements
                evaluation["scores"] = {
                    dim: int(score) for dim, score in last_iter.dimensions.items()
                }

            save_reflection_result(
                agent.role.value, question, evaluation, improved=len(eval_history.iterations) > 1
            )
            return best_output, evaluation
        except Exception as e:
            logger.debug(f"Agentic eval enhanced path failed, falling back: {e}")

    # Standard reflexion flow
    iteration = 0
    current_response = response
    evaluation = None

    while iteration < max_iterations:
        # Build evaluation prompt
        eval_prompt = build_evaluation_prompt(question, current_response)

        try:
            # Call LLM for evaluation
            eval_result = await agent.call_llm([{"role": "user", "content": eval_prompt}])
            eval_response = _extract_llm_content(eval_result)
            parsed_evaluation = parse_evaluation(eval_response)

            if not _is_valid_evaluation(parsed_evaluation):
                logger.warning(
                    "Reflexion evaluation parse/validation failed; using safe fallback",
                    extra={
                        "agent_role": getattr(agent.role, "value", str(agent.role)),
                        "eval_excerpt": eval_response[:200],
                    },
                )
                evaluation = _fallback_evaluation("invalid_or_incomplete_payload")
                break

            # Pyright/Pylance type narrowing: keep a guaranteed dict after validation.
            if parsed_evaluation is None:
                evaluation = _fallback_evaluation("none_payload")
                break

            current_evaluation: dict[str, Any] = parsed_evaluation
            evaluation = current_evaluation

            # Check if improvement needed
            if not should_improve(current_evaluation, threshold):
                logger.info(f"Reflexion: Response passed (avg score >= {threshold})")
                break

            if not config.REFLEXION_AUTO_IMPROVE:
                logger.info("Reflexion: Score below threshold but auto-improve disabled")
                break

            # Build improvement prompt
            weaknesses = current_evaluation.get("weaknesses", [])
            improvements = current_evaluation.get("improvements", [])

            improve_prompt = build_improvement_prompt(
                question=question,
                response=current_response,
                weaknesses=weaknesses,
                improvements=improvements,
            )

            # Get improved response
            improve_result = await agent.call_llm([{"role": "user", "content": improve_prompt}])
            current_response = _extract_llm_content(improve_result)
            iteration += 1

            logger.info(f"Reflexion: Improved response (iteration {iteration})")

            # Save insight
            save_reflection_insight(question, current_evaluation, improved=True)

            # Save result for UI
            save_reflection_result(agent.role.value, question, current_evaluation, improved=True)

        except Exception as e:
            logger.error(f"Reflexion error: {e}")
            evaluation = evaluation or _fallback_evaluation("runtime_error")
            break

    # Save final evaluation result for UI (even if no improvement)
    if evaluation:
        save_reflection_result(agent.role.value, question, evaluation, improved=iteration > 0)

    return current_response, evaluation
