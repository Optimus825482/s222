"""
Qwen3 Next 80B — Orchestrator Agent.
The brain: task analysis, decomposition, routing, synthesis.
"""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from core.models import (
    AgentRole, EventType, PipelineType, SubTask, Task, Thread,
)
from core.events import build_orchestrator_context
from tools.registry import ORCHESTRATOR_TOOLS


class OrchestratorAgent(BaseAgent):
    role = AgentRole.ORCHESTRATOR
    model_key = "orchestrator"

    def system_prompt(self) -> str:
        return (
            "You are the Orchestrator of a multi-agent system. You coordinate 4 specialist agents:\n\n"
            "AGENTS:\n"
            "- thinker (MiniMax M2.1): Deep analysis, complex reasoning, planning, architecture\n"
            "- speed (Step 3.5 Flash): Quick answers, code generation, formatting, simple tasks\n"
            "- researcher (GLM 4.7): Web search, current info, data gathering, fact-checking\n"
            "- reasoner (Nemotron 3 Nano): Math, logic, chain-of-thought, verification\n\n"
            "PIPELINE TYPES:\n"
            "- sequential: Tasks flow A → B → C (each uses previous output)\n"
            "- parallel: Tasks run simultaneously, results merged\n"
            "- consensus: All agents answer same question, best selected\n"
            "- iterative: One agent produces, another reviews, refine until good\n\n"
            "SKILL SYSTEM:\n"
            "- Use find_skill to discover relevant skills BEFORE decomposing tasks\n"
            "- Use use_skill to load skill knowledge when needed\n"
            "- When decomposing, you can assign skill IDs to sub-tasks via the 'skills' field\n"
            "- Skills provide specialized protocols and knowledge to agents\n\n"
            "DECISION RULES:\n"
            "1. Simple question → use direct_response (no delegation)\n"
            "2. Need current info → researcher (sequential or parallel with others)\n"
            "3. Complex analysis → thinker (+ reasoner for verification if needed)\n"
            "4. Code task → speed (+ reasoner for review if complex)\n"
            "5. Math/logic → reasoner\n"
            "6. Multi-faceted → parallel pipeline with relevant agents\n"
            "7. High-stakes → consensus pipeline for reliability\n"
            "8. Specialized domain → find_skill first, then assign skills to agents\n\n"
            "Use decompose_task to break work into sub-tasks.\n"
            "Use direct_response for simple queries.\n"
            "Use synthesize_results after all sub-tasks complete.\n\n"
            "Be decisive. Route efficiently. Minimize unnecessary delegation."
        )

    def get_tools(self) -> list[dict]:
        return ORCHESTRATOR_TOOLS

    def build_context(self, thread: Thread, task_input: str) -> list[dict[str, str]]:
        """Orchestrator sees full context."""
        history = build_orchestrator_context(thread)
        messages = [{"role": "system", "content": self.system_prompt()}]
        if history.strip():
            messages.append({"role": "user", "content": f"Thread history:\n{history}"})
            messages.append({"role": "assistant", "content": "I have the full context."})
        messages.append({"role": "user", "content": task_input})
        return messages

    async def handle_tool_call(self, fn_name: str, fn_args: dict, thread: Thread) -> str:
        """Process orchestrator tool calls — routing decisions + shared tools."""
        if fn_name == "decompose_task":
            return await self._handle_decompose(fn_args, thread)
        elif fn_name == "direct_response":
            return fn_args.get("response", "")
        elif fn_name == "synthesize_results":
            return fn_args.get("final_response", "")
        # Delegate shared tools (find_skill, use_skill, web_fetch) to base
        return await super().handle_tool_call(fn_name, fn_args, thread)

    async def _handle_decompose(self, fn_args: dict, thread: Thread) -> str:
        """Create Task with SubTasks from decomposition."""
        pipeline_str = fn_args.get("pipeline_type", "sequential")
        pipeline_type = PipelineType(pipeline_str)

        sub_tasks = []
        for st_data in fn_args.get("sub_tasks", []):
            st = SubTask(
                description=st_data["description"],
                assigned_agent=AgentRole(st_data["assigned_agent"]),
                priority=st_data.get("priority", 1),
                depends_on=st_data.get("depends_on", []),
                skills=st_data.get("skills", []),
            )
            sub_tasks.append(st)

        # Find or create current task
        task = Task(
            user_input=thread.events[-1].content if thread.events else "",
            pipeline_type=pipeline_type,
            sub_tasks=sub_tasks,
        )
        thread.tasks.append(task)

        reasoning = fn_args.get("reasoning", "")
        thread.add_event(
            EventType.ROUTING_DECISION,
            f"Pipeline: {pipeline_type.value} | Sub-tasks: {len(sub_tasks)} | {reasoning}",
            agent_role=self.role,
        )

        summary_parts = [f"Task decomposed → {pipeline_type.value} pipeline:"]
        for i, st in enumerate(sub_tasks, 1):
            summary_parts.append(f"  {i}. [{st.assigned_agent.value}] {st.description}")
        return "\n".join(summary_parts)

    async def route_and_execute(self, user_input: str, thread: Thread) -> str:
        """
        Main entry point: user message → orchestrator decides → pipeline runs → result.
        This is called by the UI layer.
        """
        thread.add_event(EventType.USER_MESSAGE, user_input)

        # Step 1: Orchestrator decides what to do
        decision = await self.execute(user_input, thread)

        # Check if it was a direct response (no delegation needed)
        last_events = thread.events[-5:]
        for ev in reversed(last_events):
            if ev.event_type == EventType.TOOL_CALL and "direct_response" in ev.content:
                return decision

        # Step 2: If tasks were created, run the pipeline
        if thread.tasks:
            current_task = thread.tasks[-1]
            if current_task.sub_tasks:
                from pipelines.engine import PipelineEngine
                engine = PipelineEngine()
                result = await engine.execute(current_task, thread)

                # Step 3: Synthesize
                synth_input = (
                    f"The specialists have completed their work. Here are the results:\n\n"
                    f"{result}\n\n"
                    f"Original user request: {user_input}\n\n"
                    f"Synthesize a clear, comprehensive final response."
                )
                final = await self.execute(synth_input, thread)
                current_task.final_result = final
                return final

        return decision
