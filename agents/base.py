"""
BaseAgent — 12-Factor Agent pattern implementation.
Own your prompts (#2), context window (#3), control flow (#8),
compact errors (#9), small focused agents (#10).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import time
import uuid as uuid_module
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from openai import AsyncOpenAI

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODELS, PI_GATEWAY_URL, PI_GATEWAY_ENABLED, PI_GATEWAY_FALLBACK_ENABLED, PI_GATEWAY_STREAMING_ENABLED, GATEWAY_MODELS, RUNTIME_EVENT_SCHEMA_VERSION, get_feature_flags, get_model_capabilities, get_provider_registry_entry
from core.models import AgentRole, EventType, Thread
from core.events import serialize_thread_for_llm

# Ensure project root is in path for Streamlit compatibility
_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Regex to strip <think>...</think> blocks from model responses
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Also catch unclosed <think> tags (model started thinking but didn't close)
_THINK_OPEN_RE = re.compile(r"<think>.*", re.DOTALL | re.IGNORECASE)
# Regex to extract <tool_call>...</tool_call> blocks from model text output
_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL | re.IGNORECASE)
logger = logging.getLogger(__name__)


def _strip_thinking_tags(text: str) -> str:
    """Remove <think>...</think> blocks from LLM output.
    SAFETY: Only remove CLOSED <think>...</think> pairs.
    For unclosed <think> tags, remove ONLY the tag itself (not content after it)
    to prevent stripping actual response content from models like MiniMax M2.1.
    """
    if not text:
        return text
    # Remove properly closed <think>...</think> blocks
    cleaned = _THINK_RE.sub("", text)
    # For unclosed <think> tags: only remove the tag, NOT everything after it
    # Old behavior: _THINK_OPEN_RE with re.DOTALL would delete ALL content after <think>
    # New behavior: just strip the orphan <think> tag itself
    cleaned = re.sub(r"<think>", "", cleaned, flags=re.IGNORECASE)
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
                parsed.append(
                    {
                        "id": f"text_call_{uuid_module.uuid4().hex[:8]}",
                        "function": {"name": fn_name, "arguments": fn_args},
                    }
                )
        except (json.JSONDecodeError, AttributeError):
            continue

    return parsed if parsed else None


class BaseAgent(ABC):
    """Abstract base for all agents — specialist and orchestrator."""

    role: AgentRole
    model_key: str

    # Max seconds per LLM request and per agent run (avoid endless hangs)
    LLM_TIMEOUT = 60
    AGENT_EXECUTE_TIMEOUT = 120
    # Extended timeout for reasoning models (chain-of-thought takes longer)
    LLM_TIMEOUT_REASONING = 180

    def __init__(self) -> None:
        self.cfg = MODELS[self.model_key]
        if self.cfg.get("base_url") == "deepseek":
            _base_url = DEEPSEEK_BASE_URL
            _api_key = DEEPSEEK_API_KEY
        else:
            _base_url = NVIDIA_BASE_URL
            _api_key = NVIDIA_API_KEY
        # Use extended timeout for reasoning/thinking models
        _timeout = (
            float(self.LLM_TIMEOUT_REASONING)
            if self.cfg.get("has_thinking")
            else float(self.LLM_TIMEOUT)
        )
        self.client = AsyncOpenAI(
            base_url=_base_url,
            api_key=_api_key,
            timeout=_timeout,
        )

        # PI AI Gateway client (optional, for multi-provider routing)
        self.gateway_client: AsyncOpenAI | None = None
        if PI_GATEWAY_ENABLED:
            gateway_base_url = PI_GATEWAY_URL.rstrip("/")
            if not gateway_base_url.endswith("/v1"):
                gateway_base_url = f"{gateway_base_url}/v1"
            self.gateway_client = AsyncOpenAI(
                base_url=gateway_base_url,
                api_key="pi-gateway",  # gateway handles auth per provider
                timeout=_timeout,
            )

        self.max_steps = 15  # Reduced from 30 for faster responses
        self._live_monitor = None  # LiveMonitor callback for realtime UI

        # Agent Communication Protocol (Faz 15) — lazy init
        self._bus = None
        self._handoff_manager = None
        self._task_delegation = None
        self._perf_collector = None
        
        # Inter-Agent Communication (Faz 16)
        self._message_bus = None
        self._pending_messages: list = []

    @abstractmethod
    def system_prompt(self) -> str:
        """Each agent owns its prompt — 12-Factor #2."""
        ...

    def _identity_prompt(self) -> str:
        """Load SOUL.md identity context for this agent (Faz 11.6)."""
        try:
            from tools.agent_identity import IdentityManager
            mgr = IdentityManager()
            return mgr.get_system_prompt(self.role.value if hasattr(self.role, 'value') else str(self.role))
        except Exception:
            return ""

    def get_tools(self) -> list[dict] | None:
        """Override to provide function-calling tools."""
        return None

    async def build_context(
        self, thread: Thread, task_input: str
    ) -> list[dict[str, Any]]:
        """
        12-Factor #3: Build context window.
        Default: system prompt + serialized thread + current task.
        Injects current date + activated skills into system prompt.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%d %B %Y, %A, %H:%M UTC")
        date_injection = (
            f"\n\nCURRENT DATE AND TIME: {date_str}. "
            f"Year is {now.year}. Use this as the real current date and time for all responses."
        )

        # Anti-hallucination rules — injected into ALL agents
        integrity_rules = (
            "\n\n## INTEGRITY RULES (MANDATORY — NEVER VIOLATE):\n"
            "1. NEVER fabricate, invent, or hallucinate information. Only provide factual, verifiable data.\n"
            "2. NEVER generate fake URLs, file paths, download links, or API endpoints that do not exist.\n"
            "3. If you don't know something, say 'Bilmiyorum' or 'Bu bilgiye sahip değilim' — do NOT make up an answer.\n"
            "4. NEVER invent statistics, percentages, market sizes, or quotes without a real source.\n"
            "5. When citing sources, only cite URLs you actually found via web_search or web_fetch.\n"
            "6. If a task fails or produces no result, report the failure honestly — do NOT fabricate a success response.\n"
            "7. NEVER generate S3, CDN, cloud storage, or any external download URLs unless you created them.\n"
            "8. Distinguish clearly between facts (verified) and opinions/estimates (labeled as such).\n"
        )

        # Auto-inject activated skills from sub-task assignments
        skill_injection = self._build_skill_injection(task_input, thread)

        # Visual capabilities — grafik çizme + Pollinations ile görsel üretme (injected into ALL agents)
        image_capability = (
            "\n\n## VISUAL CAPABILITIES (use when tasks need visuals):\n"
            "**1. generate_image** (Pollinations API — AI image generation):\n"
            "- Use for: illustrations, diagrams, infographics, concept art, photos.\n"
            "- Prompt in ENGLISH, descriptive and specific. Returns markdown image + download URL.\n"
            "- Example: 'Professional diagram showing microservices architecture with API gateway'.\n"
            "**2. generate_chart** (matplotlib — data visualization):\n"
            "- Use for: bar/line/pie/scatter/histogram/area/heatmap from structured data.\n"
            "- Pass chart_type, data (e.g. {labels, values} or {x, y}), title, optional width/height.\n"
            "- Use when the user asks for a chart, graph, or when analysis results should be shown visually.\n"
            "- In reports: add 1–3 relevant images (generate_image) and/or charts (generate_chart) when they add value.\n"
            "- DO NOT skip these tools when the task would benefit from a visual.\n"
        )

        # Faz 11.6 — SOUL.md identity injection
        identity_ctx = self._identity_prompt()

        history = serialize_thread_for_llm(thread, max_events=30)
        system_content = self.system_prompt() + date_injection + integrity_rules + image_capability
        if identity_ctx:
            system_content = identity_ctx + "\n\n---\nAgent Task Instructions:\n" + system_content
        if skill_injection:
            system_content += skill_injection

        # Faz 16: Inject active prompt strategy if available
        try:
            from tools.prompt_strategies import get_prompt_strategy_manager
            from tools.agent_eval import detect_task_type
            ps_task_type = detect_task_type(task_input)
            active_strategy = get_prompt_strategy_manager().get_active(
                self.role.value, ps_task_type
            )
            if active_strategy:
                strategy_injection = "\n\n## ACTIVE PROMPT STRATEGY:\n"
                if active_strategy.get("cot_instructions"):
                    strategy_injection += f"Chain-of-Thought: {active_strategy['cot_instructions']}\n"
                if active_strategy.get("few_shot_examples"):
                    strategy_injection += "Few-shot examples:\n"
                    for ex in active_strategy["few_shot_examples"][:3]:
                        if isinstance(ex, dict):
                            strategy_injection += f"- Input: {ex.get('input', '')}\n  Output: {ex.get('output', '')}\n"
                        else:
                            strategy_injection += f"- {ex}\n"
                system_content += strategy_injection
        except Exception:
            pass  # Never break agent for strategy injection

        messages = [
            {"role": "system", "content": system_content},
        ]
        if history.strip():
            messages.append({"role": "user", "content": f"Context so far:\n{history}"})
            messages.append({"role": "assistant", "content": "Understood. I have the context."})
        messages.append({"role": "user", "content": task_input})
        return messages

    def _build_skill_injection(self, task_input: str, thread: Thread) -> str:
        """Extract skill IDs from current sub-task and inject their knowledge."""
        skill_ids: list[str] = []

        # Find skill IDs from the current sub-task assigned to this agent
        for task in reversed(thread.tasks):
            for st in task.sub_tasks:
                if st.assigned_agent == self.role and st.skills:
                    skill_ids.extend(st.skills)

        if not skill_ids:
            return ""

        try:
            from tools.dynamic_skills import get_full_skill_context
            parts = []
            seen = set()
            for sid in skill_ids:
                if sid in seen:
                    continue
                seen.add(sid)
                ctx = get_full_skill_context(sid)
                if ctx:
                    parts.append(f'<skill id="{sid}">\n{ctx}\n</skill>')
            if parts:
                return "\n\n## ACTIVATED SKILLS:\n" + "\n\n".join(parts) + "\n"
        except Exception:
            pass
        return ""

    def _get_client_for_model(self, effective: dict) -> tuple[AsyncOpenAI, str]:
        """Return (client, model_id) based on gateway availability and config.

        Routing logic:
        - If gateway is enabled AND effective config has a 'gateway_model' override → gateway client
        - Otherwise → existing NVIDIA/DeepSeek client (fully backward compatible)
        """
        gateway_model = effective.get("gateway_model")
        if self.gateway_client and gateway_model:
            return self.gateway_client, gateway_model
        return self.client, effective["id"]

    def _build_runtime_metadata(
        self,
        *,
        model_name: str,
        provider: str,
        attempt_count: int,
        fallback_used: bool,
        used_gateway: bool,
        stream: bool,
        error_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = {
            "event_schema_version": RUNTIME_EVENT_SCHEMA_VERSION,
            "feature_flags": get_feature_flags(),
            "capabilities": get_model_capabilities(self.model_key),
            "provider_registry": get_provider_registry_entry(self.model_key),
            "provider": provider,
            "selected_model": model_name,
            "attempt_count": attempt_count,
            "fallback_used": fallback_used,
            "used_gateway": used_gateway,
            "stream": stream,
        }
        if error_message:
            metadata["error_message"] = error_message[:500]
        if extra:
            metadata.update(extra)
        return metadata

    def _resolve_runtime_provider_metadata(
        self,
        *,
        model_name: str,
        effective: dict[str, Any],
        used_gateway: bool,
    ) -> tuple[str, dict[str, Any]]:
        """Avoid claiming a concrete provider when the gateway may have rerouted internally."""
        provider_entry = get_provider_registry_entry(self.model_key)
        configured_provider = str(provider_entry.get("primary_provider", effective.get("base_url", "nvidia")))
        if not used_gateway:
            return configured_provider, {"configured_provider": configured_provider}
        if "/" in model_name:
            actual_provider = model_name.split("/", 1)[0]
            return actual_provider, {
                "configured_provider": configured_provider,
                "gateway_routed": True,
            }
        return "gateway", {
            "configured_provider": configured_provider,
            "gateway_routed": True,
        }

    def _get_fallback_models(self) -> list[str]:
        """Get fallback model IDs from GATEWAY_MODELS for this agent's role.
        Returns list of 'provider/model_id' strings for gateway fallback.
        """
        if not PI_GATEWAY_FALLBACK_ENABLED or not self.gateway_client:
            return []
        role = self.role.value if hasattr(self.role, "value") else str(self.role)
        role_config = GATEWAY_MODELS.get(self.model_key) or GATEWAY_MODELS.get(role)
        if not role_config:
            return []
        alternatives = role_config.get("alternatives", [])
        return [f"{alt['provider']}/{alt['id']}" for alt in alternatives if alt.get("provider") and alt.get("id")]

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        """Check if an LLM error is worth retrying on a different provider."""
        msg = str(exc).lower()
        # Rate limits, server errors, timeouts, connection issues
        return any(kw in msg for kw in (
            "429", "rate limit", "rate_limit",
            "500", "502", "503", "504",
            "timeout", "timed out",
            "connection", "econnrefused", "econnreset",
            "server error", "internal server error",
            "all providers failed",
        ))

    @staticmethod
    def _normalize_token_usage(usage: Any) -> dict[str, Any]:
        """Normalize provider usage payload.

        Standard:
        - known values => integer token counts + status=known
        - unknown values => null (None) + status=unknown + reason
        """
        if usage is None:
            return {
                "tokens_prompt": None,
                "tokens_completion": None,
                "tokens_total": None,
                "token_usage_status": "unknown",
                "token_usage_reason": "provider_usage_missing",
            }

        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

        missing_fields = []
        if prompt_tokens is None:
            missing_fields.append("prompt_tokens")
        if completion_tokens is None:
            missing_fields.append("completion_tokens")
        if total_tokens is None:
            missing_fields.append("total_tokens")

        status = "known" if not missing_fields else "unknown"
        reason = None if status == "known" else f"missing_fields:{','.join(missing_fields)}"

        return {
            "tokens_prompt": int(prompt_tokens) if prompt_tokens is not None else None,
            "tokens_completion": int(completion_tokens) if completion_tokens is not None else None,
            "tokens_total": int(total_tokens) if total_tokens is not None else None,
            "token_usage_status": status,
            "token_usage_reason": reason,
        }

    async def call_llm(self, messages: list[dict], tools: list[dict] | None = None) -> dict[str, Any]:
        """Single LLM call with metrics tracking and provider fallback.
        Uses effective config (Faz 12.1 overrides).
        When PI gateway is enabled, sends fallback_models in the request body
        so the gateway can try alternatives if the primary provider fails.
        If the gateway itself fails, retries with alternative models from GATEWAY_MODELS.
        """
        try:
            from tools.agent_param_overrides import get_effective_config

            effective = get_effective_config(self.model_key)
        except Exception:
            effective = self.cfg

        # Determine which client and model to use
        client, model_id = self._get_client_for_model(effective)

        # Build fallback model list for gateway-level fallback
        fallback_models = self._get_fallback_models()

        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "max_tokens": effective["max_tokens"],
            "temperature": effective["temperature"],
            "top_p": effective["top_p"],
        }
        extra_body = dict(effective.get("extra_body") or {})
        # Inject fallback_models into extra_body for gateway
        if fallback_models and self.gateway_client and client is self.gateway_client:
            extra_body["fallback_models"] = fallback_models
        if extra_body:
            kwargs["extra_body"] = extra_body
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        t0 = time.monotonic()

        # Attempt primary call
        last_error: Exception | None = None
        attempt_count = 1
        fallback_used = False
        selected_model = model_id
        used_gateway = client is self.gateway_client
        selected_provider, runtime_extra = self._resolve_runtime_provider_metadata(
            model_name=selected_model,
            effective=effective,
            used_gateway=used_gateway,
        )
        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as primary_err:
            last_error = primary_err
            response = None

            # Python-level fallback: if primary failed and we have alternatives, try them
            if self._is_retryable_error(primary_err) and fallback_models and self.gateway_client:
                for fb_model in fallback_models:
                    try:
                        attempt_count += 1
                        fb_kwargs = dict(kwargs)
                        fb_kwargs["model"] = fb_model
                        # Remove fallback_models from extra_body for fallback calls
                        fb_extra = {k: v for k, v in extra_body.items() if k != "fallback_models"}
                        if fb_extra:
                            fb_kwargs["extra_body"] = fb_extra
                        elif "extra_body" in fb_kwargs:
                            del fb_kwargs["extra_body"]
                        response = await self.gateway_client.chat.completions.create(**fb_kwargs)
                        fallback_used = True
                        selected_model = fb_model
                        selected_provider, runtime_extra = self._resolve_runtime_provider_metadata(
                            model_name=selected_model,
                            effective=effective,
                            used_gateway=True,
                        )
                        last_error = None
                        break  # success
                    except Exception as fb_err:
                        last_error = fb_err
                        if not self._is_retryable_error(fb_err):
                            break  # non-retryable, stop trying

            # If all gateway attempts failed, try direct client as last resort
            if response is None and client is self.gateway_client:
                try:
                    attempt_count += 1
                    direct_kwargs = dict(kwargs)
                    direct_kwargs["model"] = effective["id"]
                    direct_extra = {k: v for k, v in (effective.get("extra_body") or {}).items()}
                    if direct_extra:
                        direct_kwargs["extra_body"] = direct_extra
                    elif "extra_body" in direct_kwargs:
                        del direct_kwargs["extra_body"]
                    response = await self.client.chat.completions.create(**direct_kwargs)
                    fallback_used = True
                    selected_model = effective["id"]
                    selected_provider, runtime_extra = self._resolve_runtime_provider_metadata(
                        model_name=selected_model,
                        effective=effective,
                        used_gateway=False,
                    )
                    last_error = None
                except Exception:
                    pass  # keep original error

        if response is None:
            # Record failed metrics
            try:
                if self.perf_collector:
                    self.perf_collector.record(
                        agent_role=self.role.value if hasattr(self.role, 'value') else str(self.role),
                        response_time_ms=(time.monotonic() - t0) * 1000,
                        success=False,
                        model_name=selected_model,
                        error_message=str(last_error)[:500] if last_error else "Unknown error",
                        metadata=self._build_runtime_metadata(
                            model_name=selected_model,
                            provider=selected_provider,
                            attempt_count=attempt_count,
                            fallback_used=fallback_used,
                            used_gateway=used_gateway,
                            stream=False,
                            error_message=str(last_error) if last_error else None,
                            extra=runtime_extra,
                        ),
                    )
            except Exception:
                pass
            raise last_error or RuntimeError("LLM call failed with no response")

        latency_ms = (time.monotonic() - t0) * 1000

        choice = response.choices[0]
        usage = response.usage
        usage_norm = self._normalize_token_usage(usage)

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

        # Record performance metrics
        try:
            if self.perf_collector:
                self.perf_collector.record(
                    agent_role=self.role.value if hasattr(self.role, 'value') else str(self.role),
                    response_time_ms=latency_ms,
                    input_tokens=int(usage_norm["tokens_prompt"] or 0),
                    output_tokens=int(usage_norm["tokens_completion"] or 0),
                    total_tokens=int(usage_norm["tokens_total"] or 0),
                    success=True,
                    model_name=selected_model,
                    metadata=self._build_runtime_metadata(
                        model_name=selected_model,
                        provider=selected_provider,
                        attempt_count=attempt_count,
                        fallback_used=fallback_used,
                        used_gateway=used_gateway,
                        stream=False,
                        extra=runtime_extra,
                    ),
                )
        except Exception:
            pass  # Never break LLM flow for metrics

        return {
            "content": clean_content,
            "tool_calls": tool_calls,
            "finish_reason": choice.finish_reason,
            "tokens_prompt": usage_norm["tokens_prompt"],
            "tokens_completion": usage_norm["tokens_completion"],
            "tokens_total": usage_norm["tokens_total"],
            "token_usage_status": usage_norm["token_usage_status"],
            "token_usage_reason": usage_norm["token_usage_reason"],
            "latency_ms": latency_ms,
            "thinking": thinking,
            "provider": selected_provider,
            "selected_model": selected_model,
            "fallback_used": fallback_used,
            "attempt_count": attempt_count,
            "used_gateway": used_gateway,
            "runtime": self._build_runtime_metadata(
                model_name=selected_model,
                provider=selected_provider,
                attempt_count=attempt_count,
                fallback_used=fallback_used,
                used_gateway=used_gateway,
                stream=False,
                extra=runtime_extra,
            ),
        }

    async def call_llm_stream(self, messages: list[dict], tools: list[dict] | None = None):
        """Streaming version of call_llm — yields granular events.

        Yields dicts with types: text_delta, thinking_delta,
        toolcall_start, toolcall_delta, done.
        Falls back to non-streaming call_llm() if streaming is disabled
        or if an error occurs mid-stream.
        """
        # Guard: streaming requires gateway
        if not PI_GATEWAY_STREAMING_ENABLED or not self.gateway_client:
            result = await self.call_llm(messages, tools)
            if result.get("content"):
                yield {"type": "text_delta", "delta": result["content"], "agent": self.role.value}
            yield {
                "type": "done",
                "agent": self.role.value,
                "content": result.get("content", ""),
                "thinking": result.get("thinking", ""),
                "tool_calls": result.get("tool_calls") or [],
                "usage": {
                    "prompt_tokens": result.get("tokens_prompt"),
                    "completion_tokens": result.get("tokens_completion"),
                    "total_tokens": result.get("tokens_total"),
                    "token_usage_status": result.get("token_usage_status", "unknown"),
                    "token_usage_reason": result.get("token_usage_reason", "provider_usage_missing"),
                },
            }
            return

        try:
            from tools.agent_param_overrides import get_effective_config
            effective = get_effective_config(self.model_key)
        except Exception:
            effective = self.cfg

        client, model_id = self._get_client_for_model(effective)
        fallback_models = self._get_fallback_models()

        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "max_tokens": effective["max_tokens"],
            "temperature": effective["temperature"],
            "top_p": effective["top_p"],
            "stream": True,
        }
        extra_body = dict(effective.get("extra_body") or {})
        if fallback_models and client is self.gateway_client:
            extra_body["fallback_models"] = fallback_models
        if extra_body:
            kwargs["extra_body"] = extra_body
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        t0 = time.monotonic()
        full_text = ""
        full_thinking = ""
        tool_calls_acc: dict[int, dict] = {}  # index → {id, name, arguments}
        provider_entry = get_provider_registry_entry(self.model_key)
        selected_provider, runtime_extra = self._resolve_runtime_provider_metadata(
            model_name=model_id,
            effective=effective,
            used_gateway=client is self.gateway_client,
        )
        attempt_count = 1
        fallback_used = False
        used_gateway = client is self.gateway_client

        try:
            stream = await client.chat.completions.create(**kwargs)

            async for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason

                # --- Text content delta ---
                if delta.content:
                    full_text += delta.content
                    yield {
                        "type": "text_delta",
                        "delta": delta.content,
                        "agent": self.role.value,
                        "runtime": self._build_runtime_metadata(
                            model_name=model_id,
                            provider=selected_provider,
                            attempt_count=attempt_count,
                            fallback_used=fallback_used,
                            used_gateway=used_gateway,
                            stream=True,
                            extra=runtime_extra,
                        ),
                    }

                # --- Thinking delta (custom gateway extension) ---
                thinking_delta = getattr(delta, "thinking", None) or getattr(delta, "reasoning_content", None)
                if thinking_delta:
                    full_thinking += thinking_delta
                    yield {
                        "type": "thinking_delta",
                        "delta": thinking_delta,
                        "agent": self.role.value,
                        "runtime": self._build_runtime_metadata(
                            model_name=model_id,
                            provider=selected_provider,
                            attempt_count=attempt_count,
                            fallback_used=fallback_used,
                            used_gateway=used_gateway,
                            stream=True,
                            extra=runtime_extra,
                        ),
                    }

                # --- Tool call deltas ---
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_acc:
                            # New tool call starting
                            tc_id = (
                                tc_delta.id
                                or f"stream_call_{uuid_module.uuid4().hex[:8]}"
                            )
                            tc_name = tc_delta.function.name if tc_delta.function and tc_delta.function.name else ""
                            tool_calls_acc[idx] = {
                                "id": tc_id,
                                "name": tc_name,
                                "arguments": "",
                            }
                            if tc_name:
                                yield {
                                    "type": "toolcall_start",
                                    "agent": self.role.value,
                                    "tool_name": tc_name,
                                    "tool_call_id": tc_id,
                                    "runtime": self._build_runtime_metadata(
                                        model_name=model_id,
                                        provider=selected_provider,
                                        attempt_count=attempt_count,
                                        fallback_used=fallback_used,
                                        used_gateway=used_gateway,
                                        stream=True,
                                        extra=runtime_extra,
                                    ),
                                }
                        else:
                            # Update name if it arrives in a later chunk
                            if tc_delta.function and tc_delta.function.name:
                                tool_calls_acc[idx]["name"] = tc_delta.function.name

                        # Accumulate arguments
                        if tc_delta.function and tc_delta.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments
                            yield {
                                "type": "toolcall_delta",
                                "delta": tc_delta.function.arguments,
                                "agent": self.role.value,
                                "tool_call_id": tool_calls_acc[idx]["id"],
                                "runtime": self._build_runtime_metadata(
                                    model_name=model_id,
                                    provider=selected_provider,
                                    attempt_count=attempt_count,
                                    fallback_used=fallback_used,
                                    used_gateway=used_gateway,
                                    stream=True,
                                    extra=runtime_extra,
                                ),
                            }

                # --- Stream finished ---
                if finish_reason:
                    break

            latency_ms = (time.monotonic() - t0) * 1000

            # Build final tool_calls list matching call_llm() format
            final_tool_calls = []
            if tool_calls_acc:
                from types import SimpleNamespace
                for idx in sorted(tool_calls_acc):
                    tc = tool_calls_acc[idx]
                    final_tool_calls.append(SimpleNamespace(
                        id=tc["id"],
                        type="function",
                        function=SimpleNamespace(
                            name=tc["name"],
                            arguments=tc["arguments"],
                        ),
                    ))

            # Clean content: strip <think> tags
            clean_content = _strip_thinking_tags(full_text)

            # Extract usage from the last chunk if available
            usage_data: dict[str, Any] = {
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "token_usage_status": "unknown",
                "token_usage_reason": "provider_usage_missing",
            }
            if chunk and hasattr(chunk, "usage"):
                usage_data = self._normalize_token_usage(getattr(chunk, "usage", None))

            try:
                if self.perf_collector:
                    self.perf_collector.record(
                        agent_role=self.role.value if hasattr(self.role, 'value') else str(self.role),
                        response_time_ms=latency_ms,
                        input_tokens=int(usage_data.get("prompt_tokens", 0) or 0),
                        output_tokens=int(usage_data.get("completion_tokens", 0) or 0),
                        total_tokens=int(usage_data.get("total_tokens", 0) or 0),
                        success=True,
                        model_name=model_id,
                        metadata=self._build_runtime_metadata(
                            model_name=model_id,
                            provider=selected_provider,
                            attempt_count=attempt_count,
                            fallback_used=fallback_used,
                            used_gateway=used_gateway,
                            stream=True,
                            extra=runtime_extra,
                        ),
                    )
            except Exception:
                pass

            yield {
                "type": "done",
                "agent": self.role.value,
                "content": clean_content,
                "thinking": full_thinking,
                "tool_calls": final_tool_calls,
                "usage": usage_data,
                "latency_ms": latency_ms,
                "runtime": self._build_runtime_metadata(
                    model_name=model_id,
                    provider=selected_provider,
                    attempt_count=attempt_count,
                    fallback_used=fallback_used,
                    used_gateway=used_gateway,
                    stream=True,
                    extra=runtime_extra,
                ),
            }

        except Exception as e:
            # Fallback to non-streaming on any stream error
            import logging
            logging.getLogger(__name__).warning(
                "call_llm_stream failed, falling back to call_llm: %s", e
            )
            try:
                result = await self.call_llm(messages, tools)
                if result.get("content"):
                    yield {
                        "type": "text_delta",
                        "delta": result["content"],
                        "agent": self.role.value,
                        "runtime": result.get("runtime", {}),
                    }
                yield {
                    "type": "done",
                    "agent": self.role.value,
                    "content": result.get("content", ""),
                    "thinking": result.get("thinking", ""),
                    "tool_calls": result.get("tool_calls") or [],
                    "usage": {
                        "prompt_tokens": result.get("tokens_prompt"),
                        "completion_tokens": result.get("tokens_completion"),
                        "total_tokens": result.get("tokens_total"),
                        "token_usage_status": result.get("token_usage_status", "unknown"),
                        "token_usage_reason": result.get("token_usage_reason", "provider_usage_missing"),
                    },
                    "runtime": result.get("runtime", {}),
                }
            except Exception as fallback_err:
                yield {
                    "type": "done",
                    "agent": self.role.value,
                    "content": f"[Error] Streaming and fallback both failed: {e} / {fallback_err}",
                    "thinking": "",
                    "tool_calls": [],
                    "usage": {},
                    "runtime": self._build_runtime_metadata(
                        model_name=model_id,
                        provider=selected_provider,
                        attempt_count=attempt_count,
                        fallback_used=True,
                        used_gateway=used_gateway,
                        stream=True,
                        error_message=f"{e} / {fallback_err}",
                        extra=runtime_extra,
                    ),
                }

    def set_live_monitor(self, monitor):
        """Attach a LiveMonitor for realtime UI updates."""
        self._live_monitor = monitor

    # ── Agent Communication Protocol (Faz 15) ───────────────────

    @property
    def bus(self):
        """Lazy-init EventBus erişimi."""
        if self._bus is None:
            from core.event_bus import get_event_bus
            self._bus = get_event_bus()
        return self._bus

    @property
    def handoff_manager(self):
        """Lazy-init HandoffManager erişimi."""
        if self._handoff_manager is None:
            from core.handoff import get_handoff_manager
            self._handoff_manager = get_handoff_manager()
        return self._handoff_manager

    @property
    def task_delegation(self):
        """Lazy-init TaskDelegationManager erişimi."""
        if self._task_delegation is None:
            from core.task_delegation import get_task_delegation_manager
            self._task_delegation = get_task_delegation_manager()
        return self._task_delegation

    @property
    def perf_collector(self):
        if self._perf_collector is None:
            try:
                from tools.performance_collector import PerformanceCollector
                self._perf_collector = PerformanceCollector()
            except Exception:
                pass
        return self._perf_collector

    async def send_to_agent(
        self, target: str, msg_type, payload: dict, correlation_id: str | None = None,
    ) -> bool:
        """Başka bir agent'a doğrudan mesaj gönder."""
        from core.protocols import MessageType as MT
        return await self.bus.send_to_agent(
            source=self.role.value,
            target=target,
            msg_type=msg_type if isinstance(msg_type, MT) else MT(msg_type),
            payload=payload,
            correlation_id=correlation_id,
        )

    async def broadcast_message(self, msg_type, payload: dict) -> bool:
        """Tüm agent'lara broadcast mesaj gönder."""
        from core.protocols import MessageType as MT
        return await self.bus.broadcast(
            source=self.role.value,
            msg_type=msg_type if isinstance(msg_type, MT) else MT(msg_type),
            payload=payload,
        )

    async def delegate_task(
        self, target: str, description: str, input_data: dict | None = None, timeout: float = 120.0,
    ) -> str | None:
        """Başka bir agent'a görev delegasyonu — sonucu bekle."""
        return await self.task_delegation.delegate_and_wait(
            delegator=self.role.value,
            delegate=target,
            description=description,
            input_data=input_data,
            timeout=timeout,
        )

    async def handoff_to(
        self,
        target: str,
        reason: str,
        task_description: str,
        work_completed: str = "",
        work_remaining: str = "",
        partial_result: str = "",
        thread_id: str | None = None,
    ):
        """İşi başka bir agent'a devret."""
        return await self.handoff_manager.initiate(
            from_agent=self.role.value,
            to_agent=target,
            reason=reason,
            task_description=task_description,
            work_completed=work_completed,
            work_remaining=work_remaining,
            partial_result=partial_result,
            thread_id=thread_id,
        )

    def subscribe_to_channel(self, channel: str, handler, filter_types=None):
        """Bu agent'ı bir kanala abone et."""
        return self.bus.subscribe(
            agent_role=self.role.value,
            channel=channel,
            handler=handler,
            filter_types=filter_types,
        )

    # ── End Agent Communication Protocol ─────────────────────────

    # ── Inter-Agent Communication (Faz 16) ─────────────────────────
    
    def _get_message_bus(self):
        """Get the inter-agent message bus (lazy init)."""
        if self._message_bus is None:
            from tools.inter_agent_comm import get_message_bus
            self._message_bus = get_message_bus()
        return self._message_bus
    
    async def send_agent_message(
        self,
        to_agent: str,
        content: str,
        message_type: str = "direct",
        metadata: dict[str, Any] | None = None,
        requires_response: bool = False,
    ) -> str:
        """
        Send a message to another agent.
        
        Args:
            to_agent: Target agent role (or "broadcast" for all)
            content: Message content
            message_type: "direct", "collab_request", "task_delegation", "alert"
            metadata: Optional metadata
            requires_response: Whether a response is expected
            
        Returns:
            Message ID
        """
        from tools.inter_agent_comm import (
            MessageType,
            AgentMessage,
            send_collaboration_request,
            send_task_delegation,
            broadcast_alert,
        )
        
        bus = self._get_message_bus()
        
        if message_type == "collab_request":
            return await send_collaboration_request(
                from_agent=self.role.value,
                to_agent=to_agent,
                task_description=content,
                context=metadata or {},
            )
        elif message_type == "task_delegation":
            return await send_task_delegation(
                from_agent=self.role.value,
                to_agent=to_agent,
                task=content,
            )
        elif message_type == "alert" or to_agent == "broadcast":
            await broadcast_alert(
                from_agent=self.role.value,
                alert_content=content,
                metadata=metadata or {},
            )
            return "broadcast_sent"
        else:
            # Direct message
            message = AgentMessage(
                from_agent=self.role.value,
                to_agent=to_agent,
                message_type=MessageType.DIRECT,
                content=content,
                metadata=metadata or {},
                requires_response=requires_response,
            )
            await bus.send(message)
            return message.id
    
    async def receive_agent_messages(self, timeout: float = 0.1) -> list:
        """
        Check for pending messages from other agents.
        
        Returns:
            List of AgentMessage objects
        """
        bus = self._get_message_bus()
        messages = []
        
        while True:
            msg = await bus.receive(self.role.value, timeout=timeout)
            if msg is None:
                break
            messages.append(msg)
        
        return messages

    def share_knowledge(
        self, key: str, value: Any, tags: list[str] | None = None
    ) -> None:
        """
        Share knowledge with all agents.

        Args:
            key: Knowledge key (e.g., "user_preference_theme")
            value: Knowledge value
            tags: Optional tags for categorization
        """
        from tools.inter_agent_comm import share_knowledge

        share_knowledge(
            key=key,
            value=value,
            source_agent=self.role.value,
            tags=tags or [],
        )

    def get_shared_knowledge(self, key: str | None = None) -> Any:
        """
        Get shared knowledge.
        
        Args:
            key: Knowledge key (None for all knowledge)
            
        Returns:
            Knowledge value or dict of all knowledge
        """
        from tools.inter_agent_comm import get_shared_knowledge, get_message_bus
        if key:
            return get_shared_knowledge(key)
        else:
            bus = self._get_message_bus()
            return bus.get_all_knowledge()
    
    def suggest_collaborator(self, task_type: str) -> Optional[str]:
        """
        Suggest a collaborator agent for a task type.
        
        Args:
            task_type: Type of task (research, analysis, code, math, review)
            
        Returns:
            Suggested agent role or None
        """
        from tools.inter_agent_comm import suggest_collaborator
        return suggest_collaborator(self.role.value, task_type)

    def _emit(self, event_type: str, content: str, **extra):
        """Emit event to live monitor if attached."""
        if self._live_monitor:
            try:
                self._live_monitor.emit(event_type, self.role.value, content, **extra)
            except Exception:
                pass  # Never let UI updates break execution

    def _tool_error(self, code: str, message: str, recovery: str | None = None) -> str:
        """Return structured, recovery-friendly tool error messages for the LLM."""
        msg = f"[tool_error:{code}] {message}"
        if recovery:
            msg += f" | recovery: {recovery}"
        return msg

    def _normalize_tool_args(
        self, fn_name: str, fn_args: dict[str, Any]
    ) -> dict[str, Any]:
        """Clamp and sanitize common tool parameters to safe ranges."""
        args = dict(fn_args)

        if "max_results" in args:
            try:
                args["max_results"] = max(1, min(20, int(args["max_results"])))
            except Exception:
                args["max_results"] = 5

        if "max_chars" in args:
            try:
                args["max_chars"] = max(200, min(30000, int(args["max_chars"])))
            except Exception:
                args["max_chars"] = 8000

        if fn_name == "generate_image":
            try:
                args["width"] = max(256, min(2048, int(args.get("width", 800))))
            except Exception:
                args["width"] = 800
            try:
                args["height"] = max(256, min(2048, int(args.get("height", 450))))
            except Exception:
                args["height"] = 450

        if fn_name == "generate_chart":
            try:
                args["width"] = max(400, min(1600, int(args.get("width", 800))))
            except Exception:
                args["width"] = 800
            try:
                args["height"] = max(300, min(1200, int(args.get("height", 450))))
            except Exception:
                args["height"] = 450

        return args

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

        # Progress tracking başlat (Faz 10.5)
        from tools.agent_progress_tracker import get_tracker, AgentStatus

        tracker = get_tracker()
        agent_id = f"{self.role.value}_{uuid_module.uuid4().hex[:8]}"
        tracker.start_task(agent_id, self.role.value, thread.id)
        tracker.update_step(
            agent_id,
            "init",
            "Görev başlatıldı",
            AgentStatus.THINKING,
            progress_percent=10,
        )
        self._emit("agent_start", f"Görev alındı: {task_input[:80]}")

        messages = await self.build_context(thread, task_input)
        tools = self.get_tools()

        # Adaptive Tool Selector — record tool usage for learning (Faz 12)
        try:
            from tools.adaptive_tool_selector import get_adaptive_tool_selector
            _ats = get_adaptive_tool_selector()
        except Exception:
            _ats = None

        # Agentic Loop (Faz 11.1 + 14.6): token/cost guards + context compression + transforms + steering + follow-up
        from agents.agentic_loop import (
            get_loop_config,
            check_guards,
            compress_messages_if_needed,
            cost_per_1k_for_model,
            get_default_transformer,
            get_followup_config,
        )

        loop_config = get_loop_config()
        context_transformer = get_default_transformer()
        followup_config = get_followup_config()
        max_steps_loop = min(self.max_steps, loop_config.max_iterations)
        cumulative_tokens = 0
        cumulative_cost_usd = 0.0
        token_usage_unknown = False
        token_usage_reasons: set[str] = set()
        cost_per_1k = cost_per_1k_for_model(self.cfg.get("id", ""))
        follow_up_count = 0

        for step in range(max_steps_loop):
            # Guard: iteration, token budget, cost — soft warning only, never hard-stop
            guard = check_guards(
                step, cumulative_tokens, cumulative_cost_usd, loop_config
            )
            if not guard.ok:
                thread.add_event(
                    EventType.AGENT_THINKING,
                    f"Loop guard warning: {guard.reason} (tokens={cumulative_tokens}, cost=${cumulative_cost_usd:.4f}) — devam ediliyor",
                    agent_role=self.role,
                )
                self._emit("warning", f"Guard: {guard.reason} — devam ediliyor")

            # Check stop request
            if self._live_monitor and self._live_monitor.should_stop():
                thread.add_event(EventType.ERROR, "User requested stop", agent_role=self.role)
                try:
                    tracker.set_error(agent_id, "Kullanıcı durdurdu")
                except Exception:
                    pass
                return "[Stopped] Kullanıcı tarafından durduruldu."

            # Context Window Guard: compress if too many messages
            messages = compress_messages_if_needed(messages, loop_config)

            # Faz 14.6: Context Transformer — apply pluggable transforms before LLM call
            messages = context_transformer.apply(messages, loop_config)

            # Faz 14.6: Steering Messages — inject user steering if available
            if self._live_monitor and hasattr(self._live_monitor, '_steering_queue'):
                steering_msg = self._live_monitor._steering_queue.pop()
                if steering_msg:
                    messages.append({
                        "role": "user",
                        "content": f"[STEERING — Kullanıcı talimatı] {steering_msg}",
                    })
                    thread.add_event(
                        EventType.AGENT_THINKING,
                        f"Steering message injected: {steering_msg[:100]}",
                        agent_role=self.role,
                    )
                    self._emit(
                        "steering",
                        f"Kullanıcı talimatı alındı: {steering_msg[:80]}",
                        queue_standard="v2",
                        steering_applied=True,
                    )

            # Retry mechanism for LLM calls
            from tools.agent_retry import (
                RetryConfig,
                should_retry,
                classify_error,
                record_failure,
                record_success,
            )
            
            retry_config = RetryConfig()
            last_error = None
            
            for retry_attempt in range(retry_config.max_retries + 1):
                try:
                    result = await self.call_llm(messages, tools)
                    # Success - record and continue
                    record_success(self.role.value, None)  # type: ignore
                    break
                except Exception as e:
                    last_error = e
                    error_str = f"{type(e).__name__}: {e}"
                    
                    # Check if should retry
                    should, delay = should_retry(e, retry_attempt, retry_config)
                    
                    if not should:
                        # Permanent error - don't retry
                        error_msg = f"LLM call failed permanently: {error_str}"
                        thread.add_event(EventType.ERROR, error_msg, agent_role=self.role)
                        thread.update_metrics(self.role, 0, 0, success=False)
                        self._emit("error", error_msg)
                        try:
                            tracker.set_error(agent_id, error_msg[:200])
                        except Exception:
                            pass
                        return f"[Error] {error_msg}"
                    
                    # Log retry attempt
                    thread.add_event(
                        EventType.AGENT_THINKING,
                        f"LLM call failed (attempt {retry_attempt + 1}), retrying in {delay:.0f}ms: {error_str[:100]}",
                        agent_role=self.role,
                    )
                    self._emit("warning", f"Retry {retry_attempt + 1}: {error_str[:80]}")
                    
                    # Wait before retry
                    if delay > 0:
                        await asyncio.sleep(delay / 1000)
            else:
                # All retries exhausted
                error_msg = f"LLM call failed after {retry_config.max_retries} retries: {last_error}"
                thread.add_event(EventType.ERROR, error_msg, agent_role=self.role)
                thread.update_metrics(self.role, 0, 0, success=False)
                record_failure(self.role.value, None)  # type: ignore
                return f"[Error] {error_msg}"

            # Track thinking content
            if result.get("thinking"):
                thread.add_event(
                    EventType.AGENT_THINKING,
                    result["thinking"][:500],
                    agent_role=self.role,
                )
                self._emit("thinking", result["thinking"][:5000] if len(result["thinking"]) > 5000 else result["thinking"])

            # Handle tool calls
            if result["tool_calls"]:
                _used_tools: list[str] = []
                for tc in result["tool_calls"]:
                    fn_name = tc.function.name
                    _used_tools.append(fn_name)
                    raw_args = getattr(tc.function, "arguments", "{}")
                    args_for_message = (
                        raw_args
                        if isinstance(raw_args, str)
                        else json.dumps(raw_args, ensure_ascii=False)
                    )

                    parse_error = None
                    if isinstance(raw_args, dict):
                        fn_args = raw_args
                    elif isinstance(raw_args, str):
                        try:
                            fn_args = json.loads(raw_args) if raw_args.strip() else {}
                            if not isinstance(fn_args, dict):
                                parse_error = "Tool arguments must be a JSON object"
                                fn_args = {}
                        except json.JSONDecodeError as e:
                            parse_error = f"Invalid JSON arguments: {e}"
                            fn_args = {}
                    else:
                        parse_error = (
                            f"Unsupported argument type: {type(raw_args).__name__}"
                        )
                        fn_args = {}

                    fn_args = self._normalize_tool_args(fn_name, fn_args)
                    args_preview = json.dumps(fn_args, ensure_ascii=False)

                    # Faz 14.3: Validate tool arguments against JSON Schema
                    validation_error_msg = None
                    if not parse_error:
                        try:
                            from tools.tool_schema_registry import validate_tool_args
                            vr = validate_tool_args(fn_name, fn_args)
                            if not vr.get("valid"):
                                validation_error_msg = vr.get("correction_prompt", "Invalid tool arguments.")
                        except ImportError:
                            pass  # jsonschema not available — skip validation

                    thread.add_event(
                        EventType.TOOL_CALL,
                        f"{fn_name}({args_preview[:200]})",
                        agent_role=self.role,
                    )
                    self._emit(
                        "tool_call",
                        args_preview[:120],
                        tool_name=fn_name,
                    )

                    if parse_error:
                        _tool_latency_ms = 0.0
                        self._emit(
                            "tool_validation",
                            parse_error[:150],
                            tool_name=fn_name,
                            validation_status="failed",
                            validation_code="invalid_tool_arguments",
                        )
                        tool_result = self._tool_error(
                            "invalid_tool_arguments",
                            parse_error,
                            "Call the same tool again with valid JSON object arguments.",
                        )
                    elif validation_error_msg:
                        _tool_latency_ms = 0.0
                        self._emit(
                            "tool_validation",
                            validation_error_msg[:150],
                            tool_name=fn_name,
                            validation_status="failed",
                            validation_code="schema_validation_failed",
                        )
                        tool_result = self._tool_error(
                            "schema_validation_failed",
                            validation_error_msg,
                            None,
                        )
                    else:
                        self._emit(
                            "tool_validation",
                            f"{fn_name} args validated",
                            tool_name=fn_name,
                            validation_status="passed",
                            validation_code="ok",
                        )
                        try:
                            _tool_t0 = time.monotonic()
                            tool_result = await self.handle_tool_call(
                                fn_name, fn_args, thread
                            )
                            _tool_latency_ms = (time.monotonic() - _tool_t0) * 1000
                        except KeyError as e:
                            _tool_latency_ms = (time.monotonic() - _tool_t0) * 1000
                            tool_result = self._tool_error(
                                "missing_required_argument",
                                f"Missing required argument: {e}",
                                "Check tool schema and provide all required fields.",
                            )
                        except Exception as e:
                            _tool_latency_ms = (time.monotonic() - _tool_t0) * 1000
                            tool_result = self._tool_error(
                                "tool_execution_failed",
                                f"{type(e).__name__}: {e}",
                                "Try smaller input, adjust parameters, or use an alternative tool.",
                            )

                    thread.add_event(
                        EventType.TOOL_RESULT,
                        str(tool_result)[:500],
                        agent_role=self.role,
                    )
                    _is_tool_error = isinstance(tool_result, dict) and tool_result.get("error")
                    self._emit(
                        "tool_result",
                        str(tool_result)[:150],
                        tool_name=fn_name,
                        tool_success=not _is_tool_error,
                    )

                    # Adaptive Tool Selector: record tool usage
                    if _ats:
                        try:
                            error_message = (
                                tool_result.get("error", "")
                                if isinstance(tool_result, dict)
                                else ""
                            )
                            _is_err = bool(error_message)
                            if _is_err:
                                _ats.record_failure(
                                    self.role.value,
                                    fn_name,
                                    task_input,
                                    str(error_message)[:200],
                                )
                            else:
                                _ats.record_success(self.role.value, fn_name, task_input)
                        except Exception:
                            pass

                    # Record to PostgreSQL tool_usage table for MCP usage panel
                    try:
                        from tools.pg_connection import get_conn, release_conn, postgres_available
                        if postgres_available():
                            _pg = get_conn()
                            try:
                                with _pg.cursor() as _cur:
                                    _cur.execute(
                                        """INSERT INTO tool_usage
                                           (tool_name, agent_role, latency_ms, success, tokens_used, user_id, timestamp)
                                           VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
                                        (
                                            fn_name,
                                            self.role.value,
                                            round(_tool_latency_ms, 1),
                                            0 if _is_tool_error else 1,
                                            0,
                                            getattr(thread, 'user_id', 'system'),
                                        ),
                                    )
                                _pg.commit()
                            finally:
                                release_conn(_pg)
                    except Exception:
                        pass  # Non-critical — don't break tool execution

                    # Append to messages for next LLM turn
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": fn_name,
                                        "arguments": args_for_message,
                                    },
                                }
                            ],
                        }
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(tool_result),
                    })
                # Track tokens and cost for this LLM call (result from last call_llm)
                tok = result.get("tokens_total")
                if isinstance(tok, int):
                    cumulative_tokens += tok
                    cumulative_cost_usd += (tok / 1000.0) * cost_per_1k
                else:
                    token_usage_unknown = True
                    token_usage_reasons.add(
                        str(result.get("token_usage_reason") or "provider_usage_missing")
                    )
                # Canlı ilerleme: bu döngü adımı sonrası güncelle
                progress_pct = min(90, 10 + (step + 1) * 25)
                _tools_label = ", ".join(_used_tools[-3:]) if _used_tools else "?"
                tracker.update_step(
                    agent_id,
                    f"step_{step}",
                    f"🔧 {_tools_label} (adım {step + 1})",
                    AgentStatus.EXECUTING,
                    progress_percent=progress_pct,
                )
                continue  # Back to LLM with tool results

            # Final response — break the loop
            content = result["content"]
            # Track final turn tokens/cost
            final_tok = result.get("tokens_total")
            if isinstance(final_tok, int):
                cumulative_tokens += final_tok
                cumulative_cost_usd += (final_tok / 1000.0) * cost_per_1k
            else:
                token_usage_unknown = True
                token_usage_reasons.add(
                    str(result.get("token_usage_reason") or "provider_usage_missing")
                )
            event_tokens = result.get("tokens_total")
            thread.add_event(
                EventType.AGENT_RESPONSE,
                content,
                agent_role=self.role,
                tokens=event_tokens,
                token_usage_status=result.get("token_usage_status", "unknown"),
                token_usage_reason=result.get("token_usage_reason"),
                latency_ms=result["latency_ms"],
                step=step,
            )
            thread.update_metrics(
                self.role,
                int(event_tokens) if isinstance(event_tokens, int) else 0,
                result["latency_ms"],
                success=True,
            )
            self._emit("response", content[:20000] if len(content) > 20000 else content)

            # Adaptive Tool Selector: record agent-level success
            if _ats:
                try:
                    _ats.record_success(self.role.value, f"agent:{self.role.value}", task_input)
                except Exception:
                    pass

            # Canlı ilerleme: görev tamamlandı
            tracker.complete_task(agent_id)

            # Faz 11.6: memory.md is for agent character development only.
            # Task memory goes to Qdrant (continual-learning tag).
            # No auto-dump of task completions to memory.md.

            # Record task completion to user_behavior table for agent self-improvement
            try:
                from tools.pg_connection import get_conn, release_conn
                _bconn = get_conn()
                try:
                    with _bconn.cursor() as _bcur:
                        _bcur.execute(
                            """INSERT INTO user_behavior (action, context, metadata, user_id, timestamp)
                               VALUES (%s, %s, %s, %s, %s)""",
                            (
                                "agent_task_complete",
                                task_input[:200],
                                json.dumps(
                                    {
                                        "agent": self.role.value,
                                        "model": self.cfg.get("id", ""),
                                        "tokens": None if token_usage_unknown else cumulative_tokens,
                                        "token_usage_status": "unknown" if token_usage_unknown else "known",
                                        "token_usage_reason": ",".join(sorted(token_usage_reasons)) if token_usage_unknown else None,
                                        "cost_usd": round(cumulative_cost_usd, 6),
                                        "steps": step + 1,
                                    }
                                ),
                                getattr(thread, "user_id", "system"),
                                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            ),
                        )
                    _bconn.commit()
                finally:
                    release_conn(_bconn)
            except Exception:
                pass  # non-critical — never break agent flow

            # Faz 14.6: Follow-up Messages — auto-continue if agent signals continuation
            if (
                followup_config.enabled
                and follow_up_count < followup_config.max_follow_ups
                and followup_config.should_follow_up(content)
            ):
                follow_up_count += 1
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": followup_config.follow_up_message,
                })
                self._emit("follow_up", f"Otomatik devam #{follow_up_count}")
                self._emit(
                    "follow_up",
                    f"Otomatik devam #{follow_up_count}",
                    follow_up_count=follow_up_count,
                    queue_standard="v2",
                )
                thread.add_event(
                    EventType.AGENT_THINKING,
                    f"Auto follow-up #{follow_up_count}: response indicated continuation",
                    agent_role=self.role,
                )
                continue  # Back to LLM for continuation

            # ── Reflexion: Self-evaluation and improvement ───────────────
            # Quality-critical roles get multi-iteration agentic eval;
            # others get the standard single-pass reflexion.
            try:
                import config
                if config.REFLEXION_ENABLED:
                    from tools.reflexion import evaluate_and_improve

                    _quality_critical_roles = {"thinker", "reasoner", "researcher"}
                    _max_iter = (
                        config.REFLEXION_MAX_ITERATIONS
                        if self.role.value not in _quality_critical_roles
                        else max(config.REFLEXION_MAX_ITERATIONS, 2)
                    )

                    content, reflexion_eval = await evaluate_and_improve(
                        agent=self,
                        question=task_input,
                        response=content,
                        threshold=config.REFLEXION_SCORE_THRESHOLD,
                        max_iterations=_max_iter,
                    )
                    if reflexion_eval:
                        _is_agentic = reflexion_eval.get("agentic_eval", False)
                        _scores = reflexion_eval.get("scores", {})
                        _score_sum = sum(_scores.values()) if _scores else 0
                        _score_count = len(_scores) if _scores else 1
                        thread.add_event(
                            EventType.AGENT_THINKING,
                            f"Reflexion{'(rubric)' if _is_agentic else ''}: "
                            f"avg_score={_score_sum / max(_score_count, 1):.1f}/5",
                            agent_role=self.role,
                        )
            except Exception as e:
                logger.debug(f"Reflexion skipped: {e}")

            return content

        # Max steps reached — treat as normal completion with note
        thread.add_event(
            EventType.AGENT_RESPONSE,
            f"Görev tamamlandı (maks adım: {max_steps_loop}, tokens: {cumulative_tokens})",
            agent_role=self.role,
        )
        thread.update_metrics(self.role, cumulative_tokens, 0, success=True)
        try:
            tracker.complete_task(agent_id)
        except Exception:
            pass
        return f"Görev tamamlandı — {max_steps_loop} adımda işlendi."

    async def handle_tool_call(self, fn_name: str, fn_args: dict, thread: Thread) -> str:
        """
        Handle tool calls — shared tools first, then subclass-specific.
        Override _handle_custom_tool in subclasses for agent-specific tools.
        """
        # Sandbox validation — block unauthorized or dangerous tool calls
        try:
            from tools.sandbox import validate_tool_call, SandboxViolation
            validate_tool_call(self.role.value, fn_name, fn_args)
        except SandboxViolation as e:
            thread.add_event(EventType.ERROR, str(e), agent_role=self.role)
            return f"[Sandbox] {e}"
        except Exception:
            pass  # Never break tool flow for sandbox import/init errors

        # Inter-Agent Communication Tools
        if fn_name == "send_agent_message":
            try:
                msg_id = await self.send_agent_message(
                    to_agent=fn_args["to_agent"],
                    content=fn_args["content"],
                    message_type=fn_args.get("message_type", "direct"),
                    metadata=fn_args.get("context"),
                    requires_response=fn_args.get("requires_response", False),
                )
                return f"[Inter-Agent] Message sent to {fn_args['to_agent']} (ID: {msg_id})"
            except Exception as e:
                return f"[Inter-Agent Error] Failed to send message: {e}"

        if fn_name == "check_agent_messages":
            try:
                messages = await self.receive_agent_messages(timeout=0.1)
                if not messages:
                    return "[Inter-Agent] No pending messages"
                result = f"[Inter-Agent] {len(messages)} pending messages:\n"
                for msg in messages:
                    result += f"- From {msg.from_agent}: {msg.content[:100]}...\n"
                return result
            except Exception as e:
                return f"[Inter-Agent Error] Failed to check messages: {e}"

        if fn_name == "share_knowledge":
            try:
                self.share_knowledge(
                    key=fn_args["key"],
                    value=fn_args["value"],
                    tags=fn_args.get("tags"),
                )
                return f"[Shared Knowledge] Key '{fn_args['key']}' shared with all agents"
            except Exception as e:
                return f"[Shared Knowledge Error] {e}"

        if fn_name == "get_shared_knowledge":
            try:
                key = fn_args.get("key")
                if key:
                    value = self.get_shared_knowledge(key)
                    if value is None:
                        return f"[Shared Knowledge] No value for key '{key}'"
                    return f"[Shared Knowledge] {key}: {value}"
                else:
                    all_knowledge = self.get_shared_knowledge()
                    if not all_knowledge:
                        return "[Shared Knowledge] No shared knowledge available"
                    result = "[Shared Knowledge] All knowledge:\n"
                    for k, v in all_knowledge.items():
                        result += f"- {k}: {str(v)[:100]}\n"
                    return result
            except Exception as e:
                return f"[Shared Knowledge Error] {e}"

        if fn_name == "suggest_collaborator":
            try:
                suggested = self.suggest_collaborator(fn_args["task_type"])
                if suggested:
                    return f"[Collaborator Suggestion] For '{fn_args['task_type']}' tasks, consider asking: {suggested}"
                return f"[Collaborator Suggestion] No specific collaborator for '{fn_args['task_type']}'"
            except Exception as e:
                return f"[Collaborator Suggestion Error] {e}"

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

            results = await recall_memory(
                query=fn_args["query"],
                category=fn_args.get("category"),
                max_results=fn_args.get("max_results", 5),
            )
            return format_recall_results(results)

        if fn_name == "list_memories":
            from tools.memory import list_memories

            memories = await list_memories(
                category=fn_args.get("category"),
                layer=fn_args.get("layer"),
                limit=fn_args.get("limit", 20),
            )
            if not memories:
                return "No memories found for the given filters."
            lines = [f"Found {len(memories)} memories:"]
            for i, mem in enumerate(memories, 1):
                lines.append(
                    f"{i}. [{mem.get('category')}|{mem.get('memory_layer')}] "
                    f"{str(mem.get('content', ''))[:220]}"
                )
            return "\n".join(lines)

        if fn_name == "memory_stats":
            from tools.memory import get_memory_stats

            stats = await get_memory_stats()
            return json.dumps(stats, ensure_ascii=False, indent=2)

        if fn_name == "memory_advanced_search":
            from tools.memory import advanced_recall
            results = await advanced_recall(
                query=fn_args["query"],
                tags=fn_args.get("tags"),
                date_from=fn_args.get("date_from"),
                date_to=fn_args.get("date_to"),
                similarity_threshold=fn_args.get("similarity_threshold", 0.6),
                memory_type=fn_args.get("memory_type"),
                limit=fn_args.get("limit", 10),
            )
            return json.dumps(results, ensure_ascii=False, default=str, indent=2)

        if fn_name == "memory_add_tags":
            from tools.memory import add_tags
            result = add_tags(
                memory_id=fn_args["memory_id"],
                tags=fn_args["tags"],
            )
            return json.dumps(result, ensure_ascii=False)

        if fn_name == "memory_remove_tags":
            from tools.memory import remove_tags
            result = remove_tags(
                memory_id=fn_args["memory_id"],
                tags=fn_args["tags"],
            )
            return json.dumps(result, ensure_ascii=False)

        if fn_name == "memory_list_tags":
            from tools.memory import list_all_tags
            tags = list_all_tags()
            return json.dumps(tags, ensure_ascii=False, indent=2)

        if fn_name == "find_skill":
            # Try dynamic registry first, fallback to static
            try:
                from tools.dynamic_skills import search_skills
                skills = search_skills(
                    query=fn_args["query"],
                    max_results=fn_args.get("max_results", 3),
                )
                if skills:
                    from tools.skill_finder import format_skill_results
                    return format_skill_results(skills)
            except Exception:
                pass
            from tools.skill_finder import find_skills, format_skill_results
            skills = find_skills(
                query=fn_args["query"],
                max_results=fn_args.get("max_results", 3),
            )
            return format_skill_results(skills)

        if fn_name == "use_skill":
            # Try disk-based Kiro skill package first, then DB, then static
            try:
                from tools.dynamic_skills import load_skill_package, get_full_skill_context
                pkg = load_skill_package(fn_args["skill_id"])
                if pkg:
                    knowledge = pkg.get("knowledge", "")
                    # Enrich with reference files
                    ref_ctx = ""
                    if pkg.get("references"):
                        from tools.dynamic_skills import load_skill_reference
                        for ref_name in pkg["references"][:5]:
                            ref_text = load_skill_reference(fn_args["skill_id"], ref_name)
                            if ref_text:
                                ref_ctx += f"\n\n## Reference: {ref_name}\n{ref_text[:3000]}"
                    full_knowledge = knowledge + ref_ctx if ref_ctx else knowledge
                    if full_knowledge:
                        from tools.skill_finder import format_skill_knowledge
                        return format_skill_knowledge(fn_args["skill_id"], full_knowledge)
                # Fallback: full context from DB + disk references
                ctx = get_full_skill_context(fn_args["skill_id"])
                if ctx:
                    from tools.skill_finder import format_skill_knowledge
                    return format_skill_knowledge(fn_args["skill_id"], ctx)
            except Exception:
                pass
            from tools.skill_finder import get_skill_knowledge, format_skill_knowledge
            knowledge = get_skill_knowledge(fn_args["skill_id"])
            if knowledge:
                return format_skill_knowledge(fn_args["skill_id"], knowledge)
            return f"Skill '{fn_args['skill_id']}' not found."

        if fn_name == "code_execute":
            from tools.code_executor import execute_code, format_execution_result
            result = await execute_code(
                code=fn_args["code"],
                language=fn_args.get("language", "python"),
            )
            return format_execution_result(result)

        if fn_name == "rag_ingest":
            from tools.rag import ingest_document

            result = await ingest_document(
                content=fn_args["content"],
                title=fn_args["title"],
                source=fn_args.get("source", "agent_input"),
            )
            if result["success"]:
                return f"Document ingested: '{result['title']}' — {result['chunks']} chunks, {result['embedded']} embedded"
            return f"Ingest failed: {result.get('error', 'unknown')}"

        if fn_name == "rag_query":
            from tools.rag import query_documents, format_rag_results

            results = await query_documents(
                query=fn_args["query"],
                max_results=fn_args.get("max_results", 5),
            )
            return format_rag_results(results)

        if fn_name == "rag_list_documents":
            from tools.rag import list_documents

            docs = list_documents(
                limit=fn_args.get("limit", 20), user_id=fn_args.get("user_id")
            )
            if not docs:
                return "No documents ingested yet."
            lines = [f"Found {len(docs)} documents:"]
            for i, d in enumerate(docs, 1):
                lines.append(
                    f"{i}. [{d.get('id')}] {d.get('title', 'Untitled')} | "
                    f"chunks={d.get('chunk_count', 0)} | source={d.get('source', '-')}"
                )
            return "\n".join(lines)

        if fn_name == "list_teachings":
            from tools.teachability import get_all_teachings

            teachings = get_all_teachings(active_only=fn_args.get("active_only", True))
            if not teachings:
                return "No teachings found."
            lines = [f"Found {len(teachings)} teachings:"]
            for i, t in enumerate(teachings, 1):
                lines.append(
                    f"{i}. [{t.get('category')}] {str(t.get('instruction', ''))[:220]}"
                )
            return "\n".join(lines)

        if fn_name == "request_approval":
            from tools.human_loop import create_approval_request, format_approval_for_agent
            request = create_approval_request(
                action=fn_args["action"],
                description=fn_args["description"],
                details=fn_args.get("details"),
                agent_role=self.role.value,
                thread=thread,
            )
            # Auto-approve in non-interactive mode (agents can't wait for UI)
            request.approve("Auto-approved (non-interactive mode)")
            return format_approval_for_agent(request)

        if fn_name == "spawn_subagent":
            from tools.spawn_subagent import run_subagent
            task = fn_args.get("task", "")
            role = fn_args.get("role_description", "")
            skill_ids = fn_args.get("skill_ids") or []
            model_key = fn_args.get("model_key") or "thinker"
            if not task or not role:
                return "[spawn_subagent] task and role_description are required."
            result = await run_subagent(
                task=task,
                role_description=role,
                skill_ids=skill_ids,
                model_key=model_key,
            )
            return f"[Subagent result]\n{result}"

        if fn_name == "get_agent_baseline":
            from tools.agent_eval import get_performance_baseline
            baseline = get_performance_baseline(fn_args.get("agent_role"))
            return (
                f"Performance baseline ({baseline.get('agent_role') or 'system-wide'}): "
                f"task_success_rate={baseline['task_success_rate_pct']}%, "
                f"user_satisfaction={baseline['user_satisfaction_score']}/10, "
                f"avg_latency_ms={baseline['avg_latency_ms']}, "
                f"token_ratio={baseline['token_efficiency_ratio']}, "
                f"total_tasks={baseline['total_tasks']}, success_count={baseline['success_count']}. "
                "Use for improvement targets: +15% success, -25% corrections, no safety regression."
            )

        if fn_name == "get_best_agent":
            from tools.agent_eval import get_best_agent_for_task
            task_type = fn_args.get("task_type") or "general"
            best = get_best_agent_for_task(task_type)
            if best:
                return f"Best agent for task_type '{task_type}': {best}. Prefer assigning this agent."
            return f"No sufficient evaluation data for task_type '{task_type}'. Use default assignment."

        if fn_name == "self_evaluate":
            from tools.reflexion import build_evaluation_prompt
            eval_prompt = build_evaluation_prompt(
                question=fn_args["question"],
                response=fn_args["response"],
            )
            return f"Self-evaluation prompt ready. Evaluate:\n{eval_prompt[:500]}"

        if fn_name == "mcp_call":
            from tools.mcp_client import call_mcp_tool
            result = await call_mcp_tool(
                server_id=fn_args["server_id"],
                tool_name=fn_args["tool_name"],
                arguments=fn_args.get("arguments"),
            )
            if result["success"]:
                return f"[MCP:{result['server']}:{result['tool']}] {result['output']}"
            return f"[MCP Error] {result.get('error', 'unknown')}"

        if fn_name == "mcp_list_tools":
            from tools.mcp_client import format_mcp_tools_for_agent, list_servers, list_discovered_tools, discover_tools as _discover
            server_id = fn_args.get("server_id")
            formatted = format_mcp_tools_for_agent(server_id)
            if formatted:
                return formatted
            # No tools cached — try on-demand discovery
            servers = list_servers(active_only=True)
            if not servers:
                return "No MCP servers registered. Use the MCP panel to add servers."
            discovered = 0
            for srv in servers:
                try:
                    tools = await _discover(srv["id"])
                    discovered += len(tools)
                except Exception:
                    pass
            if discovered:
                formatted = format_mcp_tools_for_agent(server_id)
                if formatted:
                    return formatted
            return (
                f"{len(servers)} MCP servers registered but tool discovery returned 0 tools. "
                "Servers may not be installed locally (npx/uvx required). "
                "Available servers: " + ", ".join(s["name"] for s in servers)
            )

        if fn_name == "generate_image":
            import urllib.parse
            import httpx
            import os
            prompt = fn_args["prompt"]
            width = fn_args.get("width", 800)
            height = fn_args.get("height", 450)
            model = (fn_args.get("model") or "flux").lower().strip()
            if model not in {"flux", "zimage", "turbo", "imagen-4", "grok-imagine"}:
                model = "flux"
            encoded_prompt = urllib.parse.quote(prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model}&width={width}&height={height}"
            # Download image to data/images/
            images_dir = os.path.join("data", "images")
            os.makedirs(images_dir, exist_ok=True)
            filename = f"img_{uuid_module.uuid4().hex[:10]}.jpg"
            filepath = os.path.join(images_dir, filename)
            last_error = None

            async def _try_download(
                url: str, timeout: float, headers: dict | None = None
            ) -> tuple[bool, str | None]:
                nonlocal last_error
                for _ in range(3):
                    try:
                        async with httpx.AsyncClient(
                            timeout=timeout, follow_redirects=True
                        ) as client:
                            resp = await client.get(url, headers=headers)
                            if resp.status_code == 200 and len(resp.content) > 1000:
                                with open(filepath, "wb") as f:
                                    f.write(resp.content)
                                return True, None
                            if resp.status_code == 200:
                                last_error = "Response too small"
                            else:
                                last_error = f"HTTP {resp.status_code}"
                    except Exception as e:
                        last_error = str(e)
                    await asyncio.sleep(2)
                return False, last_error

            # Prefer authenticated generation endpoint when API key is available.
            api_key = (
                os.environ.get("POLLINATIONS_API_KEY")
                or os.environ.get("Pollinations_api_key")
                or ""
            ).strip()
            if api_key:
                gen_url = (
                    f"https://gen.pollinations.ai/image/{encoded_prompt}"
                    f"?model={model}&width={width}&height={height}&nologo=true&enhance=true"
                )
                ok, _ = await _try_download(
                    gen_url,
                    timeout=65.0,
                    headers={
                        "Accept": "image/jpeg, image/png",
                        "Authorization": f"Bearer {api_key}",
                    },
                )
                if not ok and model != "flux":
                    flux_url = (
                        f"https://gen.pollinations.ai/image/{encoded_prompt}"
                        f"?model=flux&width={width}&height={height}&nologo=true&enhance=true"
                    )
                    ok, _ = await _try_download(
                        flux_url,
                        timeout=65.0,
                        headers={
                            "Accept": "image/jpeg, image/png",
                            "Authorization": f"Bearer {api_key}",
                        },
                    )
                if ok:
                    download_url = f"/api/images/{filename}/download"
                    return (
                        f"Image generated successfully.\n\n"
                        f"![{prompt}]({image_url})\n\n"
                        f"**Download:** [{filename}]({download_url})\n\n"
                        f"Direct URL: {image_url}"
                    )

            # Public endpoint fallback.
            ok, _ = await _try_download(image_url, timeout=20.0)
            if ok:
                download_url = f"/api/images/{filename}/download"
                return (
                    f"Image generated successfully.\n\n"
                    f"![{prompt}]({image_url})\n\n"
                    f"**Download:** [{filename}]({download_url})\n\n"
                    f"Direct URL: {image_url}"
                )

            # All download attempts failed — still provide direct URL.
            return (
                f"Image URL generated, but automatic download is currently unavailable ({last_error}).\n\n"
                f"![{prompt}]({image_url})\n\n"
                f"Direct URL: {image_url}"
            )

        if fn_name == "generate_chart":
            from tools.chart_generator import generate_chart as run_generate_chart

            chart_type = (fn_args.get("chart_type") or "bar").lower().strip()
            data = fn_args.get("data")
            if not isinstance(data, dict):
                data = {}
            title = fn_args.get("title") or f"{chart_type} chart"
            width = fn_args.get("width", 800)
            height = fn_args.get("height", 450)
            try:
                out = run_generate_chart(
                    chart_type=chart_type,
                    data=data,
                    title=title,
                    width=width,
                    height=height,
                )
                if out.get("error"):
                    return self._tool_error(
                        "chart_generation_failed",
                        out["error"],
                        "Fix data shape and retry.",
                    )
                cid = out.get("chart_id", "")
                b64 = out.get("image_base64", "")
                return (
                    f"Chart generated successfully.\n"
                    f"- **chart_id:** {cid}\n"
                    f"- **title:** {out.get('title', title)}\n"
                    f"- **type:** {out.get('chart_type', chart_type)}\n"
                    f"- View/download: dashboard Grafik panel or API GET /api/charts/{cid}.\n"
                )
            except Exception as e:
                return self._tool_error(
                    "chart_generation_failed",
                    str(e),
                    "Check chart_type and data format, then retry.",
                )

        if fn_name == "check_budget":
            from tools.cost_tracker import get_cost_tracker
            tracker = get_cost_tracker()
            hours = fn_args.get("hours", 24)
            summary = tracker.get_cost_summary(hours=hours)
            budget = tracker.check_budget()
            return (
                f"Cost summary (last {hours}h): "
                f"total=${summary.get('total_cost', 0):.4f}, "
                f"requests={summary.get('total_requests', 0)}, "
                f"input_tokens={summary.get('total_input_tokens', 0)}, "
                f"output_tokens={summary.get('total_output_tokens', 0)}. "
                f"Budget status: {'WITHIN LIMITS' if budget.get('within_budget', True) else 'OVER BUDGET'}. "
                f"Remaining: ${budget.get('remaining', 'unlimited')}"
            )

        if fn_name == "check_error_patterns":
            from tools.error_patterns import get_error_analyzer
            analyzer = get_error_analyzer()
            hours = fn_args.get("hours", 24)
            severity = fn_args.get("severity")
            patterns = analyzer.get_patterns()
            if severity:
                patterns = [p for p in patterns if p.get("severity") == severity]
            recommendations = analyzer.get_recommendations(hours=hours)
            if not patterns:
                return f"No error patterns detected in the last {hours}h."
            lines = [f"Found {len(patterns)} error patterns (last {hours}h):"]
            for p in patterns[:10]:
                lines.append(
                    f"- [{p.get('severity', '?')}] {p.get('pattern_type', '?')}: "
                    f"{p.get('message_sample', '')[:120]} (count={p.get('occurrence_count', 0)})"
                )
            if recommendations:
                lines.append(f"\nRecommendations ({len(recommendations)}):")
                for r in recommendations[:5]:
                    lines.append(f"- {r.get('recommendation', '')[:150]}")
            return "\n".join(lines)

        if fn_name == "create_skill":
            from tools.dynamic_skills import create_skill_package
            result = create_skill_package(
                skill_id=fn_args["skill_id"],
                name=fn_args["name"],
                description=fn_args["description"],
                knowledge=fn_args["knowledge"],
                category=fn_args.get("category", "capability"),
                keywords=fn_args.get("keywords", []),
                references=fn_args.get("references"),
                scripts=fn_args.get("scripts"),
                source=f"agent:{self.role.value}",
            )
            parts = [
                f"Skill package created: [{result['id']}] {result['name']} ({result['category']})",
                f"Path: {result.get('path', 'data/skills/' + result['id'])}",
            ]
            if result.get("has_references"):
                parts.append("References: included")
            if result.get("has_scripts"):
                parts.append("Scripts: included")
            parts.append(f"Inject into sub-tasks by adding '{result['id']}' to the skills list.")
            return "\n".join(parts)

        if fn_name == "ocr_extract":
            from tools.ocr_service import extract_text, format_ocr_result
            # Determine source from arguments
            file_path = fn_args.get("file_path")
            file_bytes = fn_args.get("file_bytes")
            filename = fn_args.get("filename")
            language = fn_args.get("lang", "eng")
            pages = fn_args.get("pages")
            extract_tables = fn_args.get("extract_tables", False)

            # Handle page list format
            if pages and isinstance(pages, list):
                pages = ",".join(str(p) for p in pages)

            if not file_path and not file_bytes:
                return self._tool_error(
                    "ocr_missing_source",
                    "Either file_path or file_bytes is required",
                    "Provide a file path or base64-encoded file content.",
                )

            # Prefer file_path, fallback to file_bytes
            if file_path:
                source = file_path
            else:
                source = file_bytes

            if source is None:
                return self._tool_error(
                    "extract_text",
                    "Either file_path or file_bytes is required",
                )

            result = await extract_text(
                source=source,
                source_type="auto",
                language=language,
                pages=pages,
                extract_tables=extract_tables,
            )

            if result.get("error"):
                return self._tool_error(
                    "ocr_extraction_failed",
                    result["error"],
                    "Verify the file exists and is a valid image or PDF. Check OCR dependencies.",
                )

            # Save output if requested
            if fn_args.get("save_output") and result.get("text"):
                import os
                output_dir = os.path.join("data", "ocr_output")
                os.makedirs(output_dir, exist_ok=True)
                import uuid
                output_filename = f"ocr_{uuid.uuid4().hex[:8]}.txt"
                output_path = os.path.join(output_dir, output_filename)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result["text"])
                result["saved_to"] = output_path

            return format_ocr_result(result)

        if fn_name == "ocr_status":
            from tools.ocr_service import _ensure_imports, _check_tesseract_installed, LANGUAGE_MAP
            import shutil

            _ensure_imports()

            status = {
                "available": True,
                "dependencies": {},
                "supported_formats": {
                    "images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"],
                    "pdfs": [".pdf"],
                },
                "languages": list(set(LANGUAGE_MAP.values())),
            }

            # Check PIL
            try:
                from PIL import Image
                status["dependencies"]["pillow"] = "installed"
            except ImportError:
                status["dependencies"]["pillow"] = "not installed"
                status["available"] = False

            # Check pytesseract
            try:
                import pytesseract
                status["dependencies"]["pytesseract"] = "installed"
            except ImportError:
                status["dependencies"]["pytesseract"] = "not installed"
                status["available"] = False

            # Check Tesseract binary
            if _check_tesseract_installed():
                status["dependencies"]["tesseract_binary"] = "installed"
                # Try to get installed languages
                try:
                    import pytesseract
                    langs = pytesseract.get_languages()
                    status["installed_languages"] = langs
                except Exception:
                    status["installed_languages"] = ["unknown"]
            else:
                status["dependencies"]["tesseract_binary"] = "not installed"
                status["available"] = False

            # Check pdfplumber
            try:
                import pdfplumber
                status["dependencies"]["pdfplumber"] = "installed"
            except ImportError:
                status["dependencies"]["pdfplumber"] = "not installed"
                # PDF support is optional, don't mark as unavailable

            # Format response
            if status["available"]:
                return (
                    f"OCR Service Status: AVAILABLE\n"
                    f"- Pillow: {status['dependencies'].get('pillow', 'unknown')}\n"
                    f"- pytesseract: {status['dependencies'].get('pytesseract', 'unknown')}\n"
                    f"- tesseract binary: {status['dependencies'].get('tesseract_binary', 'unknown')}\n"
                    f"- pdfplumber: {status['dependencies'].get('pdfplumber', 'not installed')}\n"
                    f"- Supported images: {', '.join(status['supported_formats']['images'])}\n"
                    f"- PDF support: {'yes' if status['dependencies'].get('pdfplumber') == 'installed' else 'no'}\n"
                    f"- Installed languages: {', '.join(status.get('installed_languages', ['eng']))}"
                )
            else:
                missing = [k for k, v in status["dependencies"].items() if v == "not installed"]
                return (
                    f"OCR Service Status: UNAVAILABLE\n"
                    f"Missing dependencies: {', '.join(missing)}\n"
                    f"Install with: pip install pytesseract pdfplumber Pillow && apt-get install tesseract-ocr"
                )

        # ── YouTube Summarizer Tool ─────────────────────────────────────
        if fn_name == "summarize_video":
            from tools.youtube_summarizer import summarize_video as yt_summarize, format_video_summary
            
            result = await yt_summarize(
                url=fn_args["url"],
                language=fn_args.get("language", "en"),
                target_language=fn_args.get("target_language"),
                use_whisper_fallback=fn_args.get("use_whisper_fallback", True),
                whisper_model=fn_args.get("whisper_model", "base"),
                max_transcript_chars=fn_args.get("max_transcript_chars", 10000),
            )
            
            if result.get("errors"):
                return format_video_summary(result)
            
            return format_video_summary(result)

        # ── YouTube Transcript Tool ─────────────────────────────────────
        if fn_name == "fetch_transcript":
            from tools.youtube_summarizer import (
                get_transcript,
                get_video_info,
            )

            url = fn_args["url"]
            target_language = fn_args.get("target_language")
            max_chars = fn_args.get("max_chars", 15000)

            import asyncio as _aio

            video_result, transcript_result = await _aio.gather(
                get_video_info(url),
                get_transcript(url, language="en", target_language=target_language),
                return_exceptions=True,
            )

            if isinstance(video_result, BaseException):
                video_result = {"success": False, "video_info": None}
            if isinstance(transcript_result, BaseException):
                return f"<error>Transcript fetch failed: {transcript_result}</error>"

            if not isinstance(video_result, dict) or not isinstance(
                transcript_result, dict
            ):
                return "<error>Unexpected transcript provider response</error>"

            if not transcript_result.get("success"):
                return f"<error>{transcript_result.get('error', 'Transcript unavailable')}</error>"

            info = video_result.get("video_info", {}) or {}
            t_data = transcript_result.get("transcript", {}) or {}
            full_text = t_data.get("full_text", "") if isinstance(t_data, dict) else ""
            lang = transcript_result.get("language", "en")
            source = transcript_result.get("source", "unknown")

            # Truncate if needed
            if len(full_text) > max_chars:
                full_text = full_text[:max_chars] + "\n\n[... truncated]"

            parts = [
                "<youtube_transcript>",
                f'  <video title="{info.get("title", "")}" channel="{info.get("uploader", "")}" />',
                f'  <transcript language="{lang}" source="{source}" words="{t_data.get("word_count", 0)}">',
                f"    {full_text}",
                "  </transcript>",
                "</youtube_transcript>",
            ]
            return "\n".join(parts)

        # ── Email Sender Tools ───────────────────────────────────────────
        if fn_name == "email_send":
            from tools.email_sender import send_email, format_email_result, SMTPConfig
            
            # Build SMTP config from args
            smtp_config = SMTPConfig(
                host=fn_args["smtp_host"],
                port=fn_args.get("smtp_port", 587),
                username=fn_args["smtp_user"],
                password=fn_args["smtp_password"],
                use_tls=fn_args.get("use_tls", True),
                use_ssl=fn_args.get("use_ssl", False),
            )
            
            result = await send_email(
                smtp_config=smtp_config,
                to=fn_args["to"],
                subject=fn_args["subject"],
                body=fn_args.get("body"),
                html_body=fn_args.get("html_body"),
                cc=fn_args.get("cc"),
                bcc=fn_args.get("bcc"),
                reply_to=fn_args.get("reply_to"),
                from_name=fn_args.get("from_name"),
                attachments=fn_args.get("attachments"),
                headers=fn_args.get("headers"),
                priority=fn_args.get("priority", "normal"),
            )
            
            return format_email_result(result)

        if fn_name == "email_send_template":
            from tools.email_sender import send_template_email, format_email_result, SMTPConfig
            
            # Build SMTP config from args
            smtp_config = SMTPConfig(
                host=fn_args["smtp_host"],
                port=fn_args.get("smtp_port", 587),
                username=fn_args["smtp_user"],
                password=fn_args["smtp_password"],
                use_tls=fn_args.get("use_tls", True),
                use_ssl=fn_args.get("use_ssl", False),
            )
            
            result = await send_template_email(
                smtp_config=smtp_config,
                template_name=fn_args["template_name"],
                to=fn_args["to"],
                variables=fn_args["variables"],
                cc=fn_args.get("cc"),
                bcc=fn_args.get("bcc"),
                reply_to=fn_args.get("reply_to"),
                from_name=fn_args.get("from_name"),
                attachments=fn_args.get("attachments"),
                priority=fn_args.get("priority", "normal"),
            )
            
            return format_email_result(result)

        if fn_name == "email_list_templates":
            from tools.email_sender import list_templates, format_template_list
            
            templates = list_templates()
            return format_template_list(templates)

        if fn_name == "email_test_smtp":
            from tools.email_sender import test_smtp_connection, SMTPConfig
            
            # Build SMTP config from args
            smtp_config = SMTPConfig(
                host=fn_args["smtp_host"],
                port=fn_args.get("smtp_port", 587),
                username=fn_args["smtp_user"],
                password=fn_args["smtp_password"],
                use_tls=fn_args.get("use_tls", True),
                use_ssl=fn_args.get("use_ssl", False),
            )
            
            result = await test_smtp_connection(smtp_config)
            
            if result.get("success"):
                return (
                    f"<smtp_test>\n"
                    f"  <status>success</status>\n"
                    f"  <message>{result.get('message', 'Connection successful')}</message>\n"
                    f"  <server_info>{result.get('server_info', 'N/A')}</server_info>\n"
                    f"</smtp_test>"
                )
            else:
                return (
                    f"<smtp_test>\n"
                    f"  <status>failed</status>\n"
                    f"  <message>{result.get('message', 'Connection failed')}</message>\n"
                    f"  <error>{result.get('error', 'Unknown error')}</error>\n"
                    f"</smtp_test>"
                )

        # ── Self-Managing Workspace Tools (pi-mom inspired) ────────────
        if fn_name == "workspace_create_skill":
            from tools.self_managing_workspace import get_workspace_manager
            ws = get_workspace_manager().get_agent_workspace(self.role.value)
            result = ws.create_skill(
                skill_name=fn_args["skill_name"],
                description=fn_args["description"],
                usage_instructions=fn_args.get("usage_instructions", ""),
                scripts=fn_args.get("scripts", {}),
            )
            return (
                f"[Workspace] Skill '{result['skill_name']}' created at {result['path']}\n"
                f"Scripts: {', '.join(result['scripts'])}\n"
                f"Run with: workspace_run_script(skill_name='{result['skill_name']}', script_name='...')"
            )

        if fn_name == "workspace_run_script":
            from tools.self_managing_workspace import get_workspace_manager
            ws = get_workspace_manager().get_agent_workspace(self.role.value)
            result = ws.execute_skill_script(
                skill_name=fn_args["skill_name"],
                script_name=fn_args["script_name"],
                args=fn_args.get("args"),
                stdin_data=fn_args.get("stdin_data"),
            )
            status = "✅" if result["success"] else "❌"
            parts = [f"{status} Script execution ({result['execution_time_ms']:.0f}ms)"]
            if result["stdout"]:
                parts.append(f"STDOUT:\n{result['stdout']}")
            if result["stderr"]:
                parts.append(f"STDERR:\n{result['stderr']}")
            return "\n".join(parts)

        if fn_name == "workspace_list_skills":
            from tools.self_managing_workspace import get_workspace_manager
            ws = get_workspace_manager().get_agent_workspace(self.role.value)
            skills = ws.list_skills()
            if not skills:
                return "[Workspace] No skills created yet. Use workspace_create_skill to create one."
            lines = [f"[Workspace] {len(skills)} skills:"]
            for s in skills:
                lines.append(f"- {s['name']}: {s['description']} (scripts: {', '.join(s['scripts'])})")
            return "\n".join(lines)

        if fn_name == "workspace_scratch_write":
            from tools.self_managing_workspace import get_workspace_manager
            ws = get_workspace_manager().get_agent_workspace(self.role.value)
            path = ws.write_scratch(fn_args["filename"], fn_args["content"])
            return f"[Workspace] Written to scratch: {path}"

        if fn_name == "workspace_scratch_read":
            from tools.self_managing_workspace import get_workspace_manager
            ws = get_workspace_manager().get_agent_workspace(self.role.value)
            content = ws.read_scratch(fn_args["filename"])
            if content is None:
                return f"[Workspace] File not found: {fn_args['filename']}"
            return f"[Workspace] {fn_args['filename']}:\n{content}"

        # ── Agent Event Tools (pi-mom inspired) ──────────────────────
        if fn_name == "agent_event_create":
            from tools.agent_events import create_event, AgentEventType
            from datetime import datetime, timezone
            evt_type = AgentEventType(fn_args["event_type"])
            trigger_at = None
            if fn_args.get("trigger_at"):
                trigger_at = datetime.fromisoformat(fn_args["trigger_at"])
            event = create_event(
                event_type=evt_type,
                target_agent=fn_args["target_agent"],
                message=fn_args["message"],
                schedule=fn_args.get("schedule"),
                trigger_at=trigger_at,
                created_by=self.role.value,
            )
            return f"[Event] Created {event.event_type.value} event '{event.id}' for {event.target_agent}"

        if fn_name == "agent_event_list":
            from tools.agent_events import list_events
            events = list_events(target_agent=fn_args.get("target_agent"))
            if not events:
                return "[Events] No active events."
            lines = [f"[Events] {len(events)} active:"]
            for e in events:
                lines.append(f"- [{e['id']}] {e['event_type']} → {e['target_agent']}: {e['message'][:80]}")
            return "\n".join(lines)

        if fn_name == "agent_event_delete":
            from tools.agent_events import delete_event
            ok = delete_event(fn_args["event_id"])
            return f"[Event] {'Deleted' if ok else 'Not found'}: {fn_args['event_id']}"

        # ── Context History Search (pi-mom's grep on log.jsonl) ──────
        if fn_name == "search_thread_history":
            from tools.context_compaction import search_thread_history
            events = [e.model_dump() for e in thread.events] if thread.events else []
            results = search_thread_history(
                events=events,
                query=fn_args["query"],
                max_results=fn_args.get("max_results", 10),
            )
            if not results:
                return f"[History] No matches for '{fn_args['query']}'"
            lines = [f"[History] {len(results)} matches for '{fn_args['query']}':"]
            for r in results:
                lines.append(
                    f"- [{r['event_type']}|{r.get('agent_role', '?')}] {r['content'][:200]}"
                )
            return "\n".join(lines)

        # Delegate to subclass
        return await self._handle_custom_tool(fn_name, fn_args, thread)

    async def _handle_custom_tool(self, fn_name: str, fn_args: dict, thread: Thread) -> str:
        """Override in subclasses for agent-specific tools."""
        return f"Tool '{fn_name}' not implemented."
