"""
Context Compaction — Inspired by pi-mom's log.jsonl + context.jsonl pattern.

Mom keeps full history in log.jsonl and a compacted working context in context.jsonl.
When context exceeds the LLM window, older messages are summarized.

Our adaptation:
- Thread events = log.jsonl (full history, never truncated)
- LLM messages = context.jsonl (working context, compacted when needed)
- Agents can grep thread events for older history (like mom greps log.jsonl)
- Compaction produces a summary event, keeping recent messages intact

Integrates with existing agentic_loop.py ContextTransformer pipeline.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────

# When context exceeds this many messages, trigger compaction
COMPACTION_THRESHOLD = 30

# Keep this many recent messages intact after compaction
KEEP_RECENT = 12

# Max chars for a single tool result in compacted context
MAX_TOOL_RESULT_CHARS = 600

# Summary template for compacted context
COMPACTION_SUMMARY_TEMPLATE = """[CONTEXT COMPACTED — {msg_count} messages summarized]

## Conversation Summary
{summary}

## Key Decisions
{decisions}

## Active Context
- Tools used: {tools_used}
- Agents involved: {agents_involved}
- Last topic: {last_topic}
"""


# ── Compaction Engine ────────────────────────────────────────────

def should_compact(messages: list[dict[str, Any]]) -> bool:
    """Check if context needs compaction."""
    non_system = [m for m in messages if m.get("role") != "system"]
    return len(non_system) > COMPACTION_THRESHOLD


def compact_context(
    messages: list[dict[str, Any]],
    keep_recent: int = KEEP_RECENT,
) -> list[dict[str, Any]]:
    """
    Compact message context, keeping system + recent messages.
    Older messages are replaced with a structured summary.

    This is a deterministic compaction (no LLM call).
    For LLM-powered summarization, use compact_context_with_llm().
    """
    if not should_compact(messages):
        return messages

    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    if len(non_system) <= keep_recent:
        return messages

    # Split into old (to summarize) and recent (to keep)
    old_msgs = non_system[:-keep_recent]
    recent_msgs = non_system[-keep_recent:]

    # Extract key info from old messages
    summary_parts = _extract_summary(old_msgs)

    summary_msg = {
        "role": "user",
        "content": COMPACTION_SUMMARY_TEMPLATE.format(**summary_parts),
    }

    logger.info(
        "[Compaction] Compacted %d messages → summary + %d recent",
        len(old_msgs), len(recent_msgs),
    )

    return system_msgs + [summary_msg] + recent_msgs


def _extract_summary(messages: list[dict[str, Any]]) -> dict[str, str]:
    """Extract structured summary from old messages."""
    user_messages = []
    assistant_messages = []
    tool_names = set()
    agents = set()
    topics = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user" and content:
            user_messages.append(content[:200])
            # Extract topic from first sentence
            first_sentence = content.split(".")[0].split("?")[0][:100]
            if first_sentence:
                topics.append(first_sentence)

        elif role == "assistant" and content:
            assistant_messages.append(content[:200])
            # Check for agent mentions
            for agent in ["orchestrator", "thinker", "researcher", "reasoner", "speed", "critic"]:
                if agent in content.lower():
                    agents.add(agent)

        elif role == "tool":
            name = msg.get("name", "unknown")
            tool_names.add(name)

        # Check for tool_calls in assistant messages
        tool_calls = msg.get("tool_calls", [])
        for tc in tool_calls:
            fn = tc.get("function", {})
            tool_names.add(fn.get("name", "unknown"))

    # Build summary
    summary_lines = []
    for i, um in enumerate(user_messages[:5]):
        summary_lines.append(f"- User asked: {um}")
    if len(user_messages) > 5:
        summary_lines.append(f"- ... and {len(user_messages) - 5} more exchanges")

    # Extract decisions from assistant responses
    decisions = []
    for am in assistant_messages[:3]:
        # Look for decision-like patterns
        for pattern in [r"I'll use", r"decided to", r"choosing", r"selected", r"kullanacağım", r"seçtim"]:
            match = re.search(pattern + r"[^.]*\.", am, re.IGNORECASE)
            if match:
                decisions.append(f"- {match.group(0)}")
                break

    return {
        "msg_count": str(len(messages)),
        "summary": "\n".join(summary_lines) if summary_lines else "General conversation",
        "decisions": "\n".join(decisions) if decisions else "No major decisions recorded",
        "tools_used": ", ".join(sorted(tool_names)) if tool_names else "none",
        "agents_involved": ", ".join(sorted(agents)) if agents else "orchestrator",
        "last_topic": topics[-1] if topics else "general",
    }


# ── Thread History Search (like mom's grep on log.jsonl) ─────────

def search_thread_history(
    events: list[dict[str, Any]],
    query: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Search through full thread event history.
    Like mom grepping log.jsonl for older context.

    Args:
        events: Full thread events list
        query: Search term (case-insensitive)
        max_results: Max results to return

    Returns:
        Matching events with context
    """
    query_lower = query.lower()
    results = []

    for event in events:
        content = event.get("content", "")
        if query_lower in content.lower():
            results.append({
                "timestamp": event.get("timestamp", ""),
                "event_type": event.get("event_type", ""),
                "agent_role": event.get("agent_role", ""),
                "content": content[:500],  # Truncate for context window
                "relevance": _simple_relevance(query_lower, content.lower()),
            })

    # Sort by relevance
    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:max_results]


def _simple_relevance(query: str, text: str) -> float:
    """Simple relevance scoring based on term frequency and position."""
    count = text.count(query)
    position = text.find(query)
    # Earlier position = more relevant, more occurrences = more relevant
    pos_score = 1.0 / (1 + position / 100) if position >= 0 else 0
    freq_score = min(count / 5, 1.0)
    return pos_score * 0.4 + freq_score * 0.6


# ── Trim Tool Results (for ContextTransformer pipeline) ──────────

def trim_old_tool_results(
    messages: list[dict[str, Any]],
    config: Any = None,
) -> list[dict[str, Any]]:
    """
    Aggressively trim tool results in older messages.
    Keeps recent tool results intact, truncates older ones.

    Designed as a ContextTransformer transform function.
    """
    if len(messages) <= 15:
        return messages

    cutoff = len(messages) - 10
    trimmed = []

    for i, msg in enumerate(messages):
        if i < cutoff and msg.get("role") == "tool":
            content = msg.get("content", "")
            if len(content) > MAX_TOOL_RESULT_CHARS:
                trimmed.append({
                    **msg,
                    "content": content[:MAX_TOOL_RESULT_CHARS] + "\n...[compacted]",
                })
                continue
        trimmed.append(msg)

    return trimmed
