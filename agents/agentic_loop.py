"""
Agentic Loop — Otonom görev zincirleme (Faz 11.1 + Faz 14.6).
Tool call zincirleme, iterasyon limiti, token/maliyet gardları, context window guard.
Faz 14.6: Context Transformer, Follow-up Config, Steering Message support.
Multi-parallel orchestration ile uyumlu: her agent execute() içinde bu gardlar uygulanır.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

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
        default_factory=lambda: int(os.getenv("AGENTIC_LOOP_MAX_ITERATIONS", "50"))
    )
    max_tokens_budget: int = field(
        default_factory=lambda: int(os.getenv("AGENTIC_LOOP_MAX_TOKENS_BUDGET", "500000"))
    )
    max_cost_usd: float = field(
        default_factory=lambda: float(os.getenv("AGENTIC_LOOP_MAX_COST_USD", "5.00"))
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


# ---------------------------------------------------------------------------
# Faz 14.6: Context Transformer — mesaj dizisini LLM'e göndermeden önce dönüştürme
# ---------------------------------------------------------------------------

# Transform function signature: (messages, config) -> messages
TransformFn = Callable[[list[dict[str, Any]], "LoopConfig"], list[dict[str, Any]]]


@dataclass
class ContextTransformer:
    """Pluggable context transformation pipeline.

    Transforms are applied in order before each LLM call.
    Built-in transforms: trim_redundant_tool_results, inject_summary.
    Agents can register custom transforms via `add_transform()`.
    """

    _transforms: list[TransformFn] = field(default_factory=list)

    def add_transform(self, fn: TransformFn) -> None:
        self._transforms.append(fn)

    def apply(self, messages: list[dict[str, Any]], config: LoopConfig | None = None) -> list[dict[str, Any]]:
        cfg = config or get_loop_config()
        result = messages
        for fn in self._transforms:
            result = fn(result, cfg)
        return result


def trim_redundant_tool_results(messages: list[dict[str, Any]], config: LoopConfig) -> list[dict[str, Any]]:
    """Trim long tool results in older messages to save context window space.

    Improved strategy (inspired by arxiv.org/abs/2510.06727):
    - Older tool results get progressively more aggressive trimming
    - Recent 6 messages kept intact, 6-12 messages trimmed to 500 chars,
      older messages trimmed to 200 chars
    - Web search results in old messages stripped to just URLs
    """
    if len(messages) <= 10:
        return messages
    trimmed = []
    recent_cutoff = len(messages) - 6   # keep last 6 intact
    medium_cutoff = len(messages) - 12  # medium trim zone

    for i, msg in enumerate(messages):
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            if i < medium_cutoff and len(content) > 200:
                # Aggressive trim for old tool results
                trimmed.append({**msg, "content": content[:200] + "\n...[trimmed — old context]"})
                continue
            elif i < recent_cutoff and len(content) > 500:
                # Medium trim
                trimmed.append({**msg, "content": content[:400] + "\n...[trimmed]"})
                continue
        trimmed.append(msg)
    return trimmed


def inject_context_summary(messages: list[dict[str, Any]], config: LoopConfig) -> list[dict[str, Any]]:
    """If message count exceeds threshold, inject a summary note after system messages."""
    if len(messages) <= config.max_messages_before_compress:
        return messages
    # Count tool interactions for summary
    tool_count = sum(1 for m in messages if m.get("role") == "tool")
    user_count = sum(1 for m in messages if m.get("role") == "user")
    summary = (
        f"[Context summary: {len(messages)} messages, {tool_count} tool calls, "
        f"{user_count} user messages. Focus on the latest task.]"
    )
    # Find insertion point (after system messages)
    insert_idx = 0
    for i, m in enumerate(messages):
        if m.get("role") == "system":
            insert_idx = i + 1
        else:
            break
    # Don't duplicate if already present
    if insert_idx < len(messages) and "[Context summary:" in (messages[insert_idx].get("content") or ""):
        return messages
    return messages[:insert_idx] + [{"role": "user", "content": summary}] + messages[insert_idx:]


def get_default_transformer() -> ContextTransformer:
    """Create a transformer with default built-in transforms."""
    ct = ContextTransformer()
    ct.add_transform(trim_redundant_tool_results)
    ct.add_transform(inject_context_summary)
    # pi-mom inspired: aggressive old tool result trimming
    try:
        from tools.context_compaction import trim_old_tool_results
        ct.add_transform(trim_old_tool_results)
    except ImportError:
        pass
    return ct


# ---------------------------------------------------------------------------
# Faz 14.6: Follow-up Config — agent durduğunda otomatik devam ettirme
# ---------------------------------------------------------------------------

# Patterns that indicate the agent wants to continue
_DEFAULT_CONTINUE_PATTERNS = [
    r"devam\s+ed",           # Turkish: devam edelim / edeceğim
    r"continue\s+with",
    r"next\s+step",
    r"I(?:'ll| will)\s+now",
    r"let me also",
    r"şimdi\s+de",
    r"ayrıca",
]


@dataclass
class FollowUpConfig:
    """Configuration for automatic follow-up messages when agent signals continuation."""
    enabled: bool = field(
        default_factory=lambda: os.getenv("AGENTIC_FOLLOWUP_ENABLED", "true").lower() == "true"
    )
    max_follow_ups: int = field(
        default_factory=lambda: int(os.getenv("AGENTIC_MAX_FOLLOWUPS", "5"))
    )
    trigger_patterns: list[str] = field(default_factory=lambda: list(_DEFAULT_CONTINUE_PATTERNS))
    follow_up_message: str = "Devam et — önceki yanıtını tamamla."

    def should_follow_up(self, response_text: str) -> bool:
        """Check if the response text indicates the agent wants to continue."""
        if not self.enabled:
            return False
        text = response_text.strip()
        # If response ends abruptly (mid-sentence) — likely needs continuation
        if text and not text[-1] in ".!?…\"')\u200b":
            return True
        # Check trigger patterns
        last_chunk = text[-200:] if len(text) > 200 else text
        for pattern in self.trigger_patterns:
            if re.search(pattern, last_chunk, re.IGNORECASE):
                return True
        return False


def get_followup_config() -> FollowUpConfig:
    return FollowUpConfig()


# ---------------------------------------------------------------------------
# Faz 14.6: Steering Queue — kullanıcının agent çalışırken araya girmesi
# ---------------------------------------------------------------------------

class SteeringQueue:
    """Thread-safe queue for injecting user steering messages into a running agent loop.

    Usage:
        - Backend (chat_ws.py) pushes steering messages via `push()`
        - Agent execute() loop checks `pop()` each iteration
        - Steering messages are injected as high-priority user messages
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    def push(self, message: str) -> None:
        """Push a steering message (non-blocking)."""
        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            pass  # drop if somehow full

    def pop(self) -> str | None:
        """Pop a steering message if available (non-blocking). Returns None if empty."""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def has_messages(self) -> bool:
        return not self._queue.empty()
