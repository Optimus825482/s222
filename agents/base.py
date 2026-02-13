"""
BaseAgent — 12-Factor Agent pattern implementation.
Own your prompts (#2), context window (#3), control flow (#8),
compact errors (#9), small focused agents (#10).
"""

from __future__ import annotations

import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

import sys
from pathlib import Path

# Ensure project root is in path for Streamlit compatibility
_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from openai import AsyncOpenAI

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, MODELS
from core.models import AgentMetrics, AgentRole, Event, EventType, Thread
from core.events import serialize_thread_for_llm

# Regex to strip <think>...</think> blocks from model responses
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Also catch unclosed <think> tags (model started thinking but didn't close)
_THINK_OPEN_RE = re.compile(r"<think>.*", re.DOTALL | re.IGNORECASE)
# Regex to extract <tool_call>...</tool_call> blocks from model text output
_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL | re.IGNORECASE)


def _strip_thinking_tags(text: str) -> str:
    """Remove <think>...</think> blocks from LLM output."""
    if not text:
        return text
    # First remove closed tags
    cleaned = _THINK_RE.sub("", text)
    # Then remove unclosed tags
    cleaned = _THINK_OPEN_RE.sub("", cleaned)
    return cleaned.strip()


def _parse_text_tool_calls(content: str) -> list[dict] | None:
    """
    Fallback parser: extract tool calls from text when model returns them
    as <tool_call>{"name": ..., "arguments": ...}</tool_call> instead of
    native OpenAI tool_calls format.
    """
    if not content:
        return None
    matches = _TOOL_CALL_RE.findall(content)
    if not matches:
        return None

    parsed = []
    for match in matches:
        try:
            data = json.loads(match)
            fn_name = data.get("name") or data.get("function", {}).get("name")
            fn_args = data.get("arguments") or data.get("parameters") or data.get("function", {}).get("arguments", {})
            if fn_name:
                if isinstance(fn_args, dict):
                    fn_args = json.dumps(fn_args, ensure_ascii=False)
                parsed.append({
                    "id": f"text_call_{uuid.uuid4().hex[:8]}",
                    "function": {"name": fn_name, "arguments": fn_args},
                })
        except (json.JSONDecodeError, AttributeError):
            continue

    return parsed if parsed else None


