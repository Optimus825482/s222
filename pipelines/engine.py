"""
Pipeline Engine — 12-Factor #8: Own your control flow.
Executes sub-tasks via sequential, parallel, consensus, or iterative pipelines.
Supports skill injection into agent context.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

# Max seconds for one sub-agent run; prevents one stuck agent from blocking the pipeline
SUBTASK_TIMEOUT = 120
# Max seconds for entire parallel/consensus gather
PIPELINE_GATHER_TIMEOUT = 300

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
        self._live_monitor = None

    def set_live_monitor(self, monitor):
        """Attach live monitor and propagate to all agents."""
        self._live_monitor = monitor
        for agent in self._agents.values():
            agent.set_live_monitor(monitor)

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
        # Multiparallel: 2+ sub-tasks always run simultaneously (never sequential)
        effective_type = task.pipeline_type
        if len(task.sub_tasks) >= 2 and effective_type == PipelineType.SEQUENTIAL:
            effective_type = PipelineType.PARALLEL

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
        # Check stop
        if self._live_monitor and self._live_monitor.should_stop():
            subtask.status = TaskStatus.FAILED
            return "[Stopped]"

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
        try:
            result = await asyncio.wait_for(
                agent.execute(enriched_context, thread),
                timeout=SUBTASK_TIMEOUT,
            )
        except asyncio.TimeoutError:
            result = "[Timeout] Agent did not respond in time. Try a simpler query or try again."
            subtask.status = TaskStatus.FAILED
            subtask.latency_ms = (time.monotonic() - t0) * 1000
            subtask.result = result
            return result
        subtask.latency_ms = (time.monotonic() - t0) * 1000
        subtask.status = TaskStatus.COMPLETED
        subtask.result = result

        # Auto-evaluate agent output quality
        try:
            from tools.agent_eval import score_agent_output, detect_task_type
            task_type = detect_task_type(subtask.description)
            score_agent_output(
                agent_role=subtask.assigned_agent.value,
                task_type=task_type,
                output=result,
                tokens_used=subtask.token_usage,
                latency_ms=subtask.latency_ms,
                task_preview=subtask.description[:200],
            )
        except Exception:
            pass  # Never break pipeline for evaluation

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
                text = result
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

