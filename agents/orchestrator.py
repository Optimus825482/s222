"""
DeepSeek Chat — Orchestrator Agent.
The brain: intent analysis, pipeline selection, skill discovery, task delegation, synthesis.
5-Phase Pipeline: Intent → Pipeline → Skills → Delegate → Synthesize.
Deep Research mode: auto-detects complex queries and fans out to ALL agents in parallel.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
from typing import Any

from agents.base import BaseAgent
from core.models import (
    AgentRole, EventType, PipelineType, SubTask, Task, TaskStatus, Thread,
)
from core.events import build_orchestrator_context
from tools.registry import ORCHESTRATOR_TOOLS
from tools.cache import get_cached_response, cache_response

# Keywords that trigger brainstorm mode (Turkish + English)
_BRAINSTORM_PATTERNS = re.compile(
    r"(beyin fırtınası|brainstorm|tartış|debate|discuss|fikir alışverişi|"
    r"farklı bakış|different perspective|pros?\s+cons|artı\s+eksi|"
    r"ne dersiniz|ne düşünüyorsunuz|görüş|opinion|"
    r"avantaj.*dezavantaj|lehte.*aleyhte|for\s+and\s+against)",
    re.IGNORECASE,
)

# Keywords that trigger deep research mode (Turkish + English)
# More strict - only for complex research tasks
_DEEP_RESEARCH_PATTERNS = re.compile(
    r"(kapsamlı\s+araştır|comprehensive\s+research|derinlemesine\s+araştır|in-depth\s+research|"
    r"detaylı\s+araştır|detailed\s+research|araştırma\s+yap|conduct\s+research|"
    r"karşılaştırmalı\s+analiz|comparative\s+analysis|detaylı\s+analiz|detailed\s+analysis|"
    r"piyasa\s+araştır|market\s+research|sektör\s+analiz|industry\s+analysis|"
    r"literatür\s+tarama|literature\s+review|akademik\s+araştır|academic\s+research|"
    r"rekabet\s+analiz|competitive\s+analysis|rakip\s+analiz|competitor\s+analysis|"
    r"teknoloji\s+araştır|technology\s+research|ürün\s+karşılaştır|product\s+comparison)",
    re.IGNORECASE,
)

# Patterns that trigger idea-to-project mode (Turkish + English)
_IDEA_PROJECT_PATTERNS = re.compile(
    r"(proje yap|proje oluştur|proje kur|projeye dönüştür|fikrim var|"
    r"build me|create a project|scaffold|start a project|"
    r"uygulama yap|uygulama geliştir|app yap|site yap|"
    r"bunu yap|şunu yap|geliştirmek istiyorum|yapmak istiyorum|"
    r"idea to project|fikri projeye|mvp|startup fikri|"
    r"bir .{0,30} yap|bir .{0,30} oluştur|bir .{0,30} geliştir)",
    re.IGNORECASE,
)

# Patterns that trigger presentation generation (Turkish + English)
_PRESENTATION_PATTERNS = re.compile(
    r"(sunum yap|sunum hazırla|sunum oluştur|slayt yap|slayt hazırla|"
    r"pptx|ppt yap|powerpoint|presentation|slide|"
    r"sunum .{0,30} hazırla|.{0,30} sunumu|.{0,30} slayt)",
    re.IGNORECASE,
)

# Patterns that detect MINI/MIDI/MAXI mode selection
_PRESENTATION_MODE_PATTERNS = re.compile(
    r"^\s*(MINI|MIDI|MAXI)(?:\s+(\d+))?\s*$",
    re.IGNORECASE,
)

# Short/simple patterns that should NOT trigger deep research
_SIMPLE_PATTERNS = re.compile(
    r"^(merhaba|hello|hi|hey|selam|test|ping|saat kaç|what time|"
    r"teşekkür|thanks|thank you|ok|tamam|evet|hayır|yes|no)[\s!?.]*$",
    re.IGNORECASE,
)

_MEMORY_STATS_PATTERNS = re.compile(
    r"(memory\s*stats|hafıza\s*istatistik|bellek\s*istatistik)",
    re.IGNORECASE,
)

_LIST_MEMORIES_PATTERNS = re.compile(
    r"(list\s+memories|memories\s+list|hafızaları\s+listele|bellekleri\s+listele)",
    re.IGNORECASE,
)

_LIST_RAG_DOCS_PATTERNS = re.compile(
    r"(list\s+documents|rag\s+documents|dokümanları\s+listele|dökümanları\s+listele)",
    re.IGNORECASE,
)


logger = logging.getLogger(__name__)


def _status_meta(status: TaskStatus | str) -> dict[str, str]:
    canonical = TaskStatus.normalize(status)
    return {
        "run_state": canonical,
        "run_state_alias": TaskStatus.legacy_alias(status),
    }


def _transition_meta(previous: TaskStatus | str, current: TaskStatus | str) -> dict[str, str]:
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
    agent_role: AgentRole | None = AgentRole.ORCHESTRATOR,
    strict: bool = False,
    **meta: Any,
) -> None:
    previous = task.status
    prev_canonical = TaskStatus.normalize(previous)
    next_canonical = TaskStatus.normalize(next_status)
    transition_allowed = TaskStatus.can_transition(previous, next_status)
    if not transition_allowed:
        logger.warning(
            "run.state.invalid_transition",
            extra={
                "event": "run.state.invalid_transition",
                "thread_id": thread.id,
                "task_id": task.id,
                "from_state": prev_canonical,
                "to_state": next_canonical,
                "legacy_from": TaskStatus.legacy_alias(previous),
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
        **_transition_meta(previous, task.status),
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
            "legacy_from": TaskStatus.legacy_alias(previous),
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
                run_state_prev_alias=TaskStatus.legacy_alias(previous),
                run_state_transition=f"{prev_canonical}->{TaskStatus.normalize(task.status)}",
                thread_id=thread.id,
                task_id=task.id,
            )
        except Exception:
            pass


_LIST_TEACHINGS_PATTERNS = re.compile(
    r"(list\s+teachings|teachings\s+list|öğretileri\s+listele|tercihleri\s+listele)",
    re.IGNORECASE,
)


class OrchestratorAgent(BaseAgent):
    role = AgentRole.ORCHESTRATOR
    model_key = "orchestrator"

    def __init__(self) -> None:
        super().__init__()
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        """Subscribe to relevant EventBus channels."""
        try:
            bus = self.bus
            if bus:
                bus.subscribe(
                    agent_role=self.role.value,
                    channel="task.*",
                    handler=self._on_task_message,
                )
                bus.subscribe(
                    agent_role=self.role.value,
                    channel="metrics.*",
                    handler=self._on_metrics_message,
                )
        except Exception:
            pass  # EventBus not ready yet

    async def _on_task_message(self, msg):
        """Handle incoming task messages."""
        pass

    async def _on_metrics_message(self, msg):
        """Handle metrics messages."""
        pass

    def system_prompt(self) -> str:
        return (
            "You are the Orchestrator of a multi-agent system. You run a 5-Phase Pipeline:\n"
            "Intent Analysis → Pipeline Selection → Skill Discovery → Task Delegation → Synthesis.\n\n"
            "PRIMARY RULE: Understand user intent BEFORE acting. If unsure (< 70%), ask a clarification question.\n\n"
            "AGENTS (delegate via decompose_task):\n"
            "- researcher: Web search, data gathering, fact-checking\n"
            "- thinker: Deep analysis, reasoning, planning\n"
            "- reasoner: Math, logic, verification\n"
            "- speed: Quick answers, code, formatting\n"
            "- critic: Quality review, fact-checking\n\n"
            "🔗 INTER-AGENT COMMUNICATION:\n"
            "Agents can communicate with each other using these tools:\n"
            "- send_agent_message: Send message to another agent (collab_request, task_delegation, alert)\n"
            "- check_agent_messages: Check for pending messages from other agents\n"
            "- share_knowledge: Share findings with all agents\n"
            "- get_shared_knowledge: Get knowledge shared by other agents\n"
            "- suggest_collaborator: Get suggestion for which agent to collaborate with\n"
            "Use these when agents need to coordinate or share information!\n\n"
            "TOOL DECISION:\n"
            "- Simple greeting/trivial → direct_response\n"
            "- Short question (< 50 chars) → assign to ONE agent (speed or researcher)\n"
            "- Complex task → decompose_task with parallel, 2-3 agents\n"
            "- Deep research → decompose_task with deep_research, 3-5 agents\n\n"
            "CRITICAL RULES:\n"
            "1. Short/simple queries → ONE agent for SPEED\n"
            "2. Complex queries → 2-3 agents in PARALLEL\n"
            "3. Instruct agents to USE THEIR TOOLS in task descriptions\n"
            "4. NEVER fabricate URLs or fake download links\n\n"
            "YOUR TOOLS:\n"
            "- decompose_task: Break work into sub-tasks (prefer parallel)\n"
            "- direct_response: Simple answers only\n"
            "- web_search / web_fetch: Search/fetch web content\n"
            "- summarize_video: Extract info + transcript + summary from YouTube videos\n"
            "- fetch_transcript: Fetch raw transcript from YouTube videos (with auto-translation)\n"
            "- find_skill / use_skill: Load specialized knowledge\n"
            "- save_memory / recall_memory: Persistent memory\n"
            "- code_execute: Run Python/JS/Bash\n"
            "- rag_query: Query knowledge base\n"
            "- generate_image / generate_chart: Create visuals\n"
            "- create_skill: Create new skills\n"
            "- mcp_call: Call external MCP services (IMPORTANT!)\n"
            "- mcp_list_tools: Discover available MCP tools\n"
            "- send_agent_message: Message other agents\n"
            "- check_agent_messages: Check pending messages\n"
            "- share_knowledge / get_shared_knowledge: Share knowledge between agents\n\n"
            "🔌 MCP SERVERS (USE THESE FIRST!):\n"
            "BEFORE using web_search, check if an MCP server is more appropriate:\n"
            "- Academic papers → mcp_call to 'arxiv' server\n"
            "- Financial data → mcp_call to 'yahoo-finance' server\n"
            "- Wikipedia info → mcp_call to 'wikipedia' server\n"
            "- Web browsing (JS pages) → mcp_call to 'puppeteer' server\n"
            "- Database queries → mcp_call to 'postgres' or 'sqlite' server\n"
            "- File operations → mcp_call to 'filesystem' server\n"
            "Always use mcp_list_tools first to discover available tools!\n\n"
            "BE FAST: Short queries should complete in 15-30 seconds. Use fewer agents when possible."
        )

    def get_tools(self) -> list[dict]:
        return ORCHESTRATOR_TOOLS

    async def build_context(
        self, thread: Thread, task_input: str
    ) -> list[dict[str, str]]:
        """Orchestrator sees full context + relevant memories + current date."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%d %B %Y, %A, %H:%M UTC")
        date_injection = (
            f"\n\nCURRENT DATE AND TIME: {date_str}. "
            f"Year is {now.year}. Use this as the real current date and time for all responses."
        )

        history = build_orchestrator_context(thread)

        # Auto-recall relevant memories
        memory_context = ""
        try:
            from tools.memory import recall_memory, format_recall_results

            memories = await recall_memory(query=task_input, max_results=3)
            if memories:
                memory_context = (
                    "\n\n--- RELEVANT MEMORIES ---\n"
                    + format_recall_results(memories)
                    + "\n--- END MEMORIES ---\n"
                )
        except Exception:
            pass

        # Auto-inject user teachings/preferences
        teaching_context = ""
        try:
            from tools.teachability import get_relevant_teachings, format_teachings_for_context
            teachings = get_relevant_teachings(task_input, max_results=5)
            if teachings:
                teaching_context = "\n\n" + format_teachings_for_context(teachings) + "\n"
        except Exception:
            pass

        system_content = self.system_prompt() + date_injection
        if teaching_context:
            system_content += teaching_context

        messages = [{"role": "system", "content": system_content}]
        if history.strip() or memory_context:
            ctx = ""
            if history.strip():
                ctx += f"Thread history:\n{history}"
            if memory_context:
                ctx += memory_context
            messages.append({"role": "user", "content": ctx})
            messages.append({"role": "assistant", "content": "I have the full context."})
        messages.append({"role": "user", "content": task_input})
        return messages

    # Agent names that the model might call directly as tools
    _AGENT_NAMES = {"thinker", "speed", "researcher", "reasoner", "critic"}

    # ── Deep Research Detection ──────────────────────────────────

    def _detect_deep_research(self, user_input: str) -> bool:
        """
        Detect if the user query warrants deep research mode.
        Returns True for complex queries that should fan out to all agents.
        """
        # Simple/trivial → no deep research
        if _SIMPLE_PATTERNS.match(user_input.strip()):
            return False

        # Very short queries (< 15 chars) are usually simple
        if len(user_input.strip()) < 15:
            return False

        # Idea-to-project queries should NOT go to deep research
        if _IDEA_PROJECT_PATTERNS.search(user_input):
            return False

        # Presentation queries should NOT go to deep research
        if _PRESENTATION_PATTERNS.search(user_input):
            return False

        # Internal presentation prompts should NOT go to deep research
        if "SLIDE" in user_input and "IMAGE:" in user_input:
            return False
        if user_input.strip().startswith("Create a professional") and "presentation" in user_input.lower():
            return False

        # Check for deep research keywords
        if _DEEP_RESEARCH_PATTERNS.search(user_input):
            return True

        # Long queries (> 60 chars) with question marks are likely complex
        if len(user_input.strip()) > 60 and "?" in user_input:
            return True

        # Multiple sentences suggest complexity
        sentences = [s.strip() for s in re.split(r'[.!?]', user_input) if s.strip()]
        if len(sentences) >= 3:
            return True

        return False

    def _build_deep_research_tasks(self, user_input: str) -> list[dict]:
        """Build parallel sub-tasks for deep research mode.
        Short queries use 2 agents (researcher + speed) for faster response.
        Task descriptions explicitly instruct agents to USE their tools."""
        query_len = len(user_input.strip())
        quick_research = query_len < 180  # short query → fewer agents, faster

        if quick_research:
            return [
                {
                    "description": (
                        f"Research this topic using your tools: {user_input}\n"
                        "REQUIRED: Use web_search to find 2-4 good sources. "
                        "Use web_fetch on the best URLs for details. "
                        "Check mcp_list_tools for any relevant data sources. "
                        "Cite all URLs. Be concise but evidence-based."
                    ),
                    "assigned_agent": "researcher",
                    "priority": 1,
                },
                {
                    "description": (
                        f"Summarize and structure: {user_input}\n"
                        "If you need current data, use web_search first. "
                        "Clear sections, bullets, key takeaways. Keep it readable and short."
                    ),
                    "assigned_agent": "speed",
                    "priority": 1,
                },
            ]
        # Full deep research: 5 agents
        return [
            {
                "description": (
                    f"Research this topic thoroughly using ALL your tools: {user_input}\n"
                    "REQUIRED STEPS:\n"
                    "1. Use web_search with multiple different queries to find diverse sources\n"
                    "2. Use web_fetch on the top 2-3 URLs to get full content\n"
                    "3. Use mcp_list_tools to check for specialized data sources, then mcp_call if relevant\n"
                    "4. Use rag_query to check internal knowledge base\n"
                    "5. Synthesize findings with source URLs cited\n"
                    "Do NOT skip tool usage — real data beats assumptions."
                ),
                "assigned_agent": "researcher",
                "priority": 1,
            },
            {
                "description": (
                    f"Provide deep analysis for: {user_input}\n"
                    "REQUIRED: Use web_search to verify your claims and gather evidence. "
                    "Use web_fetch for detailed reading of key sources. "
                    "Check mcp_list_tools for specialized analysis tools. "
                    "Consider multiple perspectives, pros/cons, trade-offs, "
                    "strategic implications, and long-term impact. Be thorough and evidence-based."
                ),
                "assigned_agent": "thinker",
                "priority": 1,
            },
            {
                "description": (
                    f"Verify and reason about: {user_input}\n"
                    "REQUIRED: Use web_search to fact-check claims. "
                    "Use code_execute for any calculations or data verification. "
                    "Check logical consistency, identify potential biases or errors, "
                    "validate claims with chain-of-thought reasoning backed by evidence."
                ),
                "assigned_agent": "reasoner",
                "priority": 1,
            },
            {
                "description": (
                    f"Prepare a well-structured summary for: {user_input}\n"
                    "Use web_search if you need current data to enrich the summary. "
                    "Create clear formatting with sections, bullet points, "
                    "and actionable takeaways. Focus on readability."
                ),
                "assigned_agent": "speed",
                "priority": 1,
            },
            {
                "description": (
                    f"Critically evaluate all findings about: {user_input}\n"
                    "Use web_search to cross-check claims from other agents. "
                    "Find weaknesses, missing perspectives, unsupported claims. "
                    "Suggest concrete improvements. Rate overall quality."
                ),
                "assigned_agent": "critic",
                "priority": 2,
            },
        ]


    # ── Idea-to-Project Detection ───────────────────────────────────

    def _detect_idea_to_project(self, user_input: str) -> bool:
        """Detect if user wants to transform an idea into a project."""
        if _SIMPLE_PATTERNS.match(user_input.strip()):
            return False
        if len(user_input.strip()) < 15:
            return False
        return bool(_IDEA_PROJECT_PATTERNS.search(user_input))

    def _detect_brainstorm(self, user_input: str) -> bool:
        """Detect if user wants a brainstorm/debate session."""
        if _SIMPLE_PATTERNS.match(user_input.strip()):
            return False
        if len(user_input.strip()) < 15:
            return False
        # Don't trigger brainstorm for idea-to-project or presentation
        if _IDEA_PROJECT_PATTERNS.search(user_input):
            return False
        if _PRESENTATION_PATTERNS.search(user_input):
            return False
        return bool(_BRAINSTORM_PATTERNS.search(user_input))

    def _detect_presentation(self, user_input: str) -> bool:
        """Detect if user wants to generate a presentation."""
        if _SIMPLE_PATTERNS.match(user_input.strip()):
            return False
        if len(user_input.strip()) < 10:
            return False
        return bool(_PRESENTATION_PATTERNS.search(user_input))

    def _detect_direct_tool_intent(
        self, user_input: str
    ) -> tuple[str, dict[str, Any]] | None:
        """Deterministically route explicit operational requests to the right shared tool."""
        text = user_input.strip()
        if not text:
            return None

        if _MEMORY_STATS_PATTERNS.search(text):
            return ("memory_stats", {})
        if _LIST_MEMORIES_PATTERNS.search(text):
            return ("list_memories", {"limit": 20})
        if _LIST_RAG_DOCS_PATTERNS.search(text):
            return ("rag_list_documents", {"limit": 20})
        if _LIST_TEACHINGS_PATTERNS.search(text):
            return ("list_teachings", {"active_only": True})
        return None

    # ── Tool Call Handling ────────────────────────────────────────

    async def handle_tool_call(self, fn_name: str, fn_args: dict, thread: Thread) -> str:
        """Process orchestrator tool calls — routing decisions + shared tools."""
        if fn_name == "decompose_task":
            return await self._handle_decompose(fn_args, thread)
        elif fn_name == "direct_response":
            return fn_args.get("response", "")
        elif fn_name == "synthesize_results":
            return fn_args.get("final_response", "")
        elif fn_name == "idea_to_project":
            return await self._handle_idea_to_project(fn_args, thread)
        elif fn_name == "generate_presentation":
            return await self._handle_generate_presentation(fn_args, thread)
        elif fn_name == "research_create_skill":
            return await self._handle_research_create_skill(fn_args, thread)

        # Catch model calling agent names directly as tools
        # Auto-upgrade to multi-agent parallel if task is complex
        if fn_name in self._AGENT_NAMES:
            query = (
                fn_args.get("query")
                or fn_args.get("task")
                or fn_args.get("input")
                or fn_args.get("description")
                or ""
            )
            if not query or query in ("{}", "{}}", ""):
                for ev in reversed(thread.events):
                    if ev.event_type == EventType.USER_MESSAGE:
                        query = ev.content
                        break
            if not query:
                query = json.dumps(fn_args, ensure_ascii=False)

            # Auto-upgrade: if task is complex, fan out to all agents
            if self._detect_deep_research(query):
                self._emit("routing", f"Auto-upgrade: {fn_name} → parallel multi-agent")
                return await self._handle_decompose({
                    "sub_tasks": self._build_deep_research_tasks(query),
                    "pipeline_type": "parallel",
                    "reasoning": f"Auto-upgraded from single {fn_name} call to parallel multi-agent",
                }, thread)

            # Simple task — route to single agent
            return await self._handle_decompose({
                "sub_tasks": [{
                    "description": query,
                    "assigned_agent": fn_name,
                    "priority": 1,
                }],
                "pipeline_type": "sequential",
                "reasoning": f"Auto-routed: model called {fn_name} directly",
            }, thread)

        elif fn_name == "run_workflow":
            return await self._handle_run_workflow(fn_args, thread)
        elif fn_name == "list_workflows":
            return await self._handle_list_workflows(fn_args)
        elif fn_name == "domain_expert":
            return await self._handle_domain_expert(fn_args, thread)
        elif fn_name == "list_domain_tools":
            return self._handle_list_domain_tools(fn_args)

        # Delegate shared tools to base
        return await super().handle_tool_call(fn_name, fn_args, thread)

    async def _handle_idea_to_project(self, fn_args: dict, thread: Thread) -> str:
        """Run the Idea-to-Project pipeline through specialist agents.

        Improvements:
        - Context summarization between phases to prevent bloat
        - Quality gate on final output
        - Phase-level progress events
        """
        from tools.idea_to_project import (
            PHASES,
            get_phase_prompt,
            detect_project_type,
            save_project_output,
        )
        from pipelines.engine import PipelineEngine, _summarize_phase_output

        idea = fn_args["idea"]
        project_type = fn_args.get("project_type") or detect_project_type(idea)
        target_phase = fn_args.get("phase", "all")

        thread.add_event(
            EventType.ROUTING_DECISION,
            f"Idea-to-Project: type={project_type}, phase={target_phase}",
            agent_role=self.role,
        )
        self._emit("routing", f"🚀 Idea-to-Project başlatılıyor — {project_type}")

        results = {}
        prev_result = ""

        phases_to_run = PHASES if target_phase == "all" else [
            p for p in PHASES if p["id"] == target_phase
        ]

        engine = PipelineEngine()
        if self._live_monitor:
            engine.set_live_monitor(self._live_monitor)

        for i, phase in enumerate(phases_to_run):
            self._emit("pipeline", f"📋 Faz {i+1}/{len(phases_to_run)}: {phase['name']}")

            # Summarize previous result to prevent context bloat
            compressed_prev = prev_result
            if len(prev_result) > 2000 and phase["id"] not in ("analyze",):
                compressed_prev = _summarize_phase_output(phase["id"], prev_result)

            prompt = get_phase_prompt(phase["id"], idea, compressed_prev)
            agent_role = AgentRole(phase["agent"])
            agent = engine.get_agent(agent_role)

            result = await agent.execute(prompt, thread)
            results[phase["id"]] = result
            prev_result = result

            # Save phase output
            project_name = idea[:50].strip()
            save_project_output(project_name, phase["id"], result)

        # Build summary
        parts = [f"🚀 IDEA-TO-PROJECT: {project_type}\n"]
        for phase in phases_to_run:
            if phase["id"] in results:
                parts.append(f"\n{'='*60}")
                parts.append(f"📋 {phase['name'].upper()}")
                parts.append(f"{'='*60}")
                parts.append(results[phase["id"]])

        final = "\n".join(parts)

        # Quality Gate on final output
        try:
            final, qg_passed = await self._quality_gate(final, idea, thread)
            if not qg_passed and self._live_monitor:
                self._live_monitor.emit("pipeline", "orchestrator", "⚠️ Quality Gate: refinement önerildi")
        except Exception:
            pass

        return final

    async def _handle_generate_presentation(self, fn_args: dict, thread: Thread) -> str:
        """Generate a professional PPTX presentation with deep research + AI visuals.
        Supports MINI/MIDI/MAXI modes and uses thinker agent for content quality."""
        from tools.presentation_service import (
            build_presentation_prompt, parse_slide_content, generate_presentation,
            deep_research_for_presentation, format_research_for_prompt,
            MODE_CONFIG, PresentationMode,
        )
        from pipelines.engine import PipelineEngine

        topic = fn_args.get("topic", "")
        mode: PresentationMode = fn_args.get("mode", "midi")
        language = fn_args.get("language", "tr")
        theme = fn_args.get("theme", "corporate")

        cfg = MODE_CONFIG[mode]
        slide_count = fn_args.get("slide_count", cfg["default_slides"])

        thread.add_event(
            EventType.ROUTING_DECISION,
            f"Presentation: topic={topic[:60]}, mode={mode.upper()}, slides={slide_count}, lang={language}",
            agent_role=self.role,
        )
        self._emit("routing", f"🎨 Sunum hazırlanıyor — {cfg['emoji']} {cfg['label']} mod, {slide_count} slayt")

        # Step 0: Deep Research — depth scales with mode
        self._emit("pipeline", f"🔬 Deep Research başlatılıyor ({cfg['research_queries']} sorgu, {mode.upper()} derinlik)...")
        try:
            research = await deep_research_for_presentation(
                topic, language=language,
                max_queries=cfg["research_queries"],
                mode=mode,
            )
            research_context = format_research_for_prompt(research)
            source_count = research.get("total_sources", 0)
            self._emit("pipeline", f"📊 {source_count} kaynak bulundu, içerik zenginleştiriliyor...")
        except Exception as e:
            print(f"[Orchestrator] Deep research failed: {e}")
            research_context = ""
            self._emit("pipeline", "⚠️ Araştırma tamamlanamadı, mevcut bilgiyle devam ediliyor...")

        # Step 1: Use thinker agent (MiniMax M2.1) for higher quality content generation
        prompt = build_presentation_prompt(
            topic, slide_count, language,
            research_context=research_context,
            mode=mode,
        )
        engine = PipelineEngine()
        if self._live_monitor:
            engine.set_live_monitor(self._live_monitor)

        # Use thinker for MIDI/MAXI, researcher for MINI (faster)
        if mode in ("midi", "maxi"):
            content_agent = engine.get_agent(AgentRole.THINKER)
            agent_label = "Thinker (MiniMax M2.1)"
        else:
            content_agent = engine.get_agent(AgentRole.RESEARCHER)
            agent_label = "Researcher (GLM 4.7)"

        self._emit("pipeline", f"📝 Slayt içeriği oluşturuluyor — {agent_label} ile...")
        raw_content = await content_agent.execute(prompt, thread)

        # Debug: log raw content length for troubleshooting
        print(f"[Presentation] Raw content length: {len(raw_content)} chars, first 500: {raw_content[:500]}")

        # If agent returned error/empty/stopped, try fallback agent
        if not raw_content or raw_content.startswith("[Error]") or raw_content.startswith("[Stopped]") or len(raw_content.strip()) < 50:
            print(f"[Presentation] Primary agent failed or returned empty, trying fallback agent...")
            self._emit("pipeline", f"⚠️ {agent_label} boş döndü, yedek agent deneniyor...")
            # Swap: if thinker failed, try researcher; if researcher failed, try thinker
            if mode in ("midi", "maxi"):
                fallback_agent = engine.get_agent(AgentRole.RESEARCHER)
                agent_label = "Researcher (GLM 4.7) [fallback]"
            else:
                fallback_agent = engine.get_agent(AgentRole.THINKER)
                agent_label = "Thinker (MiniMax M2.1) [fallback]"
            self._emit("pipeline", f"📝 Yedek agent ile deneniyor — {agent_label}...")
            raw_content = await fallback_agent.execute(prompt, thread)
            print(f"[Presentation] Fallback content length: {len(raw_content)} chars, first 500: {raw_content[:500]}")

        # Step 2: Parse structured slides
        slides_data = parse_slide_content(raw_content)

        # Fallback: if strict parsing failed, try to build slides from raw content
        if not slides_data:
            print(f"[Presentation] parse_slide_content returned 0 slides, attempting fallback...")
            paragraphs = [p.strip() for p in raw_content.split("\n\n") if p.strip() and len(p.strip()) > 10]
            for i, para in enumerate(paragraphs[:slide_count], 1):
                lines = [l.strip() for l in para.split("\n") if l.strip()]
                title = lines[0][:80].lstrip("#- •*0123456789.)") .strip() if lines else f"Slayt {i}"
                if not title:
                    title = f"Slayt {i}"
                bullets = []
                for l in lines[1:6]:
                    clean = l.lstrip("#- •*0123456789.)").strip()
                    if clean and len(clean) > 3:
                        bullets.append(clean)
                if not bullets and len(lines) > 0:
                    bullets = [lines[0][:100]]
                slides_data.append({
                    "num": i,
                    "title": title,
                    "bullets": bullets,
                    "image_prompt": f"Professional visual about {topic}, slide {i}",
                    "is_section": False,
                    "quote": None,
                    "data_highlights": [],
                })
            print(f"[Presentation] Fallback produced {len(slides_data)} slides")

        if not slides_data:
            return "❌ Slayt içeriği oluşturulamadı. Agent boş yanıt döndü. Lütfen tekrar deneyin."

        self._emit("pipeline", f"🖼️ {len(slides_data)} slayt için görseller üretiliyor...")

        # Step 3: Generate PPTX with images and theme
        pptx_bytes = await generate_presentation(
            slides_data=slides_data,
            title=topic,
            subtitle=f"{cfg['emoji']} {cfg['label']} | {len(slides_data)} Slayt | AI Destekli Sunum",
            with_images=True,
            theme=theme,
        )

        # Step 4: Save to disk
        from pathlib import Path
        presentations_dir = Path(__file__).parent.parent / "data" / "presentations"
        presentations_dir.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r"[^\w\s-]", "", topic[:50]).strip().replace(" ", "_")
        if not safe_name:
            safe_name = "sunum"
        filename = f"{safe_name}_{mode}.pptx"
        filepath = presentations_dir / filename
        filepath.write_bytes(pptx_bytes)

        self._emit("pipeline", f"✅ Sunum kaydedildi: {filename}")

        source_info = ""
        if research_context:
            source_info = f"🔬 **Araştırma:** {source_count} web kaynağından veri toplandı ({cfg['research_queries']} sorgu)\n"

        # Build real download URL (local API endpoint)
        encoded_filename = urllib.parse.quote(filename)
        download_url = f"/api/presentations/{encoded_filename}/download"

        return (
            f"✅ **Sunum Hazır!**\n\n"
            f"📊 **Konu:** {topic}\n"
            f"🎯 **Mod:** {cfg['emoji']} {cfg['label']}\n"
            f"📄 **Slayt Sayısı:** {len(slides_data)} + başlık + kapanış\n"
            f"{source_info}"
            f"🤖 **İçerik:** {agent_label} ile üretildi\n"
            f"🖼️ **Görseller:** Pollinations.ai ile üretildi\n"
            f"🎨 **Tema:** {theme}\n"
            f"📁 **Dosya:** {filename}\n"
            f"📥 **İndir:** [{filename}]({download_url})\n\n"
            f"Sunumu indirmek için yukarıdaki linki veya aşağıdaki 🎨 PPTX butonunu kullanabilirsin."
        )

    async def _handle_research_create_skill(self, fn_args: dict, thread: Thread) -> str:
        """
        Research a topic via web search, synthesize findings with LLM,
        then create a structured Kiro skill package.
        4 phases: search → fetch → synthesize → create_skill_package
        """
        topic = fn_args["topic"]
        skill_id = fn_args["skill_id"]
        skill_name = fn_args["skill_name"]
        category = fn_args.get("category", "capability")
        search_queries = fn_args.get("search_queries") or [
            f"{topic} best practices libraries tools",
            f"{topic} step by step tutorial how to",
        ]

        self._emit("pipeline", f"🔬 Skill araştırması: {topic[:60]}")

        # Phase 1: Web search
        from tools.search import web_search, format_search_results
        all_results = []
        for query in search_queries[:4]:
            try:
                results = await web_search(query=query, max_results=5)
                all_results.extend(results)
                self._emit("tool_call", f"web_search: {query[:60]}", tool_name="web_search")
            except Exception:
                pass

        if not all_results:
            return f"Research failed: no web results for '{topic}'. Skill not created."

        # Phase 2: Fetch top pages for deeper content
        from tools.web_fetch import web_fetch, format_fetch_result
        fetched_content = []
        seen_urls = set()
        for r in all_results[:6]:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                try:
                    page = await web_fetch(url=url, max_chars=4000)
                    if page.get("content"):
                        fetched_content.append(f"Source: {url}\n{page['content'][:3000]}")
                        self._emit("tool_result", f"Fetched: {url[:60]}")
                except Exception:
                    pass
            if len(fetched_content) >= 3:
                break

        # Phase 3: LLM synthesis — turn raw research into structured skill knowledge
        search_summary = format_search_results(all_results[:10])
        fetch_summary = "\n\n---\n\n".join(fetched_content) if fetched_content else ""

        synthesis_prompt = (
            f"You are creating a SKILL PACKAGE for AI agents about: {topic}\n\n"
            f"WEB SEARCH RESULTS:\n{search_summary}\n\n"
            f"FETCHED PAGE CONTENT:\n{fetch_summary[:8000]}\n\n"
            f"Create a comprehensive, actionable skill document that teaches an AI agent "
            f"HOW to perform this capability. Include:\n"
            f"1. Overview — what this skill enables\n"
            f"2. Required libraries/tools/APIs with install commands\n"
            f"3. Step-by-step implementation instructions\n"
            f"4. Code patterns and examples\n"
            f"5. Common pitfalls and edge cases\n"
            f"6. Best practices\n\n"
            f"Write in Markdown. Be specific and actionable — not vague descriptions.\n"
            f"This will be injected into agent context, so make it directly usable."
        )

        messages = [
            {"role": "system", "content": "You are a technical skill documentation specialist."},
            {"role": "user", "content": synthesis_prompt},
        ]

        self._emit("pipeline", "🧠 Araştırma sentezleniyor → skill bilgisi oluşturuluyor...")
        try:
            response = await self.call_llm(messages)
            knowledge = response.get("content", "")
        except Exception as e:
            knowledge = f"Research summary:\n{search_summary[:3000]}"

        if not knowledge or len(knowledge.strip()) < 50:
            knowledge = f"Research summary:\n{search_summary[:3000]}"

        # Phase 4: Create skill package
        from tools.dynamic_skills import create_skill_package

        # Build references from fetched URLs
        references = {}
        for i, r in enumerate(all_results[:5]):
            url = r.get("url", "")
            title = r.get("title", f"source-{i+1}")
            snippet = r.get("snippet", "")
            if url:
                safe_name = f"source-{i+1}.md"
                references[safe_name] = f"# {title}\n\nURL: {url}\n\n{snippet}"

        result = create_skill_package(
            skill_id=skill_id,
            name=skill_name,
            description=f"Researched capability: {topic}",
            knowledge=knowledge,
            category=category,
            keywords=[w.strip() for w in topic.split()[:8]],
            references=references if references else None,
            source="research:orchestrator",
        )

        self._emit("pipeline", f"✅ Skill oluşturuldu: {skill_id}")

        return (
            f"Skill researched and created: [{result['id']}] {result['name']}\n"
            f"Path: {result.get('path', '')}\n"
            f"Sources: {len(references)} reference files saved\n"
            f"Knowledge: {len(knowledge)} chars of structured instructions\n"
            f"Inject into sub-tasks by adding '{result['id']}' to the skills list."
        )

    async def _handle_run_workflow(self, fn_args: dict, thread: Thread) -> str:
        """Execute a workflow template or custom workflow."""
        from tools.workflow_engine import (
            get_template,
            WORKFLOW_TEMPLATES,
            create_workflow,
            execute_workflow,
            WorkflowStep,
            Workflow,
        )

        template_name = fn_args.get("template", "")
        variables = fn_args.get("variables", {})
        custom_steps = fn_args.get("custom_steps")

        if template_name != "custom" and template_name in WORKFLOW_TEMPLATES:
            workflow = get_template(template_name, variables=variables)
        elif template_name == "custom" and custom_steps:
            steps = [WorkflowStep(**s) for s in custom_steps]
            workflow = Workflow(
                workflow_id=f"custom-{int(time.time())}",
                name="Custom Workflow",
                description="User-defined workflow",
                steps=steps,
                variables=variables,
            )
        else:
            return f"[Error] Unknown workflow template: {template_name}. Available: {', '.join(WORKFLOW_TEMPLATES.keys())}"

        self._emit("pipeline", f"🔄 Workflow başlatılıyor: {workflow.name}")
        result = await execute_workflow(workflow, thread)
        self._emit("pipeline", f"{'✅' if result.status == 'completed' else '❌'} Workflow tamamlandı: {result.status} ({result.duration_ms:.0f}ms)")

        parts = [f"Workflow: {workflow.name}", f"Status: {result.status}", f"Duration: {result.duration_ms:.0f}ms"]
        if result.error:
            parts.append(f"Error: {result.error}")
        for step_id, step_result in result.step_results.items():
            preview = str(step_result)[:300]
            parts.append(f"\n--- Step: {step_id} ---\n{preview}")
        return "\n".join(parts)

    async def _handle_list_workflows(self, fn_args: dict) -> str:
        """List workflow templates and optionally execution history."""
        from tools.workflow_engine import get_workflow_templates, list_workflow_results

        templates = get_workflow_templates()
        parts = ["Available Workflow Templates:"]
        for t in templates:
            parts.append(f"  - {t['id']}: {t['name']} — {t['description']}")

        if fn_args.get("include_history"):
            history = list_workflow_results(limit=10)
            if history:
                parts.append("\nRecent Executions:")
                for h in history:
                    parts.append(f"  - {h.get('workflow_id')}: {h.get('status')} ({h.get('duration_ms', 0):.0f}ms)")

        return "\n".join(parts)

    async def _handle_domain_expert(self, fn_args: dict, thread: Thread) -> str:
        """Execute a domain-specific expert tool."""
        from tools.domain_skills import execute_domain_tool

        domain = fn_args.get("domain", "")
        tool_name = fn_args.get("tool_name", "")
        arguments = fn_args.get("arguments", {})

        if not domain or not tool_name:
            return "[Error] domain and tool_name are required."

        self._emit("tool_call", f"🧠 Domain Expert: {domain}/{tool_name}")
        result = await execute_domain_tool(domain, tool_name, arguments)

        if result.get("success"):
            return json.dumps(result["result"], ensure_ascii=False, indent=2, default=str)
        else:
            return f"[Error] Domain tool failed: {result.get('error', 'unknown')}"

    def _handle_list_domain_tools(self, fn_args: dict) -> str:
        """List available domain expertise tools."""
        from tools.domain_skills import list_domains, get_domain_tools

        domain_filter = fn_args.get("domain")

        if domain_filter:
            tools = get_domain_tools(domain_filter)
            if tools is None:
                return f"[Error] Domain not found: {domain_filter}"
            parts = [f"Domain: {domain_filter}"]
            for t in tools:
                parts.append(f"  - {t['name']}: {t['description']}")
            return "\n".join(parts)

        domains = list_domains()
        parts = ["Available Domains:"]
        for d in domains:
            parts.append(f"\n📌 {d['name']} ({d['name_tr']})")
            parts.append(f"   {d['description']}")
            parts.append(f"   Capabilities: {', '.join(d['capabilities'][:4])}")
        return "\n".join(parts)

    async def _handle_decompose(self, fn_args: dict, thread: Thread) -> str:
        """Create Task with SubTasks from decomposition. Auto-discovers and injects relevant skills.
        When 2+ sub-tasks: always run multiparallel (all subagents at the same time)."""
        pipeline_str = fn_args.get("pipeline_type", "parallel")
        pipeline_type = PipelineType(pipeline_str)
        sub_tasks_data = fn_args.get("sub_tasks", [])
        # Multiparallel: 2+ sub-tasks always run simultaneously
        if len(sub_tasks_data) >= 2 and pipeline_type == PipelineType.SEQUENTIAL:
            pipeline_type = PipelineType.PARALLEL

        # Auto-discover relevant skills for each sub-task
        skill_cache: dict[str, list[dict]] = {}
        knowledge_cache: dict[str, str] = {}
        try:
            from tools.dynamic_skills import search_skills, get_full_skill_context
            for st_data in sub_tasks_data:
                desc = st_data.get("description", "")
                if desc and len(desc) > 10:
                    found = search_skills(query=desc[:200], max_results=2)
                    if found:
                        skill_cache[desc[:50]] = found
                        # Pre-load full knowledge for injection
                        for s in found:
                            if s["id"] not in knowledge_cache:
                                ctx = get_full_skill_context(s["id"])
                                if ctx:
                                    knowledge_cache[s["id"]] = ctx
        except Exception:
            pass

        sub_tasks = []
        for st_data in sub_tasks_data:
            desc = st_data["description"]
            # Collect skill IDs for this sub-task
            injected_skills = skill_cache.get(desc[:50], [])
            skill_ids = [s["id"] for s in injected_skills] + st_data.get("skills", [])

            # Inject skill knowledge summary into description so agent knows what to use
            if injected_skills:
                skill_hints = "\n\n[ACTIVATED SKILLS — use these capabilities]\n"
                for s in injected_skills:
                    hint = f"- **{s['name']}** ({s['id']}): {s['description']}"
                    # Add brief knowledge preview
                    kn = knowledge_cache.get(s["id"], "")
                    if kn:
                        preview = kn[:300].replace("\n", " ").strip()
                        hint += f"\n  Knowledge: {preview}..."
                    skill_hints += hint + "\n"
                desc = desc + skill_hints

            st = SubTask(
                description=desc,
                assigned_agent=AgentRole(st_data["assigned_agent"]),
                priority=st_data.get("priority", 1),
                depends_on=st_data.get("depends_on", []),
                skills=skill_ids,
            )
            sub_tasks.append(st)

        task = Task(
            user_input=thread.events[-1].content if thread.events else "",
            pipeline_type=pipeline_type,
            sub_tasks=sub_tasks,
        )
        thread.tasks.append(task)
        _set_task_state(
            thread,
            task,
            TaskStatus.QUEUED,
            EventType.ROUTING_DECISION,
            "Run created and queued after decomposition",
            live_monitor=self._live_monitor,
        )

        reasoning = fn_args.get("reasoning", "")
        skill_count = sum(len(st.skills) for st in sub_tasks)
        thread.add_event(
            EventType.ROUTING_DECISION,
            f"Pipeline: {pipeline_type.value} | Sub-tasks: {len(sub_tasks)} | Skills: {skill_count} | {reasoning}",
            agent_role=self.role,
        )

        summary_parts = [f"Task decomposed → {pipeline_type.value} pipeline:"]
        for i, st in enumerate(sub_tasks, 1):
            skill_info = f" [skills: {', '.join(st.skills)}]" if st.skills else ""
            summary_parts.append(f"  {i}. [{st.assigned_agent.value}] {st.description[:80]}{skill_info}")
        return "\n".join(summary_parts)

    # ── Complexity Classification ────────────────────────────────

    def _classify_complexity(self, user_input: str) -> str:
        """Classify query complexity: 'simple', 'moderate', or 'complex'.
        Determines how many agents to use and which pipeline."""
        text = user_input.strip()
        
        # Simple: greetings, yes/no, very short
        if _SIMPLE_PATTERNS.match(text) or len(text) < 20:
            return "simple"
        
        # Complex: deep research patterns, long queries, multiple sentences
        if _DEEP_RESEARCH_PATTERNS.search(text):
            return "complex"
        if len(text) > 200:
            return "complex"
        sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
        if len(sentences) >= 3:
            return "complex"
        
        return "moderate"

    # ── Main Entry Point ─────────────────────────────────────────

    async def route_and_execute(self, user_input: str, thread: Thread, live_monitor=None, forced_pipeline: PipelineType | None = None, user_id: str | None = None) -> str:
        """
        Main entry: user message → deep research detection → orchestrator → pipeline → result.
        forced_pipeline: If user selected a specific pipeline from UI, override auto-detection.
        """
        if live_monitor:
            self.set_live_monitor(live_monitor)

        thread.add_event(EventType.USER_MESSAGE, user_input)

        # ── Cache Check ──
        try:
            cached = await get_cached_response(user_input)
            if cached:
                self._emit("routing", f"⚡ Cache hit (güven: {cached.get('confidence', 0):.0%})")
                thread.add_event(
                    EventType.PIPELINE_COMPLETE,
                    f"Cache hit — returning cached response",
                    agent_role=self.role,
                )
                return cached["response"]
        except Exception:
            pass

        # ── Complexity Classification (Smart Routing) ──
        complexity = self._classify_complexity(user_input)
        
        # Simple queries: direct single-agent response, skip heavy pipelines
        if complexity == "simple" and forced_pipeline in (None, PipelineType.AUTO):
            self._emit("routing", "⚡ Basit sorgu — hızlı yanıt modu")
            thread.add_event(
                EventType.ROUTING_DECISION,
                f"Simple query detected — fast single-agent response",
                agent_role=self.role,
                complexity=complexity,
            )
            result = await self.execute(user_input, thread)
            try:
                await cache_response(user_input, result, confidence=0.7)
            except Exception:
                pass
            self._auto_save_memory(user_input, result, user_id=user_id)
            return result

        # ── Phase -1: Intent Analysis (5-Phase Pipeline: FAZ 1) ──
        intent_result = None
        try:
            intent_result = await self._analyze_intent(user_input, thread)

            # Confidence check — if too low, ask clarification
            if intent_result.get("clarification_needed") and intent_result.get("confidence", 1.0) < 0.4:
                question = intent_result.get("clarification_question", "")
                if question:
                    self._emit("pipeline", f"❓ Netleştirme gerekli (güven: {intent_result['confidence']:.0%})")
                    clarification_msg = f"🤔 Tam olarak ne istediğini anlamak istiyorum:\n\n{question}"
                    thread.add_event(
                        EventType.AGENT_RESPONSE,
                        clarification_msg,
                        agent_role=self.role,
                    )
                    return clarification_msg

            # Use enhanced prompt from intent analysis
            enhanced = intent_result.get("enhanced_prompt", user_input)
            if enhanced and enhanced != user_input and len(enhanced) > 5:
                self._emit("pipeline", f"✨ Prompt iyileştirildi: {enhanced[:120]}")
                user_input = enhanced

            # Override complexity from intent analysis
            if intent_result.get("complexity"):
                old_complexity = complexity
                complexity = intent_result["complexity"]
                self._emit("routing", f"📊 Karmaşıklık: {old_complexity} → {complexity} (intent analizi)")

            thread.add_event(
                EventType.ROUTING_DECISION,
                f"Intent: {intent_result.get('intent', '')[:100]} | "
                f"Confidence: {intent_result.get('confidence', 0):.0%} | "
                f"Pipeline: {intent_result.get('suggested_pipeline', 'auto')}",
                agent_role=self.role,
                intent_confidence=intent_result.get("confidence", 0),
            )
        except Exception:
            pass  # Never break main flow

        # ── Phase -0.5: Skill Pre-Discovery (FAZ 3 — runs early) ──
        pre_discovered_skills = []
        if intent_result and intent_result.get("required_skills"):
            try:
                pre_discovered_skills = await self._discover_skills_for_intent(intent_result)
            except Exception:
                pass

        # ── Auto-save user teachings/preferences ──
        try:
            from tools.teachability import is_teaching_message, save_teaching
            if is_teaching_message(user_input):
                save_teaching(
                    instruction=user_input,
                    trigger_text=user_input[:200],
                    category="preference",
                )
                thread.add_event(
                    EventType.TEACHING,
                    f"User teaching auto-saved: {user_input[:80]}",
                    agent_role=self.role,
                )
        except Exception:
            pass  # Never break main flow for teachability

        # ── Phase 0.5: Deterministic direct tool routing for explicit operational intents ──
        direct_intent = self._detect_direct_tool_intent(user_input)
        if direct_intent and forced_pipeline in (None, PipelineType.AUTO):
            tool_name, tool_args = direct_intent
            self._emit("routing", f"🎯 Deterministic tool route: {tool_name}")
            thread.add_event(
                EventType.ROUTING_DECISION,
                f"Deterministic route to tool: {tool_name}",
                agent_role=self.role,
            )
            result = await super().handle_tool_call(tool_name, tool_args, thread)

            direct_task = Task(
                user_input=user_input,
                pipeline_type=PipelineType.SEQUENTIAL,
                sub_tasks=[],
                final_result=str(result),
            )
            thread.tasks.append(direct_task)
            _set_task_state(
                thread,
                direct_task,
                TaskStatus.ROUTING,
                EventType.ROUTING_DECISION,
                f"Deterministic direct tool route selected: {tool_name}",
                live_monitor=live_monitor,
            )
            _set_task_state(
                thread,
                direct_task,
                TaskStatus.RUNNING,
                EventType.PIPELINE_START,
                f"Executing direct tool: {tool_name}",
                live_monitor=live_monitor,
            )
            _set_task_state(
                thread,
                direct_task,
                TaskStatus.SYNTHESIZING,
                EventType.PIPELINE_STEP,
                f"Direct tool response received: {tool_name}",
                live_monitor=live_monitor,
            )
            _set_task_state(
                thread,
                direct_task,
                TaskStatus.COMPLETED,
                EventType.PIPELINE_COMPLETE,
                f"Direct tool completed: {tool_name}",
                live_monitor=live_monitor,
            )
            return str(result)

        # ── Phase 0: Determine pipeline mode ──
        # Check for idea-to-project first
        is_idea_project = (
            forced_pipeline == PipelineType.IDEA_TO_PROJECT
            or (forced_pipeline in (None, PipelineType.AUTO) and self._detect_idea_to_project(user_input))
        )

        if is_idea_project:
            self._emit("routing", "🚀 Idea-to-Project modu algılandı")
            thread.add_event(
                EventType.ROUTING_DECISION,
                "Idea-to-Project pipeline triggered",
                agent_role=self.role,
            )

            result = await self._handle_idea_to_project({"idea": user_input}, thread)

            # Create a Task so ExportButtons can find the result
            idea_task = Task(
                user_input=user_input,
                pipeline_type=PipelineType.IDEA_TO_PROJECT,
                sub_tasks=[],
                final_result=result,
            )
            thread.tasks.append(idea_task)
            _set_task_state(
                thread,
                idea_task,
                TaskStatus.ROUTING,
                EventType.ROUTING_DECISION,
                "Idea-to-project pipeline selected",
                live_monitor=live_monitor,
            )
            _set_task_state(
                thread,
                idea_task,
                TaskStatus.RUNNING,
                EventType.PIPELINE_START,
                "Idea-to-project execution started",
                live_monitor=live_monitor,
            )
            _set_task_state(
                thread,
                idea_task,
                TaskStatus.SYNTHESIZING,
                EventType.PIPELINE_STEP,
                "Idea-to-project outputs are being synthesized",
                live_monitor=live_monitor,
            )
            _set_task_state(
                thread,
                idea_task,
                TaskStatus.COMPLETED,
                EventType.PIPELINE_COMPLETE,
                "Idea-to-project pipeline completed",
                live_monitor=live_monitor,
            )

            self._auto_save_memory(user_input, result, user_id=user_id)
            return result

        # Check for presentation generation
        is_presentation = (
            forced_pipeline in (None, PipelineType.AUTO)
            and self._detect_presentation(user_input)
        )

        # Check for MINI/MIDI/MAXI mode selection (follow-up to presentation analysis)
        mode_match = _PRESENTATION_MODE_PATTERNS.match(user_input.strip())
        is_mode_selection = bool(mode_match)

        # If user selected a mode, check if there's a pending presentation in thread
        if is_mode_selection:
            pending_topic = None
            for ev in reversed(thread.events):
                if ev.event_type == EventType.ROUTING_DECISION and "Presentation analysis" in ev.content:
                    # Extract topic from metadata
                    pending_topic = ev.metadata.get("topic", "")
                    break
                if ev.event_type == EventType.AGENT_RESPONSE and "Sunum Modu Seçenekleri" in ev.content:
                    # Find the original user message before analysis
                    for ev2 in thread.events:
                        if ev2.event_type == EventType.USER_MESSAGE and self._detect_presentation(ev2.content):
                            pending_topic = ev2.content
                            break
                    break

            if pending_topic:
                selected_mode = mode_match.group(1).lower()
                custom_slides = int(mode_match.group(2)) if mode_match.group(2) else None

                self._emit("routing", f"🎨 {selected_mode.upper()} modu seçildi — sunum üretiliyor")

                lang = "tr" if re.search(r"[çğıöşüÇĞİÖŞÜ]", pending_topic) else "en"

                fn_args = {
                    "topic": pending_topic,
                    "mode": selected_mode,
                    "language": lang,
                    "theme": "corporate",
                }
                if custom_slides:
                    fn_args["slide_count"] = custom_slides

                result = await self._handle_generate_presentation(fn_args, thread)

                pres_task = Task(
                    user_input=f"{pending_topic} [{selected_mode.upper()}]",
                    pipeline_type=PipelineType.DEEP_RESEARCH,
                    sub_tasks=[],
                    final_result=result,
                )
                thread.tasks.append(pres_task)
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.ROUTING,
                    EventType.ROUTING_DECISION,
                    f"Presentation route selected (mode={selected_mode})",
                    live_monitor=live_monitor,
                )
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.RUNNING,
                    EventType.PIPELINE_START,
                    "Presentation generation started",
                    live_monitor=live_monitor,
                )
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.SYNTHESIZING,
                    EventType.PIPELINE_STEP,
                    "Presentation artifacts are being finalized",
                    live_monitor=live_monitor,
                )
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.COMPLETED,
                    EventType.PIPELINE_COMPLETE,
                    "Presentation generation completed",
                    live_monitor=live_monitor,
                )

                self._auto_save_memory(pending_topic, result, user_id=user_id)
                return result

        if is_presentation:
            lang = "tr" if re.search(r"[çğıöşüÇĞİÖŞÜ]", user_input) else "en"

            # Check if user already specified slide count — skip analysis, go direct
            slide_count_match = re.search(r"(\d+)\s*(?:slayt|slide|sayfa)", user_input, re.IGNORECASE)
            if slide_count_match:
                requested_slides = int(slide_count_match.group(1))
                # Auto-select mode based on requested slide count
                if requested_slides <= 7:
                    auto_mode = "mini"
                elif requested_slides <= 15:
                    auto_mode = "midi"
                else:
                    auto_mode = "maxi"

                self._emit("routing", f"🎨 {requested_slides} slaytlık sunum — {auto_mode.upper()} modunda direkt üretiliyor")

                fn_args = {
                    "topic": user_input,
                    "mode": auto_mode,
                    "slide_count": requested_slides,
                    "language": lang,
                    "theme": "corporate",
                }

                result = await self._handle_generate_presentation(fn_args, thread)

                pres_task = Task(
                    user_input=f"{user_input} [{auto_mode.upper()} {requested_slides}]",
                    pipeline_type=PipelineType.DEEP_RESEARCH,
                    sub_tasks=[],
                    final_result=result,
                )
                thread.tasks.append(pres_task)
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.ROUTING,
                    EventType.ROUTING_DECISION,
                    f"Presentation route selected (mode={auto_mode}, slides={requested_slides})",
                    live_monitor=live_monitor,
                )
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.RUNNING,
                    EventType.PIPELINE_START,
                    "Presentation generation started",
                    live_monitor=live_monitor,
                )
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.SYNTHESIZING,
                    EventType.PIPELINE_STEP,
                    "Presentation artifacts are being finalized",
                    live_monitor=live_monitor,
                )
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.COMPLETED,
                    EventType.PIPELINE_COMPLETE,
                    "Presentation generation completed",
                    live_monitor=live_monitor,
                )

                self._auto_save_memory(user_input, result, user_id=user_id)
                return result

            # No slide count specified — show MINI/MIDI/MAXI options
            self._emit("routing", "🎨 Sunum oluşturma modu algılandı — konu analiz ediliyor")
            thread.add_event(
                EventType.ROUTING_DECISION,
                "Presentation analysis triggered",
                agent_role=self.role,
                topic=user_input,
            )

            # Step 1: Analyze topic and present MINI/MIDI/MAXI options
            from tools.presentation_service import (
                analyze_topic_for_presentation, format_analysis_response,
            )

            self._emit("pipeline", "🔍 Konu analiz ediliyor — MINI/MIDI/MAXI seçenekleri hazırlanıyor...")

            try:
                lang = "tr" if re.search(r"[çğıöşüÇĞİÖŞÜ]", user_input) else "en"
                analysis = await analyze_topic_for_presentation(user_input, language=lang)
                analysis_text = format_analysis_response(analysis)

                # Store analysis event so we can find it later
                thread.add_event(
                    EventType.AGENT_RESPONSE,
                    analysis_text,
                    agent_role=self.role,
                )

                return analysis_text

            except Exception as e:
                print(f"[Orchestrator] Presentation analysis failed: {e}, falling back to MIDI")
                # Fallback: skip analysis, go directly to MIDI mode
                lang = "tr" if re.search(r"[çğıöşüÇĞİÖŞÜ]", user_input) else "en"
                result = await self._handle_generate_presentation(
                    {"topic": user_input, "mode": "midi", "language": lang},
                    thread,
                )

                pres_task = Task(
                    user_input=user_input,
                    pipeline_type=PipelineType.DEEP_RESEARCH,
                    sub_tasks=[],
                    final_result=result,
                )
                thread.tasks.append(pres_task)
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.ROUTING,
                    EventType.ROUTING_DECISION,
                    "Presentation fallback route selected (mode=midi)",
                    live_monitor=live_monitor,
                )
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.RUNNING,
                    EventType.PIPELINE_START,
                    "Presentation generation started",
                    live_monitor=live_monitor,
                )
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.SYNTHESIZING,
                    EventType.PIPELINE_STEP,
                    "Presentation artifacts are being finalized",
                    live_monitor=live_monitor,
                )
                _set_task_state(
                    thread,
                    pres_task,
                    TaskStatus.COMPLETED,
                    EventType.PIPELINE_COMPLETE,
                    "Presentation generation completed",
                    live_monitor=live_monitor,
                )

                self._auto_save_memory(user_input, result, user_id=user_id)
                return result

        # User forced deep research from UI, or auto-detected
        is_deep = (
            forced_pipeline == PipelineType.DEEP_RESEARCH
            or (forced_pipeline in (None, PipelineType.AUTO) and self._detect_deep_research(user_input))
        )

        # User forced parallel from UI
        is_forced_parallel = forced_pipeline == PipelineType.PARALLEL

        # ── Brainstorm Pipeline ──
        is_brainstorm = (
            forced_pipeline == PipelineType.BRAINSTORM
            or (forced_pipeline in (None, PipelineType.AUTO) and self._detect_brainstorm(user_input))
        )

        if is_brainstorm:
            self._emit("routing", "🧠 Beyin Fırtınası modu — agent'lar tartışacak")

            sub_tasks = [
                SubTask(
                    description=f"Brainstorm perspective on: {user_input}",
                    assigned_agent=role,
                    priority=1,
                )
                for role in [AgentRole.THINKER, AgentRole.RESEARCHER, AgentRole.REASONER, AgentRole.SPEED, AgentRole.CRITIC]
            ]

            task = Task(
                user_input=user_input,
                pipeline_type=PipelineType.BRAINSTORM,
                sub_tasks=sub_tasks,
            )
            thread.tasks.append(task)
            _set_task_state(
                thread,
                task,
                TaskStatus.QUEUED,
                EventType.ROUTING_DECISION,
                "Run created and queued for brainstorm pipeline",
                live_monitor=live_monitor,
            )

            thread.add_event(
                EventType.ROUTING_DECISION,
                f"Brainstorm: 3-round debate with 4 agents",
                agent_role=self.role,
            )

            from pipelines.engine import PipelineEngine
            engine = PipelineEngine()
            if live_monitor:
                engine.set_live_monitor(live_monitor)

            result = await engine.execute(task, thread)

            if live_monitor and live_monitor.should_stop():
                return "[Stopped] Kullanıcı tarafından durduruldu."

            # Synthesize with orchestrator for final polish
            if live_monitor:
                live_monitor.emit("routing", "orchestrator", "Beyin fırtınası sonuçları sentezleniyor...")

            # Use SynthesizerAgent for structured synthesis
            try:
                from agents.synthesizer import SynthesizerAgent
                synthesizer = SynthesizerAgent()
                if live_monitor:
                    synthesizer.set_live_monitor(live_monitor)
                    live_monitor.emit("routing", "orchestrator", "📊 Sentez Agent çalışıyor — güven skorları hesaplanıyor...")
                
                # Parse agent results from brainstorm output
                agent_results = {}
                for st in task.sub_tasks:
                    if st.result:
                        agent_results[st.assigned_agent.value] = st.result
                
                final, conf_footer = await synthesizer.synthesize(agent_results, user_input, thread)
            except Exception:
                # Fallback to old synthesis
                synth_input = (
                    f"You are synthesizing a multi-round brainstorm debate between 4 specialist agents.\n\n"
                    f"DEBATE RESULTS:\n{result}\n\n"
                    f"ORIGINAL TOPIC: {user_input}\n\n"
                    f"Create a comprehensive final response that:\n"
                    f"1. Highlights the strongest arguments from each perspective\n"
                    f"2. Notes key agreements and disagreements\n"
                    f"3. Provides a balanced, actionable conclusion\n"
                    f"Respond in the same language as the user's request."
                )
                final = await self.execute(synth_input, thread)
                conf_footer = None
            task.final_result = final
            task.confidence_footer = conf_footer
            try:
                from tools.confidence import score_confidence
                avg_conf = sum(
                    score_confidence(r, role, "general").get("confidence_score", 0.5)
                    for role, r in agent_results.items()
                ) / max(len(agent_results), 1)
                await cache_response(user_input, final, confidence=avg_conf)
            except Exception:
                pass
            # Quality Gate (Faz 5.5)
            try:
                final, qg_passed = await self._quality_gate(final, user_input, thread)
                if not qg_passed and live_monitor:
                    live_monitor.emit("pipeline", "orchestrator", "⚠️ Quality Gate: refinement önerildi")
            except Exception:
                pass
            self._auto_save_memory(user_input, final, user_id=user_id)
            return final

        if is_deep:
            self._emit("routing", "🔬 Deep Research modu algılandı — tüm agent'lar paralel çalışacak")

            # Build parallel tasks WITHOUT waiting for LLM decision
            deep_tasks = self._build_deep_research_tasks(user_input)
            sub_tasks = [
                SubTask(
                    description=t["description"],
                    assigned_agent=AgentRole(t["assigned_agent"]),
                    priority=t["priority"],
                )
                for t in deep_tasks
            ]

            task = Task(
                user_input=user_input,
                pipeline_type=PipelineType.DEEP_RESEARCH,
                sub_tasks=sub_tasks,
            )
            thread.tasks.append(task)

            thread.add_event(
                EventType.ROUTING_DECISION,
                f"Deep Research: parallel pipeline with {len(sub_tasks)} agents",
                agent_role=self.role,
            )

            if live_monitor:
                live_monitor.emit(
                    "pipeline",
                    "orchestrator",
                    f"🔬 Deep Research — {len(sub_tasks)} agent paralel çalışıyor",
                )

            from pipelines.engine import PipelineEngine
            engine = PipelineEngine()
            if live_monitor:
                engine.set_live_monitor(live_monitor)

            result = await engine.execute(task, thread)

            if live_monitor and live_monitor.should_stop():
                return "[Stopped] Kullanıcı tarafından durduruldu."

            # Synthesize with orchestrator
            if live_monitor:
                live_monitor.emit("routing", "orchestrator", "Sonuçlar sentezleniyor...")

            # Use SynthesizerAgent for structured synthesis with confidence
            try:
                from agents.synthesizer import SynthesizerAgent
                synthesizer = SynthesizerAgent()
                if live_monitor:
                    synthesizer.set_live_monitor(live_monitor)
                    live_monitor.emit("routing", "orchestrator", "📊 Sentez Agent çalışıyor — güven skorları hesaplanıyor...")
                
                agent_results = {}
                for st in task.sub_tasks:
                    if st.result:
                        agent_results[st.assigned_agent.value] = st.result
                
                final, conf_footer = await synthesizer.synthesize(agent_results, user_input, thread)
            except Exception:
                # Fallback to old synthesis
                synth_input = (
                    f"You are synthesizing results from {len(task.sub_tasks)} specialist agents who worked in parallel.\n\n"
                    f"AGENT RESULTS:\n{result}\n\n"
                    f"ORIGINAL USER REQUEST: {user_input}\n\n"
                    f"Create a comprehensive, well-structured final response that:\n"
                    f"1. Integrates insights from ALL agents\n"
                    f"2. Resolves any contradictions between agents\n"
                    f"3. Cites sources where available\n"
                    f"4. Provides clear actionable conclusions\n"
                    f"Respond in the same language as the user's request."
                )
                final = await self.execute(synth_input, thread)
                conf_footer = None
            task.final_result = final
            task.confidence_footer = conf_footer
            try:
                from tools.confidence import score_confidence
                avg_conf = sum(
                    score_confidence(r, role, "general").get("confidence_score", 0.5)
                    for role, r in agent_results.items()
                ) / max(len(agent_results), 1)
                await cache_response(user_input, final, confidence=avg_conf)
            except Exception:
                pass
            # Quality Gate (Faz 5.5)
            try:
                final, qg_passed = await self._quality_gate(final, user_input, thread)
                if not qg_passed and live_monitor:
                    live_monitor.emit("pipeline", "orchestrator", "⚠️ Quality Gate: refinement önerildi")
            except Exception:
                pass
            self._auto_save_memory(user_input, final, user_id=user_id)
            return final

        # ── Phase 1: Let orchestrator LLM decide (non-deep queries) ──
        # Complexity-based routing hint for LLM
        complexity_hint = {
            "simple": "Bu basit bir sorgu — tek agent yeterli.",
            "moderate": "Bu orta seviye bir sorgu — 2-3 agent paralel çalışmalı.",
            "complex": "Bu karmaşık bir sorgu — 3-5 agent derinlemesine analiz yapmalı.",
        }.get(complexity, "")
        
        if complexity_hint:
            self._emit("routing", f"📊 Karmaşıklık: {complexity} — {complexity_hint[:50]}")
        
        decision = await self.execute(user_input, thread)

        if live_monitor and live_monitor.should_stop():
            return "[Stopped] Kullanıcı tarafından durduruldu."

        # Check if it was a direct response
        last_events = thread.events[-5:]
        for ev in reversed(last_events):
            if ev.event_type == EventType.TOOL_CALL and "direct_response" in ev.content:
                self._auto_save_memory(user_input, decision, user_id=user_id)
                return decision

        # ── Phase 2: Run pipeline if tasks were created ──
        if thread.tasks:
            current_task = thread.tasks[-1]
            if current_task.sub_tasks:
                # Auto-upgrade: if LLM created only 1 sub-task for a non-trivial query,
                # or user forced parallel from UI — upgrade to parallel multi-agent
                if (
                    len(current_task.sub_tasks) == 1
                    and complexity != "simple"
                    and (
                        is_forced_parallel
                        or (len(user_input.strip()) > 30 and current_task.pipeline_type != PipelineType.PARALLEL)
                    )
                ):
                    self._emit("routing", "Auto-upgrade: tek agent → parallel multi-agent")
                    original_desc = current_task.sub_tasks[0].description
                    current_task.sub_tasks = [
                        SubTask(
                            description=original_desc,
                            assigned_agent=current_task.sub_tasks[0].assigned_agent,
                            priority=1,
                        ),
                    ]
                    # Add complementary agents
                    existing_agent = current_task.sub_tasks[0].assigned_agent.value
                    # Moderate: 2-3 agents total, Complex: 4-5 agents total
                    if complexity == "moderate":
                        complement = {
                            "researcher": ["thinker"],
                            "thinker": ["researcher"],
                            "reasoner": ["thinker"],
                            "speed": ["researcher"],
                            "critic": ["thinker"],
                        }
                        self._emit("routing", f"📊 Orta seviye → 2 agent paralel")
                    else:  # complex
                        complement = {
                            "researcher": ["thinker", "reasoner", "critic"],
                            "thinker": ["researcher", "reasoner", "critic"],
                            "reasoner": ["thinker", "researcher", "speed"],
                            "speed": ["thinker", "researcher", "reasoner"],
                            "critic": ["thinker", "researcher", "reasoner"],
                        }
                        self._emit("routing", f"📊 Karmaşık seviye → 4-5 agent paralel")
                    for agent_name in complement.get(existing_agent, ["thinker", "researcher"]):
                        current_task.sub_tasks.append(SubTask(
                            description=f"Support analysis for: {user_input}",
                            assigned_agent=AgentRole(agent_name),
                            priority=2,
                        ))
                    current_task.pipeline_type = PipelineType.PARALLEL

                # Multiparallel: 2+ sub-tasks always run at the same time
                if len(current_task.sub_tasks) >= 2 and current_task.pipeline_type == PipelineType.SEQUENTIAL:
                    current_task.pipeline_type = PipelineType.PARALLEL
                    self._emit("routing", "Multiparallel: tüm alt görevler aynı anda çalışacak")

                if live_monitor:
                    live_monitor.emit(
                        "pipeline",
                        "orchestrator",
                        f"{current_task.pipeline_type.value} pipeline — "
                        f"{len(current_task.sub_tasks)} alt görev (aynı anda)",
                    )

                from pipelines.engine import PipelineEngine
                engine = PipelineEngine()
                if live_monitor:
                    engine.set_live_monitor(live_monitor)

                result = await engine.execute(current_task, thread)

                if live_monitor and live_monitor.should_stop():
                    return "[Stopped] Kullanıcı tarafından durduruldu."

                # Synthesize
                if live_monitor:
                    live_monitor.emit("routing", "orchestrator", "Sonuçlar sentezleniyor...")

                # Use SynthesizerAgent for structured synthesis
                try:
                    from agents.synthesizer import SynthesizerAgent
                    synthesizer = SynthesizerAgent()
                    if live_monitor:
                        synthesizer.set_live_monitor(live_monitor)
                        live_monitor.emit("routing", "orchestrator", "📊 Sentez Agent çalışıyor — güven skorları hesaplanıyor...")
                    
                    agent_results = {}
                    for st in current_task.sub_tasks:
                        if st.result:
                            agent_results[st.assigned_agent.value] = st.result
                    
                    final, conf_footer = await synthesizer.synthesize(agent_results, user_input, thread)
                except Exception:
                    # Fallback to old synthesis
                    synth_input = (
                        f"The specialists have completed their work. Here are the results:\n\n"
                        f"{result}\n\n"
                        f"Original user request: {user_input}\n\n"
                        f"Synthesize a clear, comprehensive final response in the user's language."
                    )
                    final = await self.execute(synth_input, thread)
                    conf_footer = None
                current_task.final_result = final
                current_task.confidence_footer = conf_footer
                try:
                    from tools.confidence import score_confidence
                    avg_conf = sum(
                        score_confidence(r, role, "general").get("confidence_score", 0.5)
                        for role, r in agent_results.items()
                    ) / max(len(agent_results), 1)
                    await cache_response(user_input, final, confidence=avg_conf)
                except Exception:
                    pass
                # Quality Gate (Faz 5.5)
                try:
                    final, qg_passed = await self._quality_gate(final, user_input, thread)
                    if not qg_passed and live_monitor:
                        live_monitor.emit("pipeline", "orchestrator", "⚠️ Quality Gate: refinement önerildi")
                except Exception:
                    pass
                self._auto_save_memory(user_input, final, user_id=user_id)
                return final

        # Cache direct orchestrator responses
        try:
            await cache_response(user_input, decision, confidence=0.5)
        except Exception:
            pass
        self._auto_save_memory(user_input, decision, user_id=user_id)
        return decision

    # ── FAZ 1: Intent Analysis ─────────────────────────────────────

    async def _analyze_intent(self, user_input: str, thread: Thread) -> dict:
        """
        Phase 1 of 5-Phase Pipeline: Intent Analysis.
        Returns structured intent with confidence score.
        If confidence < 0.7, includes clarification question.
        """
        # Trivial inputs — skip LLM call
        if len(user_input.strip()) < 10 or _SIMPLE_PATTERNS.match(user_input.strip()):
            return {
                "intent": user_input,
                "confidence": 1.0,
                "complexity": "simple",
                "suggested_pipeline": "direct",
                "required_skills": [],
                "agents_needed": [],
                "clarification_needed": False,
                "clarification_question": None,
                "enhanced_prompt": user_input,
            }

        # Recall past intent patterns from memory
        memory_hint = ""
        try:
            from tools.memory import recall_memory, format_recall_results
            memories = await recall_memory(query=f"intent pattern: {user_input[:100]}", max_results=2)
            if memories:
                memory_hint = (
                    "\n\nPAST INTENT PATTERNS (from memory):\n"
                    + format_recall_results(memories)
                )
        except Exception:
            pass

        intent_prompt = (
            "You are an Intent Analysis specialist for a multi-agent AI system.\n"
            "Analyze the user's message and extract structured intent.\n\n"
            "RULES:\n"
            "- Detect the TRUE goal behind the message, not just surface words.\n"
            "- Turkish users write informally (ALL CAPS, no punctuation, slang) — this is NORMAL, not ambiguous.\n"
            "- ONLY ask clarification if the message is truly incomprehensible or could mean completely different things.\n"
            "- Default confidence should be 0.7+ for any message with a clear topic, even if informal.\n"
            "- If the user mentions the app/system they're using, that IS the context — don't ask what they mean.\n"
            "- Keep the same language as the user (Turkish stays Turkish).\n"
            "- Enhanced prompt should be clearer and more actionable than the original.\n"
            f"{memory_hint}\n\n"
            f"USER MESSAGE:\n{user_input}\n\n"
            "Respond ONLY with valid JSON (no markdown, no explanation):\n"
            "{\n"
            '  "intent": "clear one-line description of what user wants",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "complexity": "simple|moderate|complex",\n'
            '  "suggested_pipeline": "direct|parallel|deep_research|brainstorm|idea_to_project",\n'
            '  "required_skills": ["skill-id-1", "skill-id-2"],\n'
            '  "agents_needed": ["researcher", "thinker", "reasoner", "speed", "critic"],\n'
            '  "clarification_needed": true/false,\n'
            '  "clarification_question": "question to ask user or null",\n'
            '  "enhanced_prompt": "improved version of user message"\n'
            "}"
        )

        messages = [
            {"role": "system", "content": "You are a precise intent analysis engine. Output ONLY valid JSON."},
            {"role": "user", "content": intent_prompt},
        ]

        try:
            response = await self.call_llm(messages)
            content = response.get("content", "").strip()
            if not content:
                return self._fallback_intent(user_input)

            # Strip markdown code fences if present
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

            result = json.loads(content)

            # Validate required fields
            required = ["intent", "confidence", "complexity", "suggested_pipeline"]
            if not all(k in result for k in required):
                return self._fallback_intent(user_input)

            # Clamp confidence
            result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

            # Ensure enhanced_prompt exists
            if not result.get("enhanced_prompt"):
                result["enhanced_prompt"] = user_input

            self._emit(
                "pipeline",
                f"🎯 Intent: {result['intent'][:80]} (güven: {result['confidence']:.0%}, "
                f"karmaşıklık: {result['complexity']})",
            )

            return result

        except (json.JSONDecodeError, Exception):
            return self._fallback_intent(user_input)

    def _fallback_intent(self, user_input: str) -> dict:
        """Fallback when LLM intent analysis fails — use rule-based classification."""
        complexity = self._classify_complexity(user_input)
        pipeline_map = {"simple": "direct", "moderate": "parallel", "complex": "deep_research"}
        return {
            "intent": user_input[:120],
            "confidence": 0.6,
            "complexity": complexity,
            "suggested_pipeline": pipeline_map.get(complexity, "parallel"),
            "required_skills": [],
            "agents_needed": [],
            "clarification_needed": False,
            "clarification_question": None,
            "enhanced_prompt": user_input,
        }

    # ── FAZ 3: Skill Pre-Discovery ──────────────────────────────────

    async def _discover_skills_for_intent(self, intent_result: dict) -> list[dict]:
        """
        Phase 3: Discover existing skills or flag missing ones for creation.
        Returns list of found skills with metadata.
        """
        required = intent_result.get("required_skills", [])
        if not required:
            return []

        found_skills = []
        missing_skills = []

        try:
            from tools.dynamic_skills import search_skills
            for skill_id in required[:5]:  # Max 5 skill lookups
                results = search_skills(query=skill_id, max_results=1)
                if results:
                    found_skills.append(results[0])
                else:
                    missing_skills.append(skill_id)
        except Exception:
            missing_skills = list(required[:5])

        if missing_skills:
            self._emit(
                "pipeline",
                f"⚠️ Eksik skill'ler: {', '.join(missing_skills)} — görev sırasında oluşturulacak",
            )

        if found_skills:
            self._emit(
                "pipeline",
                f"✅ {len(found_skills)} skill bulundu: {', '.join(s.get('id', '?') for s in found_skills)}",
            )

        return found_skills

    # ── FAZ 5.5: Quality Gate ────────────────────────────────────────

    async def _quality_gate(self, result: str, user_input: str, thread: Thread) -> tuple[str, bool]:
        """
        Phase 5.5: Quality Gate — Critic reviews the final synthesis using
        rubric-based evaluation from agentic_eval when available.
        Returns (result, passed). If quality < 0.6, returns (result, False) for refinement.
        """
        if not result or len(result.strip()) < 100:
            return result, True  # Too short to review

        try:
            from agents.critic import CriticAgent
            critic = CriticAgent()
            if hasattr(self, '_live_monitor') and self._live_monitor:
                critic.set_live_monitor(self._live_monitor)

            # Try rubric-based evaluation from agentic_eval
            try:
                from tools.agentic_eval import (
                    build_rubric_eval_prompt,
                    compute_weighted_score,
                    detect_eval_task_type,
                    get_rubric,
                )

                task_type = detect_eval_task_type(user_input)
                rubric = get_rubric(task_type)
                review_prompt = build_rubric_eval_prompt(result, user_input, rubric)
            except Exception:
                # Fallback to simple prompt
                review_prompt = (
                    f"QUALITY REVIEW — rate this response.\n\n"
                    f"USER REQUEST: {user_input[:300]}\n\n"
                    f"RESPONSE TO REVIEW:\n{result[:3000]}\n\n"
                    f"Rate quality 0.0-1.0. Output ONLY valid JSON:\n"
                    f'{{"quality": 0.0-1.0, "issues": ["issue1"], "pass": true/false}}'
                )
                rubric = None

            review_result = await critic.execute(review_prompt, thread)

            # Parse quality score
            try:
                json_match = re.search(r'\{[^}]+\}', review_result)
                if json_match:
                    review_data = json.loads(json_match.group())

                    # Compute weighted score from rubric dimensions if available
                    if rubric and review_data.get("dimensions"):
                        quality = compute_weighted_score(review_data["dimensions"], rubric)
                        passed = quality >= 0.6 and review_data.get("approved", quality >= 0.8)
                    else:
                        quality = float(review_data.get("quality", review_data.get("overall_score", 0.7)))
                        passed = review_data.get("pass", review_data.get("approved", True))

                    self._emit(
                        "pipeline",
                        f"🎯 Quality Gate: {quality:.0%} {'✅ PASS' if passed else '⚠️ NEEDS REFINEMENT'}",
                    )

                    thread.add_event(
                        EventType.EVALUATION,
                        f"Quality Gate: {quality:.0%}, passed={passed}",
                        agent_role=AgentRole.CRITIC,
                        quality=quality,
                    )

                    return result, passed
            except (json.JSONDecodeError, ValueError):
                pass

        except Exception:
            pass

        return result, True  # Default: pass if review fails

    # ── Prompt Enhancement (simplified, used within intent analysis) ──

    async def _enhance_prompt(self, user_input: str, thread: Thread) -> str:
        """
        Simplified prompt enhancer — delegates to intent analysis.
        Kept for backward compatibility with route_and_execute flow.
        """
        if len(user_input.strip()) < 10 or _SIMPLE_PATTERNS.match(user_input.strip()):
            return user_input

        try:
            intent = await self._analyze_intent(user_input, thread)
            enhanced = intent.get("enhanced_prompt", user_input)
            if enhanced and enhanced != user_input and len(enhanced) > 5:
                self._emit("pipeline", f"✨ Prompt iyileştirildi: {enhanced[:120]}")
                return enhanced
        except Exception:
            pass

        return user_input

    # ── Auto Memory Save ─────────────────────────────────────────────

    def _auto_save_memory(self, user_input: str, result: str, user_id: str | None = None) -> None:
        """Save task completion to learned memory."""
        tags: list[str] = []
        keywords = ["search", "code", "analyze", "math", "translate", "summarize",
                    "research", "compare", "explain", "calculate", "predict"]
        input_lower = user_input.lower()
        for kw in keywords:
            if kw in input_lower:
                tags.append(kw)
        if not tags:
            tags = ["task-completion"]

        try:
            from tools.memory import save_memory
            summary = (
                f"Task: {user_input[:200]}\n"
                f"Result: {result[:300]}"
            )
            save_memory(
                content=summary,
                category="solution",
                tags=tags + ([f"user:{user_id}"] if user_id else []),
                source_agent="orchestrator",
            )
        except Exception:
            pass

        # Periodic skill hygiene check (every ~10 tasks)
        try:
            import random
            if random.random() < 0.1:
                from tools.skill_hygiene import run_hygiene_check
                run_hygiene_check(dry_run=False)
        except Exception:
            pass

        # Post-task autonomous chat
        try:
            from backend.routes.messaging import trigger_post_task_auto_chat
            trigger_post_task_auto_chat(
                task_summary=user_input[:120],
                participating_agents=None,
                user_id=user_id or "__system__",
            )
        except Exception:
            pass
