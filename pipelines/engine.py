"""
Pipeline Engine — 12-Factor #8: Own your control flow.
Executes sub-tasks via sequential, parallel, consensus, or iterative pipelines.
Supports skill injection into agent context.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

# Max seconds for one sub-agent run; prevents one stuck agent from blocking the pipeline
SUBTASK_TIMEOUT = 30
# Max seconds for entire parallel/consensus gather
PIPELINE_GATHER_TIMEOUT = 60
ITERATIVE_SCORE_THRESHOLD = 0.8
ITERATIVE_MIN_IMPROVEMENT_DELTA = 0.05
ITERATIVE_DEFAULT_MAX_ROUNDS = 3
ITERATIVE_FAST_MAX_ROUNDS = 1
ITERATIVE_FAST_SCORE_THRESHOLD = 0.65

from agents.base import BaseAgent
from agents.thinker import ThinkerAgent
from agents.speed import SpeedAgent
from agents.researcher import ResearcherAgent
from agents.reasoner import ReasonerAgent
from config import get_iterative_eval_runtime_config
from core.models import (
    AgentRole, EventType, PipelineType, SubTask, Task, TaskStatus, Thread,
)

logger = logging.getLogger(__name__)


def _status_meta(status: TaskStatus | str) -> dict[str, Any]:
    canonical = TaskStatus.normalize(status)
    return {
        "run_state": canonical,
        "run_state_alias": TaskStatus.legacy_alias(status),
    }


def _transition_meta(previous: TaskStatus | str, current: TaskStatus | str) -> dict[str, Any]:
    prev_canonical = TaskStatus.normalize(previous)
    curr_canonical = TaskStatus.normalize(current)
    return {
        **_status_meta(current),
        "run_state_prev": prev_canonical,
        "run_state_prev_alias": TaskStatus.legacy_alias(previous),
        "run_state_transition": f"{prev_canonical}->{curr_canonical}",
    }


def _set_task_state(
    thread: Thread,
    task: Task,
    next_status: TaskStatus | str,
    event_type: EventType,
    content: str,
    *,
    live_monitor: Any | None = None,
    agent_role: AgentRole | None = None,
    strict: bool = False,
    **meta: Any,
) -> None:
    prev_status = task.status
    prev_canonical = TaskStatus.normalize(prev_status)
    next_canonical = TaskStatus.normalize(next_status)
    transition_allowed = TaskStatus.can_transition(prev_canonical, next_canonical)
    if not transition_allowed:
        logger.warning(
            "run.state.invalid_transition",
            extra={
                "event": "run.state.invalid_transition",
                "thread_id": thread.id,
                "task_id": task.id,
                "from_state": prev_canonical,
                "to_state": next_canonical,
                "legacy_from": TaskStatus.legacy_alias(prev_status),
                "legacy_to": TaskStatus.legacy_alias(next_status),
            },
        )
        if strict and prev_canonical != next_canonical:
            raise ValueError(
                f"Invalid run state transition {prev_canonical}->{next_canonical} for task {task.id}"
            )
    task.status = TaskStatus.canonical(next_status)
    thread.add_event(
        event_type,
        content,
        agent_role=agent_role,
        **_transition_meta(prev_status, task.status),
        **meta,
    )
    logger.info(
        "run.state.transition",
        extra={
            "event": "run.state.transition",
            "thread_id": thread.id,
            "task_id": task.id,
            "from_state": prev_canonical,
            "to_state": TaskStatus.normalize(task.status),
            "legacy_from": TaskStatus.legacy_alias(prev_status),
            "legacy_to": TaskStatus.legacy_alias(task.status),
            "transition": f"{prev_canonical}->{TaskStatus.normalize(task.status)}",
        },
    )
    if live_monitor:
        try:
            live_monitor.emit(
                "run_state",
                "orchestrator",
                content,
                run_state=TaskStatus.normalize(task.status),
                run_state_alias=TaskStatus.legacy_alias(task.status),
                run_state_prev=prev_canonical,
                run_state_prev_alias=TaskStatus.legacy_alias(prev_status),
                run_state_transition=f"{prev_canonical}->{TaskStatus.normalize(task.status)}",
                thread_id=thread.id,
                task_id=task.id,
            )
        except Exception:
            pass

from tools.skill_finder import get_skill_knowledge
from tools.circuit_breaker import get_circuit_breaker
from tools.cache import get_cached_response, cache_response
from tools.confidence import score_confidence


class PipelineEngine:
    """Executes task pipelines with specialist agents."""

    def __init__(self) -> None:
        self._agents: dict[AgentRole, BaseAgent] = {
            AgentRole.THINKER: ThinkerAgent(),
            AgentRole.SPEED: SpeedAgent(),
            AgentRole.RESEARCHER: ResearcherAgent(),
            AgentRole.REASONER: ReasonerAgent(),
        }
        self._live_monitor = None

        # Agent Communication Protocol (Faz 15) — bus entegrasyonu
        self._bus_initialized = False

    def set_live_monitor(self, monitor):
        """Attach live monitor and propagate to all agents."""
        self._live_monitor = monitor
        for agent in self._agents.values():
            agent.set_live_monitor(monitor)

    def _init_bus_subscriptions(self) -> None:
        """Agent'ları event bus'a kaydet — task delegation ve handoff için."""
        try:
            from core.event_bus import get_event_bus
            from core.handoff import get_handoff_manager
            from core.task_delegation import get_task_delegation_manager

            bus = get_event_bus()
            handoff_mgr = get_handoff_manager()
            task_mgr = get_task_delegation_manager()

            for role, agent in self._agents.items():
                # Subscribe each agent to its own unicast channel
                bus.subscribe(
                    agent_role=role.value,
                    channel=f"agent:{role.value}",
                    handler=self._make_agent_message_handler(agent),
                )

                # Register handoff handler
                handoff_mgr.register_handler(
                    agent_role=role.value,
                    handler=self._make_handoff_handler(agent),
                )

                # Register task delegation executor
                task_mgr.register_executor(
                    agent_role=role.value,
                    executor=self._make_task_executor(agent),
                )

            self._bus_initialized = True
        except Exception as e:
            import logging
            logging.getLogger("pipeline_engine").warning(f"Bus init failed (non-fatal): {e}")

    def _make_agent_message_handler(self, agent: BaseAgent):
        """Agent için generic bus message handler oluştur."""
        async def handler(msg):
            from core.protocols import MessageType as MT
            if msg.message_type == MT.QUERY:
                query = msg.payload.get("query", "")
                if query:
                    temp_thread = Thread()
                    result = await agent.execute(query, temp_thread)
                    await agent.send_to_agent(
                        target=msg.source_agent,
                        msg_type=MT.QUERY_RESPONSE,
                        payload={"response": result, "query": query},
                        correlation_id=msg.correlation_id,
                    )
        return handler

    def _make_handoff_handler(self, agent: BaseAgent):
        """Agent için handoff kabul handler'ı oluştur."""
        async def handler(ctx):
            temp_thread = Thread()
            prompt = (
                f"HANDOFF from {ctx.from_agent}: {ctx.reason}\n\n"
                f"Original task: {ctx.task_description}\n"
                f"Work completed: {ctx.work_completed}\n"
                f"Work remaining: {ctx.work_remaining}\n"
            )
            if ctx.partial_result:
                prompt += f"\nPartial result so far:\n{ctx.partial_result}\n"
            prompt += "\nContinue from where the previous agent left off."
            return await agent.execute(prompt, temp_thread)
        return handler

    def _make_task_executor(self, agent: BaseAgent):
        """Agent için delegated task executor oluştur."""
        async def executor(task):
            temp_thread = Thread()
            prompt = task.description
            if task.input_data:
                prompt += f"\n\nInput data: {task.input_data}"
            return await agent.execute(prompt, temp_thread)
        return executor

    def get_agent(self, role: AgentRole) -> BaseAgent:
        return self._agents[role]

    async def execute(self, task: Task, thread: Thread) -> str:
        """Route to appropriate pipeline strategy."""
        _set_task_state(
            thread,
            task,
            TaskStatus.QUEUED,
            EventType.ROUTING_DECISION,
            "Run queued for pipeline dispatch",
            agent_role=AgentRole.ORCHESTRATOR,
            live_monitor=self._live_monitor,
            strict=True,
        )

        # Initialize bus subscriptions once
        if not self._bus_initialized:
            self._init_bus_subscriptions()

        # Publish pipeline start event to bus
        try:
            from core.event_bus import get_event_bus
            from core.protocols import MessageType as MT
            bus = get_event_bus()
            await bus.broadcast(
                source="pipeline_engine",
                msg_type=MT.BROADCAST,
                payload={
                    "event": "pipeline_start",
                    "pipeline_type": task.pipeline_type.value,
                    "sub_task_count": len(task.sub_tasks),
                    "agents": [st.assigned_agent.value for st in task.sub_tasks],
                },
            )
        except Exception:
            pass  # Bus errors never break pipeline

        _set_task_state(
            thread,
            task,
            TaskStatus.ROUTING,
            EventType.ROUTING_DECISION,
            f"Routing pipeline={task.pipeline_type.value} with {len(task.sub_tasks)} sub-tasks",
            agent_role=AgentRole.ORCHESTRATOR,
            live_monitor=self._live_monitor,
        )

        # Check cache for identical queries
        try:
            cached = await get_cached_response(task.user_input, task.pipeline_type.value)
            if cached:
                _set_task_state(
                    thread,
                    task,
                    TaskStatus.RUNNING,
                    EventType.PIPELINE_START,
                    "Cache hit path entered",
                    live_monitor=self._live_monitor,
                )
                _set_task_state(
                    thread,
                    task,
                    TaskStatus.SYNTHESIZING,
                    EventType.PIPELINE_STEP,
                    f"Cache hit (confidence: {cached.get('confidence', 0):.0%}) — synthesizing cached response",
                    live_monitor=self._live_monitor,
                )
                _set_task_state(
                    thread,
                    task,
                    TaskStatus.COMPLETED,
                    EventType.PIPELINE_COMPLETE,
                    "Cache response delivered",
                    live_monitor=self._live_monitor,
                )
                task.final_result = cached["response"]
                return cached["response"]
        except Exception:
            pass  # Cache miss or error — proceed normally

        _set_task_state(
            thread,
            task,
            TaskStatus.RUNNING,
            EventType.PIPELINE_START,
            f"Starting {task.pipeline_type.value} pipeline with {len(task.sub_tasks)} sub-tasks",
            live_monitor=self._live_monitor,
        )

        t0 = time.monotonic()
        # Respect explicit pipeline type choice - don't force parallel
        effective_type = task.pipeline_type

        try:
            match effective_type:
                case PipelineType.SEQUENTIAL:
                    result = await self._sequential(task, thread)
                case PipelineType.PARALLEL:
                    result = await self._parallel(task, thread)
                case PipelineType.CONSENSUS:
                    result = await self._consensus(task, thread)
                case PipelineType.ITERATIVE:
                    result = await self._iterative(task, thread)
                case PipelineType.DEEP_RESEARCH:
                    result = await self._deep_research(task, thread)
                case PipelineType.IDEA_TO_PROJECT:
                    result = await self._idea_to_project(task, thread)
                case PipelineType.BRAINSTORM:
                    result = await self._brainstorm(task, thread)
                case _:
                    result = await self._parallel(task, thread) if len(task.sub_tasks) >= 2 else await self._sequential(task, thread)

            task.total_latency_ms = (time.monotonic() - t0) * 1000
            if isinstance(result, str) and result.strip().startswith("[Stopped]"):
                _set_task_state(
                    thread,
                    task,
                    TaskStatus.STOPPED,
                    EventType.PIPELINE_STEP,
                    "Pipeline execution stopped by user",
                    live_monitor=self._live_monitor,
                )
            else:
                _set_task_state(
                    thread,
                    task,
                    TaskStatus.SYNTHESIZING,
                    EventType.PIPELINE_STEP,
                    "Pipeline execution finished, synthesizing outputs",
                    live_monitor=self._live_monitor,
                )
                _set_task_state(
                    thread,
                    task,
                    TaskStatus.COMPLETED,
                    EventType.PIPELINE_COMPLETE,
                    "Pipeline synthesis completed",
                    live_monitor=self._live_monitor,
                )
        except Exception as e:
            result = f"[Pipeline Error] {e}"
            _set_task_state(
                thread,
                task,
                TaskStatus.FAILED,
                EventType.ERROR,
                result,
                live_monitor=self._live_monitor,
            )

        # Cache successful results
        if task.status == TaskStatus.COMPLETED:
            try:
                await cache_response(
                    task.user_input, result, task.pipeline_type.value,
                    confidence=0.0,  # Will be set by synthesizer
                )
            except Exception:
                pass

        thread.add_event(
            EventType.PIPELINE_COMPLETE,
            f"Pipeline {task.pipeline_type.value} completed: {task.status.value}",
            latency_ms=task.total_latency_ms,
            **_status_meta(task.status),
        )

        # Publish pipeline complete event to bus
        try:
            from core.event_bus import get_event_bus
            from core.protocols import MessageType as MT
            bus = get_event_bus()
            await bus.broadcast(
                source="pipeline_engine",
                msg_type=MT.BROADCAST,
                payload={
                    "event": "pipeline_complete",
                    "pipeline_type": task.pipeline_type.value,
                    "status": task.status.value,
                    "latency_ms": task.total_latency_ms,
                    "sub_task_count": len(task.sub_tasks),
                },
            )
        except Exception:
            pass

        return result

    async def _run_subtask(self, subtask: SubTask, context: str, thread: Thread) -> str:
        """Execute a single sub-task with its assigned agent, injecting skills if assigned."""
        # Check stop
        if self._live_monitor and self._live_monitor.should_stop():
            subtask.status = TaskStatus.STOPPED
            return "[Stopped]"

        subtask.status = TaskStatus.RUNNING
        agent = self.get_agent(subtask.assigned_agent)

        # Circuit breaker check
        cb = get_circuit_breaker()
        agent_role_str = subtask.assigned_agent.value
        if not cb.is_available(agent_role_str):
            fallback_role = cb.get_fallback_agent(agent_role_str)
            if fallback_role:
                thread.add_event(
                    EventType.PIPELINE_STEP,
                    f"⚡ Circuit breaker: {agent_role_str} unavailable, falling back to {fallback_role}",
                    agent_role=subtask.assigned_agent,
                )
                subtask.assigned_agent = AgentRole(fallback_role)
                agent = self.get_agent(subtask.assigned_agent)
            else:
                subtask.status = TaskStatus.FAILED
                subtask.result = f"[CircuitBreaker] Agent {agent_role_str} is unavailable and no fallback found."
                return subtask.result

        # Inject skill knowledge into context if skills were assigned
        skill_context = ""
        if subtask.skills:
            skill_parts = []
            for skill_id in subtask.skills:
                knowledge = get_skill_knowledge(skill_id)
                if knowledge:
                    skill_parts.append(f"<skill id=\"{skill_id}\">\n{knowledge}\n</skill>")
            if skill_parts:
                skill_context = (
                    "\n\n--- INJECTED SKILLS ---\n"
                    "Follow these specialized protocols for this task:\n\n"
                    + "\n\n".join(skill_parts)
                    + "\n--- END SKILLS ---\n\n"
                )

        thread.add_event(
            EventType.PIPELINE_STEP,
            f"[{subtask.assigned_agent.value}] {subtask.description[:100]}"
            + (f" (skills: {', '.join(subtask.skills)})" if subtask.skills else ""),
            agent_role=subtask.assigned_agent,
        )

        enriched_context = skill_context + context

        t0 = time.monotonic()
        try:
            result = await asyncio.wait_for(
                agent.execute(enriched_context, thread),
                timeout=SUBTASK_TIMEOUT,
            )
            cb.record_success(agent_role_str)
        except asyncio.TimeoutError:
            result = "[Timeout] Agent did not respond in time. Try a simpler query or try again."
            subtask.status = TaskStatus.FAILED
            subtask.latency_ms = (time.monotonic() - t0) * 1000
            subtask.result = result
            cb.record_failure(agent_role_str, "timeout")
            return result
        except Exception as e:
            result = f"[Error] Agent {agent_role_str} failed: {type(e).__name__}: {e}"
            subtask.status = TaskStatus.FAILED
            subtask.latency_ms = (time.monotonic() - t0) * 1000
            subtask.result = result
            cb.record_failure(agent_role_str, str(e))
            return result
        subtask.latency_ms = (time.monotonic() - t0) * 1000
        subtask.status = TaskStatus.COMPLETED
        subtask.result = result

        # Auto-evaluate agent output quality
        eval_score = 3.0  # default neutral score
        task_type = "general"
        try:
            from tools.agent_eval import score_agent_output, detect_task_type
            task_type = detect_task_type(subtask.description)
            eval_result = score_agent_output(
                agent_role=subtask.assigned_agent.value,
                task_type=task_type,
                output=result,
                tokens_used=subtask.token_usage or 0,
                latency_ms=subtask.latency_ms,
                task_preview=subtask.description[:200],
            )
            if isinstance(eval_result, (int, float)):
                eval_score = float(eval_result)
            elif isinstance(eval_result, dict) and "score" in eval_result:
                eval_score = float(eval_result["score"])
        except Exception:
            pass  # Never break pipeline for evaluation

        # Faz 16: Record performance metric for self-improvement loop
        try:
            from tools.performance_collector import get_performance_collector

            get_performance_collector().record(
                agent_role=subtask.assigned_agent.value,
                response_time_ms=subtask.latency_ms,
                total_tokens=subtask.token_usage or 0,
                success=True,
                metadata={
                    "task_type": task_type,
                    "score": eval_score,
                    "skill_ids_used": subtask.skills or [],
                },
            )
        except Exception:
            pass  # Never break pipeline for metrics collection

        return result

    # ── Sequential Pipeline ──────────────────────────────────────

    async def _sequential(self, task: Task, thread: Thread) -> str:
        """A → B → C: Each agent receives previous agent's output."""
        context = task.user_input
        results = []

        for subtask in sorted(task.sub_tasks, key=lambda s: s.priority):
            enriched = f"Original request: {task.user_input}\n\nPrevious context:\n{context}\n\nYour task: {subtask.description}"
            result = await self._run_subtask(subtask, enriched, thread)
            context = result
            results.append(f"[{subtask.assigned_agent.value}] {result}")

        return "\n\n---\n\n".join(results)

    # ── Parallel Pipeline ────────────────────────────────────────

    async def _parallel(self, task: Task, thread: Thread) -> str:
        """[A, B, C] → all run simultaneously → merge results."""
        coros = []
        for subtask in task.sub_tasks:
            enriched = f"Original request: {task.user_input}\n\nYour task: {subtask.description}"
            coros.append(self._run_subtask(subtask, enriched, thread))

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*coros, return_exceptions=True),
                timeout=PIPELINE_GATHER_TIMEOUT,
            )
        except asyncio.TimeoutError:
            timeout_msg = "[Timeout] Pipeline did not complete in time. Some agents may still be running."
            results = [timeout_msg] * len(task.sub_tasks)
            for st in task.sub_tasks:
                st.status = TaskStatus.FAILED
                if not st.result:
                    st.result = timeout_msg

        parts = []
        for subtask, result in zip(task.sub_tasks, results):
            if isinstance(result, Exception):
                parts.append(f"[{subtask.assigned_agent.value}] Error: {result}")
                subtask.status = TaskStatus.FAILED
            else:
                parts.append(f"[{subtask.assigned_agent.value}] {result}")

        # Score confidence for each successful result
        for subtask, result in zip(task.sub_tasks, results):
            if not isinstance(result, Exception) and not str(result).startswith("["):
                try:
                    from tools.agent_eval import detect_task_type
                    task_type = detect_task_type(task.user_input)
                    conf = score_confidence(str(result), subtask.assigned_agent.value, task_type)
                    subtask.metadata["confidence"] = conf
                except Exception:
                    pass

        return "\n\n---\n\n".join(parts)

    # ── Consensus Pipeline ───────────────────────────────────────

    async def _consensus(self, task: Task, thread: Thread) -> str:
        """All agents answer the same question → compare results."""
        question = task.user_input
        agents_to_use = [AgentRole.THINKER, AgentRole.SPEED, AgentRole.RESEARCHER, AgentRole.REASONER]

        coros = []
        for role in agents_to_use:
            agent = self.get_agent(role)
            coros.append(agent.execute(question, thread))

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*coros, return_exceptions=True),
                timeout=PIPELINE_GATHER_TIMEOUT,
            )
        except asyncio.TimeoutError:
            results = ["[Timeout] Consensus round did not complete in time."] * len(agents_to_use)

        parts = ["CONSENSUS RESULTS — Multiple agents answered the same question:\n"]
        for role, result in zip(agents_to_use, results):
            if isinstance(result, Exception):
                parts.append(f"[{role.value}] Error: {result}")
            else:
                parts.append(f"[{role.value}] {result}")

        return "\n\n---\n\n".join(parts)

    # ── Iterative Pipeline ───────────────────────────────────────

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any] | None:
        """Best-effort JSON extraction from model text output."""
        if not text:
            return None

        raw = text.strip()
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            pass

        # Fallback: take first JSON object block.
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            obj = json.loads(raw[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    @staticmethod
    def _should_use_fast_iterative_mode(user_input: str, task: Task) -> bool:
        """Use a low-latency iterative strategy for simple requests."""
        text = (user_input or "").lower()
        complexity_markers = (
            "detailed",
            "comprehensive",
            "deep",
            "architecture",
            "step-by-step",
            "report",
            "analysis",
        )
        has_complexity_signal = any(marker in text for marker in complexity_markers)
        # Keep simple requests fast by default.
        return (
            len(text) <= 280 and len(task.sub_tasks) <= 2 and not has_complexity_signal
        )

    async def _evaluate_draft_with_reviewer(
        self,
        reviewer: BaseAgent,
        user_input: str,
        draft: str,
        round_num: int,
        fast_mode: bool,
        thread: Thread,
    ) -> tuple[dict[str, Any] | None, str]:
        """Run structured reviewer evaluation and return (parsed_json, raw_text)."""
        if fast_mode:
            review_prompt = (
                f"Original request: {user_input}\n"
                f"Draft (round {round_num}): {draft}\n\n"
                "Return ONLY JSON: "
                '{"approved":boolean,"overall_score":number,"weaknesses":[string],"improvements":[string]}\n'
                "Rules: overall_score 0..1, keep weaknesses/improvements very short (max 2 each)."
            )
        else:
            review_prompt = (
                f"Original request: {user_input}\n\n"
                f"Draft (round {round_num}):\n{draft}\n\n"
                "Evaluate this draft and respond ONLY as JSON with this schema:\n"
                "{\n"
                '  "approved": boolean,\n'
                '  "overall_score": number,\n'
                '  "dimensions": {\n'
                '    "accuracy": number,\n'
                '    "clarity": number,\n'
                '    "completeness": number,\n'
                '    "actionability": number\n'
                "  },\n"
                '  "weaknesses": [string],\n'
                '  "improvements": [string]\n'
                "}\n"
                "Scoring rules:\n"
                "- overall_score must be 0.0 to 1.0\n"
                "- approved=true only if overall_score >= 0.8 and no critical weaknesses\n"
                "- weaknesses/improvements must be concise and actionable\n"
            )

        raw_review = await reviewer.execute(review_prompt, thread)
        parsed = self._extract_json_object(raw_review)
        return parsed, raw_review

    async def _iterative(
        self, task: Task, thread: Thread, max_rounds: int | None = None
    ) -> str:
        """Evaluator-optimizer loop with structured scoring and convergence checks."""
        if len(task.sub_tasks) < 2:
            return await self._sequential(task, thread)

        producer_task = task.sub_tasks[0]
        reviewer_task = task.sub_tasks[1]

        producer = self.get_agent(producer_task.assigned_agent)
        reviewer = self.get_agent(reviewer_task.assigned_agent)
        iterative_cfg = get_iterative_eval_runtime_config()
        configured_mode = str(iterative_cfg.get("mode", "auto"))
        if configured_mode == "fast":
            fast_mode = True
        elif configured_mode == "full":
            fast_mode = False
        else:
            fast_mode = self._should_use_fast_iterative_mode(task.user_input, task)

        effective_max_rounds = (
            max_rounds
            if max_rounds is not None
            else (
                int(iterative_cfg.get("fast_max_rounds", ITERATIVE_FAST_MAX_ROUNDS))
                if fast_mode
                else int(
                    iterative_cfg.get(
                        "default_max_rounds", ITERATIVE_DEFAULT_MAX_ROUNDS
                    )
                )
            )
        )
        effective_max_rounds = max(1, effective_max_rounds)

        score_threshold = (
            float(
                iterative_cfg.get(
                    "fast_score_threshold", ITERATIVE_FAST_SCORE_THRESHOLD
                )
            )
            if fast_mode
            else float(
                iterative_cfg.get("full_score_threshold", ITERATIVE_SCORE_THRESHOLD)
            )
        )
        score_threshold = max(0.0, min(1.0, score_threshold))
        min_improvement_delta = float(
            iterative_cfg.get("min_improvement_delta", ITERATIVE_MIN_IMPROVEMENT_DELTA)
        )
        min_improvement_delta = max(0.0, min_improvement_delta)

        # Initial draft
        draft = await producer.execute(
            f"Original request: {task.user_input}\n\nYour task: {producer_task.description}",
            thread,
        )

        best_draft = draft
        best_score = 0.0
        stagnation_rounds = 0
        review_summary: dict[str, Any] | None = None

        for round_num in range(1, effective_max_rounds + 1):
            review_json, review_raw = await self._evaluate_draft_with_reviewer(
                reviewer=reviewer,
                user_input=task.user_input,
                draft=draft,
                round_num=round_num,
                fast_mode=fast_mode,
                thread=thread,
            )

            # Graceful parse fallback: keep previous behavior semantics.
            if not review_json:
                approved = "APPROVED" in review_raw.upper()
                review_json = {
                    "approved": approved,
                    "overall_score": 1.0 if approved else 0.5,
                    "weaknesses": []
                    if approved
                    else ["Unstructured reviewer feedback"],
                    "improvements": [] if approved else [review_raw[:400]],
                }

            review_summary = review_json
            score = float(review_json.get("overall_score", 0.0) or 0.0)
            approved = bool(review_json.get("approved", False))

            thread.add_event(
                EventType.EVALUATION,
                (
                    f"Iterative round {round_num} ({'fast' if fast_mode else 'full'}"
                    f", cfg={configured_mode}): score={score:.2f}, approved={approved}"
                ),
                agent_role=reviewer_task.assigned_agent,
            )

            if score > best_score:
                if score - best_score < min_improvement_delta:
                    stagnation_rounds += 1
                else:
                    stagnation_rounds = 0
                best_score = score
                best_draft = draft
            else:
                stagnation_rounds += 1

            if approved or score >= score_threshold:
                best_draft = draft
                break

            if stagnation_rounds >= 2:
                thread.add_event(
                    EventType.EVALUATION,
                    "Iterative loop stopped due to convergence/stagnation",
                    agent_role=reviewer_task.assigned_agent,
                )
                break

            weaknesses = review_json.get("weaknesses") or []
            improvements = review_json.get("improvements") or []
            weaknesses_text = (
                "\n".join(f"- {w}" for w in weaknesses)
                if weaknesses
                else "- No explicit weaknesses provided"
            )
            improvements_text = (
                "\n".join(f"- {i}" for i in improvements)
                if improvements
                else "- Improve clarity, completeness, and actionable details"
            )

            refine_prompt = (
                f"Original request: {task.user_input}\n\n"
                f"Current draft:\n{draft}\n\n"
                f"Reviewer weaknesses:\n{weaknesses_text}\n\n"
                f"Reviewer improvements:\n{improvements_text}\n\n"
                "Revise the draft to address all weaknesses. "
                "Keep correct parts unchanged, improve only weak parts, and preserve factual accuracy."
            )
            draft = await producer.execute(refine_prompt, thread)

        producer_task.result = best_draft
        reviewer_task.result = json.dumps(review_summary or {}, ensure_ascii=False)
        return best_draft

    # ── Deep Research Pipeline ───────────────────────────────────

    async def _deep_research(self, task: Task, thread: Thread) -> str:
        """
        Deep Research: All agents work in parallel on the same query,
        each from their specialty angle. Results are merged for synthesis.
        """
        thread.add_event(
            EventType.PIPELINE_STEP,
            f"🔬 Deep Research: {len(task.sub_tasks)} agents launching in parallel",
        )

        # Phase 1: All agents run simultaneously
        coros = []
        for subtask in task.sub_tasks:
            enriched = (
                f"DEEP RESEARCH MODE — You are one of {len(task.sub_tasks)} specialist agents "
                f"working in parallel on this request.\n\n"
                f"Original request: {task.user_input}\n\n"
                f"Your specific task: {subtask.description}\n\n"
                f"Be thorough. Your output will be combined with other agents' work."
            )
            coros.append(self._run_subtask(subtask, enriched, thread))

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*coros, return_exceptions=True),
                timeout=PIPELINE_GATHER_TIMEOUT,
            )
        except asyncio.TimeoutError:
            results = [
                "[Timeout] Deep Research did not complete in time."
            ] * len(task.sub_tasks)
            for st in task.sub_tasks:
                st.status = TaskStatus.FAILED

        # Phase 2: Merge results with agent labels
        parts = []
        for subtask, result in zip(task.sub_tasks, results):
            agent_name = subtask.assigned_agent.value
            if isinstance(result, Exception):
                parts.append(f"[{agent_name}] Error: {result}")
                subtask.status = TaskStatus.FAILED
            else:
                parts.append(f"[{agent_name}] {result}")

        thread.add_event(
            EventType.PIPELINE_STEP,
            f"🔬 Deep Research complete: {sum(1 for r in results if not isinstance(r, Exception))}/{len(results)} agents succeeded",
        )

        return "\n\n---\n\n".join(parts)

    # ── Idea-to-Project Pipeline ─────────────────────────────────

    async def _idea_to_project(self, task: Task, thread: Thread) -> str:
        """
        Idea-to-Project: Sequential phases where each builds on previous.
        Analyze → PRD → Architecture → Tasks → Scaffold.
        """
        from tools.idea_to_project import PHASES, get_phase_prompt, save_project_output

        thread.add_event(
            EventType.PIPELINE_STEP,
            f"🚀 Idea-to-Project: {len(PHASES)} phases starting",
        )

        results = {}
        prev_result = ""

        for phase in PHASES:
            prompt = get_phase_prompt(phase["id"], task.user_input, prev_result)
            agent_role = AgentRole(phase["agent"])

            subtask = SubTask(
                description=f"[{phase['name']}] {phase['description']}",
                assigned_agent=agent_role,
                priority=1,
            )

            result = await self._run_subtask(subtask, prompt, thread)
            results[phase["id"]] = result
            prev_result = result

            project_name = task.user_input[:50].strip()
            save_project_output(project_name, phase["id"], result)

        parts = [f"🚀 IDEA-TO-PROJECT COMPLETE\n"]
        for phase in PHASES:
            if phase["id"] in results:
                parts.append(f"\n{'='*60}")
                parts.append(f"📋 {phase['name'].upper()}")
                parts.append(f"{'='*60}")
                parts.append(results[phase["id"]])

        return "\n".join(parts)

    # ── Brainstorm Pipeline ──────────────────────────────────────

    async def _brainstorm(self, task: Task, thread: Thread) -> str:
        """
        Multi-round debate: 4 agents argue from different angles,
        cross-challenge each other, then SPEED synthesizes.

        Round 1 (Parallel): Each agent gives initial perspective
        Round 2 (Parallel): Each agent responds to others' arguments
        Round 3 (Sequential): SPEED synthesizes the full debate
        """
        topic = task.user_input

        # Agent perspectives — each gets a unique angle
        perspectives: dict[AgentRole, str] = {
            AgentRole.THINKER: (
                "You are the STRATEGIC/ANALYTICAL voice in this brainstorm. "
                "Analyze the topic from a high-level strategic perspective. "
                "Consider long-term implications, trade-offs, and systemic effects. "
                "Think big picture."
            ),
            AgentRole.RESEARCHER: (
                "You are the DATA-DRIVEN/EVIDENCE-BASED voice in this brainstorm. "
                "Ground your perspective in facts, research, real-world examples, and data. "
                "Cite evidence where possible. Be the empirical anchor."
            ),
            AgentRole.REASONER: (
                "You are the LOGICAL/CRITICAL voice — the devil's advocate. "
                "Challenge assumptions, find logical flaws, identify risks and edge cases. "
                "Push back on weak arguments. Be constructively skeptical."
            ),
            AgentRole.SPEED: (
                "You are the PRACTICAL/IMPLEMENTATION voice in this brainstorm. "
                "Focus on feasibility, actionable steps, quick wins, and real-world constraints. "
                "How would this actually get done? Be pragmatic."
            ),
        }

        agents_order = list(perspectives.keys())
        all_parts = []

        # ── Round 1: Initial Perspectives (Parallel) ────────────

        thread.add_event(
            EventType.PIPELINE_STEP,
            "🧠 Brainstorm Round 1: Each agent shares their initial perspective",
        )
        if self._live_monitor:
            self._live_monitor.emit(
                "pipeline", "orchestrator",
                "🧠 Brainstorm Round 1/3 — Initial perspectives",
            )

        round1_coros = []
        for role in agents_order:
            agent = self.get_agent(role)
            prompt = (
                f"{perspectives[role]}\n\n"
                f"TOPIC: {topic}\n\n"
                f"Share your initial perspective. Be concise but substantive. "
                f"Take a clear position."
            )
            round1_coros.append(agent.execute(prompt, thread))

        round1_results = await asyncio.wait_for(
            asyncio.gather(*round1_coros, return_exceptions=True),
            timeout=PIPELINE_GATHER_TIMEOUT,
        )

        round1_texts: dict[AgentRole, str] = {}
        round1_section = ["## 🧠 ROUND 1 — Initial Perspectives\n"]

        for role, result in zip(agents_order, round1_results):
            if isinstance(result, Exception):
                text = f"[Error: {result}]"
            else:
                text = str(result)
            round1_texts[role] = text
            round1_section.append(f"### [{role.value.upper()}]\n{text}")

        all_parts.append("\n\n".join(round1_section))

        # ── Stop check between rounds ───────────────────────────

        if self._live_monitor and self._live_monitor.should_stop():
            thread.add_event(EventType.ERROR, "Brainstorm stopped by user after Round 1")
            return "\n\n---\n\n".join(all_parts) + "\n\n[Stopped after Round 1]"

        # ── Round 2: Cross-Challenge (Parallel) ─────────────────

        thread.add_event(
            EventType.PIPELINE_STEP,
            "⚔️ Brainstorm Round 2: Agents respond to each other's arguments",
        )
        if self._live_monitor:
            self._live_monitor.emit(
                "pipeline", "orchestrator",
                "⚔️ Brainstorm Round 2/3 — Cross-challenge & debate",
            )

        # Build the "other agents said" context for each agent
        round2_coros = []
        for role in agents_order:
            others_context = "\n\n".join(
                f"[{other_role.value.upper()}]: {other_text}"
                for other_role, other_text in round1_texts.items()
                if other_role != role
            )
            prompt = (
                f"{perspectives[role]}\n\n"
                f"TOPIC: {topic}\n\n"
                f"Here is what the other agents said in Round 1:\n\n"
                f"{others_context}\n\n"
                f"Now respond to their arguments:\n"
                f"- Challenge or support specific points from other agents\n"
                f"- Add new insights sparked by the discussion\n"
                f"- Strengthen or revise your own position\n"
                f"Be direct. Reference other agents by name."
            )
            agent = self.get_agent(role)
            round2_coros.append(agent.execute(prompt, thread))

        round2_results = await asyncio.wait_for(
            asyncio.gather(*round2_coros, return_exceptions=True),
            timeout=PIPELINE_GATHER_TIMEOUT,
        )

        round2_section = ["## ⚔️ ROUND 2 — Cross-Challenge & Debate\n"]

        for role, result in zip(agents_order, round2_results):
            if isinstance(result, Exception):
                text = f"[Error: {result}]"
            else:
                text = result
            round2_section.append(f"### [{role.value.upper()}]\n{text}")

        all_parts.append("\n\n".join(round2_section))

        # ── Stop check before synthesis ─────────────────────────

        if self._live_monitor and self._live_monitor.should_stop():
            thread.add_event(EventType.ERROR, "Brainstorm stopped by user after Round 2")
            return "\n\n---\n\n".join(all_parts) + "\n\n[Stopped after Round 2]"

        # ── Round 3: Synthesis (SPEED agent) ────────────────────

        thread.add_event(
            EventType.PIPELINE_STEP,
            "📋 Brainstorm Round 3: Synthesizing the debate",
        )
        if self._live_monitor:
            self._live_monitor.emit(
                "pipeline", "orchestrator",
                "📋 Brainstorm Round 3/3 — Final synthesis",
            )

        full_debate = "\n\n---\n\n".join(all_parts)
        synthesis_prompt = (
            f"You are the synthesizer of a multi-agent brainstorm debate.\n\n"
            f"ORIGINAL TOPIC: {topic}\n\n"
            f"FULL DEBATE:\n{full_debate}\n\n"
            f"Create a structured synthesis with these sections:\n"
            f"1. **Key Agreements** — Points where agents converged\n"
            f"2. **Key Disagreements** — Unresolved tensions and opposing views\n"
            f"3. **Strongest Arguments** — The most compelling points from the debate\n"
            f"4. **Final Recommendation** — Your balanced conclusion based on all perspectives\n\n"
            f"Be concise and actionable. Reference which agent made which point."
        )

        synthesizer = self.get_agent(AgentRole.SPEED)
        synthesis = await synthesizer.execute(synthesis_prompt, thread)

        all_parts.append(f"## 📋 SYNTHESIS\n\n{synthesis}")

        thread.add_event(
            EventType.PIPELINE_STEP,
            f"✅ Brainstorm complete: 3 rounds, {len(agents_order)} agents",
        )

        return "\n\n---\n\n".join(all_parts)

