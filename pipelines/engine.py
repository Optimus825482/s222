"""
Pipeline Engine — 12-Factor #8: Own your control flow.
Executes sub-tasks via sequential, parallel, consensus, or iterative pipelines.
Supports skill injection into agent context.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from agents.base import BaseAgent
from agents.thinker import ThinkerAgent
from agents.speed import SpeedAgent
from agents.researcher import ResearcherAgent
from agents.reasoner import ReasonerAgent
from core.models import (
    AgentRole, EventType, PipelineType, SubTask, Task, TaskStatus, Thread,
)
from tools.skill_finder import get_skill_knowledge


class PipelineEngine:
    """Executes task pipelines with specialist agents."""

    def __init__(self) -> None:
        self._agents: dict[AgentRole, BaseAgent] = {
            AgentRole.THINKER: ThinkerAgent(),
            AgentRole.SPEED: SpeedAgent(),
            AgentRole.RESEARCHER: ResearcherAgent(),
            AgentRole.REASONER: ReasonerAgent(),
        }

    def get_agent(self, role: AgentRole) -> BaseAgent:
        return self._agents[role]

    async def execute(self, task: Task, thread: Thread) -> str:
        """Route to appropriate pipeline strategy."""
        task.status = TaskStatus.RUNNING
        thread.add_event(
            EventType.PIPELINE_START,
            f"Starting {task.pipeline_type.value} pipeline with {len(task.sub_tasks)} sub-tasks",
        )

        t0 = time.monotonic()
        try:
            match task.pipeline_type:
                case PipelineType.SEQUENTIAL:
                    result = await self._sequential(task, thread)
                case PipelineType.PARALLEL:
                    result = await self._parallel(task, thread)
                case PipelineType.CONSENSUS:
                    result = await self._consensus(task, thread)
                case PipelineType.ITERATIVE:
                    result = await self._iterative(task, thread)
                case _:
                    result = await self._sequential(task, thread)

            task.status = TaskStatus.COMPLETED
            task.total_latency_ms = (time.monotonic() - t0) * 1000
        except Exception as e:
            task.status = TaskStatus.FAILED
            result = f"[Pipeline Error] {e}"
            thread.add_event(EventType.ERROR, result)

        thread.add_event(
            EventType.PIPELINE_COMPLETE,
            f"Pipeline {task.pipeline_type.value} completed: {task.status.value}",
            latency_ms=task.total_latency_ms,
        )
        return result

    async def _run_subtask(self, subtask: SubTask, context: str, thread: Thread) -> str:
        """Execute a single sub-task with its assigned agent, injecting skills if assigned."""
        subtask.status = TaskStatus.RUNNING
        agent = self.get_agent(subtask.assigned_agent)

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
        result = await agent.execute(enriched_context, thread)
        subtask.latency_ms = (time.monotonic() - t0) * 1000
        subtask.status = TaskStatus.COMPLETED
        subtask.result = result
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

        results = await asyncio.gather(*coros, return_exceptions=True)

        parts = []
        for subtask, result in zip(task.sub_tasks, results):
            if isinstance(result, Exception):
                parts.append(f"[{subtask.assigned_agent.value}] Error: {result}")
                subtask.status = TaskStatus.FAILED
            else:
                parts.append(f"[{subtask.assigned_agent.value}] {result}")

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

        results = await asyncio.gather(*coros, return_exceptions=True)

        parts = ["CONSENSUS RESULTS — Multiple agents answered the same question:\n"]
        for role, result in zip(agents_to_use, results):
            if isinstance(result, Exception):
                parts.append(f"[{role.value}] Error: {result}")
            else:
                parts.append(f"[{role.value}] {result}")

        return "\n\n---\n\n".join(parts)

    # ── Iterative Pipeline ───────────────────────────────────────

    async def _iterative(self, task: Task, thread: Thread, max_rounds: int = 3) -> str:
        """Producer creates → Reviewer critiques → refine until good."""
        if len(task.sub_tasks) < 2:
            return await self._sequential(task, thread)

        producer_task = task.sub_tasks[0]
        reviewer_task = task.sub_tasks[1]

        producer = self.get_agent(producer_task.assigned_agent)
        reviewer = self.get_agent(reviewer_task.assigned_agent)

        # Initial draft
        draft = await producer.execute(
            f"Original request: {task.user_input}\n\nYour task: {producer_task.description}",
            thread,
        )

        for round_num in range(max_rounds):
            # Review
            review_prompt = (
                f"Original request: {task.user_input}\n\n"
                f"Draft (round {round_num + 1}):\n{draft}\n\n"
                f"Review this draft. If it's good, say 'APPROVED'. "
                f"Otherwise, provide specific feedback for improvement."
            )
            review = await reviewer.execute(review_prompt, thread)

            if "APPROVED" in review.upper():
                break

            # Refine
            refine_prompt = (
                f"Original request: {task.user_input}\n\n"
                f"Your previous draft:\n{draft}\n\n"
                f"Reviewer feedback:\n{review}\n\n"
                f"Improve your draft based on this feedback."
            )
            draft = await producer.execute(refine_prompt, thread)

        producer_task.result = draft
        reviewer_task.result = review
        return draft
