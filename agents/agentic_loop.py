"""
Agentic Loop — Otonom görev zincirleme (Faz 11.1).
Tool call zincirleme, iterasyon limiti, token/maliyet gardları, context window guard.
Multi-parallel orchestration ile uyumlu: her agent execute() içinde bu gardlar uygulanır.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Cost per 1K tokens (USD) — model id → rate
COST_PER_1K: dict[str, float] = {
    "qwen/qwen3-next-80b-a3b-instruct": 0.002,
    "minimaxai/minimax-m2.1": 0.003,
    "stepfun-ai/step-3.5-flash": 0.001,
    "z-ai/glm4.7": 0.002,
    "nvidia/nemotron-3-nano-30b-a3b": 0.002,
    "deepseek-chat": 0.001,
}
DEFAULT_COST_PER_1K = 0.002


@dataclass
class LoopStatus:
    """Result of a guard check."""
    ok: bool = True
    reason: str | None = None  # e.g. "iteration_limit", "budget_exceeded"


@dataclass
class LoopConfig:
    """Agentic loop limits — env veya config'den okunabilir."""
    max_iterations: int = field(
        default_factory=lambda: int(os.getenv("AGENTIC_LOOP_MAX_ITERATIONS", "12"))
    )
    max_tokens_budget: int = field(
        default_factory=lambda: int(os.getenv("AGENTIC_LOOP_MAX_TOKENS_BUDGET", "80000"))
    )
    max_cost_usd: float = field(
        default_factory=lambda: float(os.getenv("AGENTIC_LOOP_MAX_COST_USD", "0.60"))
    )
    context_compress_threshold: float = field(
        default_factory=lambda: float(os.getenv("AGENTIC_LOOP_CONTEXT_THRESHOLD", "0.75"))
    )
    max_messages_before_compress: int = field(
        default_factory=lambda: int(os.getenv("AGENTIC_LOOP_MAX_MESSAGES", "28"))
    )


def get_loop_config() -> LoopConfig:
    return LoopConfig()


def cost_per_1k_for_model(model_id: str) -> float:
    """USD per 1K tokens for a given model id."""
    for key, rate in COST_PER_1K.items():
        if key in (model_id or ""):
            return rate
    return DEFAULT_COST_PER_1K


def check_guards(
    step: int,
    cumulative_tokens: int,
    cumulative_cost_usd: float,
    config: LoopConfig | None = None,
) -> LoopStatus:
    """Check iteration, token budget, and cost. Return status with reason if guard triggered."""
    cfg = config or get_loop_config()
    if step >= cfg.max_iterations:
        return LoopStatus(ok=False, reason="iteration_limit")
    if cumulative_tokens >= cfg.max_tokens_budget:
        return LoopStatus(ok=False, reason="budget_exceeded")
    if cumulative_cost_usd >= cfg.max_cost_usd:
        return LoopStatus(ok=False, reason="cost_exceeded")
    return LoopStatus(ok=True)


def compress_messages_if_needed(
    messages: list[dict[str, Any]],
    config: LoopConfig | None = None,
) -> list[dict[str, Any]]:
    """
    Context Window Guard: if too many messages, keep system + last N and a summary placeholder.
    Does not call LLM; just truncates to stay under limit. Orchestrator/agent can inject a short summary later.
    """
    cfg = config or get_loop_config()
    if len(messages) <= cfg.max_messages_before_compress:
        return messages
    # Keep first (system) and last messages
    system_msgs = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    keep = rest[-(cfg.max_messages_before_compress - 2):]  # leave room for summary line
    summary_note = {
        "role": "user",
        "content": "[Context truncated to stay within limits. Earlier conversation was summarized.]",
    }
    return system_msgs + [summary_note] + keep