class BaseAgent(ABC):
    """Abstract base for all agents — specialist and orchestrator."""

    role: AgentRole
    model_key: str

    def __init__(self) -> None:
        self.cfg = MODELS[self.model_key]
        self.client = AsyncOpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=NVIDIA_API_KEY,
        )
        self.max_steps = 10  # 12-Factor #10: small focused

    @abstractmethod
    def system_prompt(self) -> str:
        """Each agent owns its prompt — 12-Factor #2."""
        ...

    def get_tools(self) -> list[dict] | None:
        """Override to provide function-calling tools."""
        return None

    def build_context(self, thread: Thread, task_input: str) -> list[dict[str, str]]:
        """
        12-Factor #3: Build context window.
        Default: system prompt + serialized thread + current task.
        """
        history = serialize_thread_for_llm(thread, max_events=30)
        messages = [
            {"role": "system", "content": self.system_prompt()},
        ]
        if history.strip():
            messages.append({"role": "user", "content": f"Context so far:\n{history}"})
            messages.append({"role": "assistant", "content": "Understood. I have the context."})
        messages.append({"role": "user", "content": task_input})
        return messages

    async def call_llm(self, messages: list[dict], tools: list[dict] | None = None) -> dict[str, Any]:
        """Single LLM call with metrics tracking."""
        kwargs: dict[str, Any] = {
            "model": self.cfg["id"],
            "messages": messages,
            "max_tokens": self.cfg["max_tokens"],
            "temperature": self.cfg["temperature"],
            "top_p": self.cfg["top_p"],
        }
        if self.cfg.get("extra_body"):
            kwargs["extra_body"] = self.cfg["extra_body"]
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        t0 = time.monotonic()
        response = await self.client.chat.completions.create(**kwargs)
        latency_ms = (time.monotonic() - t0) * 1000

        choice = response.choices[0]
        usage = response.usage

        # Extract thinking content from dedicated fields
        thinking = getattr(choice.message, "reasoning_content", None) \
            or getattr(choice.message, "thinking", None)

        # Clean content: strip <think> tags that some models embed in output
        raw_content = choice.message.content or ""
        clean_content = _strip_thinking_tags(raw_content)

        # Use native tool_calls if available, otherwise try text fallback
        tool_calls = choice.message.tool_calls
        if not tool_calls and tools and raw_content:
            text_calls = _parse_text_tool_calls(raw_content)
            if text_calls:
                from types import SimpleNamespace
                tool_calls = []
                for tc in text_calls:
                    tool_calls.append(SimpleNamespace(
                        id=tc["id"],
                        type="function",
                        function=SimpleNamespace(
                            name=tc["function"]["name"],
                            arguments=tc["function"]["arguments"],
                        ),
                    ))
                # Strip tool_call tags from content since we parsed them
                clean_content = _TOOL_CALL_RE.sub("", clean_content).strip()

        return {
            "content": clean_content,
            "tool_calls": tool_calls,
            "finish_reason": choice.finish_reason,
            "tokens_prompt": usage.prompt_tokens if usage else 0,
            "tokens_completion": usage.completion_tokens if usage else 0,
            "tokens_total": usage.total_tokens if usage else 0,
            "latency_ms": latency_ms,
            "thinking": thinking,
        }

    async def execute(self, task_input: str, thread: Thread) -> str:
        """
        12-Factor #8: Own your control flow.
        While-loop with break/continue for tool calls.
        """
        thread.add_event(
            EventType.AGENT_START,
            f"Agent {self.role.value} starting: {task_input[:100]}",
            agent_role=self.role,
        )

        messages = self.build_context(thread, task_input)
        tools = self.get_tools()

        for step in range(self.max_steps):
            try:
                result = await self.call_llm(messages, tools)
            except Exception as e:
                # 12-Factor #9: Compact errors
                error_msg = f"LLM call failed: {type(e).__name__}: {e}"
                thread.add_event(EventType.ERROR, error_msg, agent_role=self.role)
                thread.update_metrics(self.role, 0, 0, success=False)
                return f"[Error] {error_msg}"

            # Track thinking content
            if result.get("thinking"):
                thread.add_event(
                    EventType.AGENT_THINKING,
                    result["thinking"][:500],
                    agent_role=self.role,
                )

            # Handle tool calls
            if result["tool_calls"]:
                for tc in result["tool_calls"]:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments)

                    thread.add_event(
                        EventType.TOOL_CALL,
                        f"{fn_name}({json.dumps(fn_args, ensure_ascii=False)[:200]})",
                        agent_role=self.role,
                    )

                    tool_result = await self.handle_tool_call(fn_name, fn_args, thread)

                    thread.add_event(
                        EventType.TOOL_RESULT,
                        str(tool_result)[:500],
                        agent_role=self.role,
                    )

                    # Append to messages for next LLM turn
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": fn_name, "arguments": tc.function.arguments}}],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(tool_result),
                    })
                continue  # Back to LLM with tool results

            # Final response — break the loop
            content = result["content"]
            thread.add_event(
                EventType.AGENT_RESPONSE,
                content,
                agent_role=self.role,
                tokens=result["tokens_total"],
                latency_ms=result["latency_ms"],
                step=step,
            )
            thread.update_metrics(
                self.role,
                result["tokens_total"],
                result["latency_ms"],
                success=True,
            )
            return content

        # Max steps reached
        thread.update_metrics(self.role, 0, 0, success=False)
        return "[Warning] Max steps reached — partial result."

    async def handle_tool_call(self, fn_name: str, fn_args: dict, thread: Thread) -> str:
        """
        Handle tool calls — shared tools first, then subclass-specific.
        Override _handle_custom_tool in subclasses for agent-specific tools.
        """
        # Shared tools available to all agents
        if fn_name == "web_search":
            from tools.search import web_search, format_search_results
            results = await web_search(
                query=fn_args["query"],
                max_results=fn_args.get("max_results", 5),
            )
            return format_search_results(results)

        if fn_name == "web_fetch":
            from tools.web_fetch import web_fetch, format_fetch_result
            result = await web_fetch(
                url=fn_args["url"],
                max_chars=fn_args.get("max_chars", 8000),
            )
            return format_fetch_result(result)

        if fn_name == "save_memory":
            from tools.memory import save_memory
            entry = save_memory(
                content=fn_args["content"],
                category=fn_args.get("category", "general"),
                tags=fn_args.get("tags"),
                source_agent=self.role.value,
            )
            return f"Memory saved: {entry['id']} [{entry['category']}]"

        if fn_name == "recall_memory":
            from tools.memory import recall_memory, format_recall_results
            results = recall_memory(
                query=fn_args["query"],
                category=fn_args.get("category"),
                max_results=fn_args.get("max_results", 5),
            )
            return format_recall_results(results)

        if fn_name == "find_skill":
            from tools.skill_finder import find_skills, format_skill_results
            skills = find_skills(
                query=fn_args["query"],
                max_results=fn_args.get("max_results", 3),
            )
            return format_skill_results(skills)

        if fn_name == "use_skill":
            from tools.skill_finder import get_skill_knowledge, format_skill_knowledge
            knowledge = get_skill_knowledge(fn_args["skill_id"])
            if knowledge:
                return format_skill_knowledge(fn_args["skill_id"], knowledge)
            return f"Skill '{fn_args['skill_id']}' not found."

        # Delegate to subclass
        return await self._handle_custom_tool(fn_name, fn_args, thread)

    async def _handle_custom_tool(self, fn_name: str, fn_args: dict, thread: Thread) -> str:
        """Override in subclasses for agent-specific tools."""
        return f"Tool '{fn_name}' not implemented."
