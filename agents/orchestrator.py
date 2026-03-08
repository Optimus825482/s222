"""
Qwen3 Next 80B — Orchestrator Agent.
The brain: task analysis, decomposition, routing, synthesis.
Deep Research mode: auto-detects complex queries and fans out to ALL agents in parallel.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

from agents.base import BaseAgent
from core.models import (
    AgentRole, EventType, PipelineType, SubTask, Task, TaskStatus, Thread,
)
from core.events import build_orchestrator_context
from tools.registry import ORCHESTRATOR_TOOLS
from tools.cache import get_cached_response, cache_response, cache_stats
from tools.circuit_breaker import get_circuit_breaker

# Keywords that trigger brainstorm mode (Turkish + English)
_BRAINSTORM_PATTERNS = re.compile(
    r"(beyin fırtınası|brainstorm|tartış|debate|discuss|fikir alışverişi|"
    r"farklı bakış|different perspective|pros?\s+cons|artı\s+eksi|"
    r"ne dersiniz|ne düşünüyorsunuz|görüş|opinion|"
    r"avantaj.*dezavantaj|lehte.*aleyhte|for\s+and\s+against)",
    re.IGNORECASE,
)

# Keywords that trigger deep research mode (Turkish + English)
_DEEP_RESEARCH_PATTERNS = re.compile(
    r"(araştır|research|analiz|analy[sz]e|incele|investigate|karşılaştır|compare|"
    r"detaylı|detailed|kapsamlı|comprehensive|derinlemesine|in-depth|deep\s*dive|"
    r"rapor|report|değerlendir|evaluate|assess|review|examine|explore|"
    r"nedir|what\s+is|nasıl|how\s+does|explain|açıkla|özetle|summarize|"
    r"avantaj|dezavantaj|pros?\s+and\s+cons|fark|difference|versus|vs\.?|"
    r"strateji|strategy|planlama|planning|mimari|architect|tasarım|design|"
    r"güvenlik|security|performans|performance|optimiz|benchmark|"
    r"trend|piyasa|market|sektör|industry|teknoloji|technology|"
    r"en\s+iyi|best\s+practice|öneri|recommend|suggest)",
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

_LIST_TEACHINGS_PATTERNS = re.compile(
    r"(list\s+teachings|teachings\s+list|öğretileri\s+listele|tercihleri\s+listele)",
    re.IGNORECASE,
)


class OrchestratorAgent(BaseAgent):
    role = AgentRole.ORCHESTRATOR
    model_key = "orchestrator"

    def system_prompt(self) -> str:
        return (
            "You are the Orchestrator of a multi-agent deep research system. "
            "You coordinate 5 specialist agents that work IN PARALLEL.\n\n"
            "AGENTS (delegate via decompose_task — these are NOT tools):\n"
            "- researcher (GLM 4.7): Web search, current info, data gathering, fact-checking\n"
            "- thinker (MiniMax M2.1): Deep analysis, complex reasoning, planning, architecture\n"
            "- reasoner (Nemotron 3 Nano): Math, logic, chain-of-thought, verification\n"
            "- speed (Step 3.5 Flash): Quick answers, code generation, formatting\n"
            "- critic (DeepSeek): Code review, fact-checking, quality assurance, verification — use as the final quality gate\n\n"
            "CRITICAL RULES:\n"
            "1. For ANY research, analysis, or complex question: ALWAYS use decompose_task with "
            "pipeline_type='parallel' and assign MULTIPLE agents (minimum 3).\n"
            "2. NEVER send a complex task to just ONE agent. Fan out to ALL relevant agents.\n"
            "3. Only use direct_response for greetings, simple yes/no, or trivial questions.\n"
            "4. Do NOT call agent names directly as tools. Use decompose_task.\n\n"
            "TOOL DECISION POLICY (DETERMINISTIC):\n"
            "- If user asks memory overview/stats: use list_memories or memory_stats.\n"
            "- If user asks what docs are available in knowledge base: use rag_list_documents first, then rag_query if needed.\n"
            "- If user asks learned preferences/teachings: use list_teachings.\n"
            "- For deep/complex analysis: use decompose_task with parallel specialists.\n"
            "- For trivial greeting/acknowledgement: use direct_response.\n\n"
            "STANDARD DECOMPOSITION for research/analysis tasks:\n"
            "- researcher: Search web, gather current data and sources\n"
            "- thinker: Deep analysis, pros/cons, strategic evaluation\n"
            "- reasoner: Verify facts, check logic, find inconsistencies\n"
            "- speed: Format output, generate code/tables if needed\n"
            "- critic: Review quality, find weaknesses, suggest improvements\n\n"
            "YOUR TOOLS:\n"
            "- decompose_task: Break work into sub-tasks and assign to agents (ALWAYS prefer parallel)\n"
            "- spawn_subagent: Create and run a ONE-OFF specialist on ANY topic (custom role + optional skills). Use when the fixed 4 agents are not the right fit or you need a domain expert (crypto, legal, etc.). You can create a skill first with research_create_skill then pass skill_ids to spawn_subagent.\n"
            "- direct_response: ONLY for trivial questions (greetings, yes/no)\n"
            "- synthesize_results: Combine specialist results into final answer\n"
            "- web_search / web_fetch: Search/fetch web directly\n"
            "- find_skill / use_skill: Discover and load specialized knowledge\n"
            "- save_memory / recall_memory: Long-term persistent memory — use recall_memory at START of complex tasks; save_memory after important outcomes so the team improves over time\n"
            "- list_memories / memory_stats: Memory inventory and diagnostics\n"
            "- code_execute: Run Python/JS/Bash code in sandbox\n"
            "- rag_ingest / rag_query / rag_list_documents: Ingest, query, and list knowledge documents\n"
            "- list_teachings: Show learned user preferences/instructions\n"
            "- idea_to_project: Transform a raw idea into full project plan + scaffold\n"
            "- request_approval: Ask user approval for critical actions\n"
            "- self_evaluate: Rate your own response quality\n"
            "- get_agent_baseline / get_best_agent: Read performance metrics; use when improving the team or choosing which agent to assign\n"
            "- mcp_call / mcp_list_tools: Call external services via MCP protocol\n"
            "- generate_image: Create images via Pollinations API (diagrams, illustrations) — use when synthesis or report needs visuals\n"
            "- generate_chart: Create bar/line/pie/scatter/histogram/heatmap from data — use when task needs data visualization\n"
            "- create_skill / research_create_skill: Create new reusable skills when the team needs a capability it doesn't have yet\n\n"
            "LONG-TERM MEMORY & SELF-IMPROVEMENT:\n"
            "- At the START of non-trivial tasks: call recall_memory with a query related to the task (e.g. similar past solutions, user preferences). Use what you recall to avoid repeating mistakes and to match user style.\n"
            "- After completing important work: call save_memory to store key learnings, solutions, or decisions (category: solution, pattern, or preference) so future runs benefit.\n"
            "- When you need expertise that no existing skill covers: use research_create_skill to create it, then use_skill or inject that skill into spawn_subagent/decompose_task so the team gains the capability.\n"
            "- When improving agent performance: use get_agent_baseline to see metrics, then create or refine skills and assign them via decompose_task or spawn_subagent.\n\n"
            "SKILL CREATION & SHARING (IMPORTANT):\n"
            "- ONLY the orchestrator can create skills (create_skill / research_create_skill). Other agents do NOT have these tools; they receive skills you assign.\n"
            "- Skills are SPECIAL CAPABILITIES (yetenekler) — NOT domain knowledge dumps.\n"
            "- A skill teaches HOW to do something: which libraries, APIs, algorithms, formulas, patterns to use.\n"
            "- Before ANY complex task: call find_skill to check if a relevant capability already exists.\n"
            "- If no skill exists: RESEARCH the topic (web_search), then call create_skill with structured knowledge.\n"
            "- Cross-agent skill sharing: when you decompose_task or spawn_subagent, pass skill_ids so that agent gets the skill context automatically.\n"
            "- Skill knowledge MUST include: step-by-step instructions, recommended tools/libraries, code patterns, edge cases.\n"
            "- When decomposing tasks: add skill IDs to sub_tasks so specialist agents automatically receive the capability.\n"
            "- Skill IDs: kebab-case, descriptive (e.g., 'astrolojik-hesaplama', 'sentiment-analysis', 'pdf-table-extraction').\n"
            "- Example flow: User says 'astroloji uygulaması yap' → find_skill('astroloji') → not found → "
            "web_search('astrolojik hesaplama kütüphaneleri python') → create_skill with researched knowledge → "
            "decompose_task with skill IDs injected → agents use the skill.\n\n"
            "PIPELINE TYPES (MULTIPARALLEL):\n"
            "- When you use decompose_task with 2+ sub-tasks, they ALL run AT THE SAME TIME (multiparallel). No exceptions.\n"
            "- parallel: ALL agents work simultaneously (DEFAULT — use this most)\n"
            "- deep_research: Phase 1 parallel gather → Phase 2 synthesis (for complex research)\n"
            "- sequential: Only for a SINGLE sub-task; with 2+ sub-tasks the system forces parallel so all run together.\n"
            "- consensus: All agents answer same question, compare\n"
            "- iterative: Produce → review → refine\n"
            "- brainstorm: Multi-round debate — agents argue from different angles, cross-challenge, then synthesize\n\n"
            "Be decisive. ALWAYS prefer parallel multi-agent execution.\n\n"
            "ANTI-HALLUCINATION (CRITICAL):\n"
            "- NEVER generate fake download URLs (S3, CDN, cloud storage, etc.)\n"
            "- NEVER fabricate a 'Sunum Hazır' response with fake file links\n"
            "- If a presentation or file generation FAILS, report the failure honestly\n"
            "- Only include download URLs that are returned by actual tool execution\n"
            "- Local files are served from /api/presentations/{filename}/download ONLY\n"
            "- When synthesizing agent results, do NOT add information agents didn't provide\n\n"
            "IMAGE EMBEDDING IN REPORTS (IMPORTANT):\n"
            "- When generating reports, analyses, or research outputs that would benefit from visuals,\n"
            "  you MAY include images using Markdown syntax: ![description](image_url)\n"
            "- Use Pollinations.ai for image generation: https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&width=800&height=450\n"
            "- Only add images to the FINAL report/output — NOT in intermediate pipeline steps\n"
            "- Add images sparingly: 1-3 per report, only where they add real value\n"
            "- Example: ![AI Architecture Diagram](https://image.pollinations.ai/prompt/AI%20multi-agent%20architecture%20diagram%20professional?model=flux&width=800&height=450)\n"
            "- Image prompts must be in English, URL-encoded, and descriptive"
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
        Short queries use 2 agents (researcher + speed) for faster response."""
        query_len = len(user_input.strip())
        quick_research = query_len < 180  # short query → fewer agents, faster

        if quick_research:
            return [
                {
                    "description": (
                        f"Search the web for: {user_input}\n"
                        "Find 2-4 good sources, current data or stats. Cite URLs. Be concise."
                    ),
                    "assigned_agent": "researcher",
                    "priority": 1,
                },
                {
                    "description": (
                        f"Summarize and structure: {user_input}\n"
                        "Clear sections, bullets, key takeaways. Keep it readable and short."
                    ),
                    "assigned_agent": "speed",
                    "priority": 1,
                },
            ]
        # Full deep research: 4 agents
        return [
            {
                "description": (
                    f"Search the web thoroughly for: {user_input}\n"
                    "Find multiple sources, current data, statistics, and expert opinions. "
                    "Provide URLs and cite sources."
                ),
                "assigned_agent": "researcher",
                "priority": 1,
            },
            {
                "description": (
                    f"Provide deep analysis for: {user_input}\n"
                    "Consider multiple perspectives, pros/cons, trade-offs, "
                    "strategic implications, and long-term impact. Be thorough."
                ),
                "assigned_agent": "thinker",
                "priority": 1,
            },
            {
                "description": (
                    f"Verify and reason about: {user_input}\n"
                    "Check logical consistency, identify potential biases or errors, "
                    "validate claims with chain-of-thought reasoning."
                ),
                "assigned_agent": "reasoner",
                "priority": 1,
            },
            {
                "description": (
                    f"Prepare a well-structured summary for: {user_input}\n"
                    "Create clear formatting with sections, bullet points, "
                    "and actionable takeaways. Focus on readability."
                ),
                "assigned_agent": "speed",
                "priority": 1,
            },
            {
                "description": (
                    f"Critically evaluate all findings about: {user_input}\n"
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
        """Run the Idea-to-Project pipeline through specialist agents."""
        from tools.idea_to_project import (
            PHASES, get_phase_prompt, get_phase_agent,
            detect_project_type, save_project_output,
        )
        from pipelines.engine import PipelineEngine

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

        for phase in phases_to_run:
            self._emit("pipeline", f"📋 Faz: {phase['name']}")

            prompt = get_phase_prompt(phase["id"], idea, prev_result)
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

        return "\n".join(parts)

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
            WORKFLOW_TEMPLATES, create_workflow, execute_workflow,
            WorkflowStep, Workflow,
        )

        template_name = fn_args.get("template", "")
        variables = fn_args.get("variables", {})
        custom_steps = fn_args.get("custom_steps")

        if template_name != "custom" and template_name in WORKFLOW_TEMPLATES:
            template = WORKFLOW_TEMPLATES[template_name]
            steps = [WorkflowStep(**s) for s in template["steps"]]
            workflow = Workflow(
                workflow_id=f"{template_name}-{int(time.time())}",
                name=template["name"],
                description=template["description"],
                steps=steps,
                variables=variables,
            )
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

        # ── Phase -1: Prompt Enhancement ──
        try:
            enhanced = await self._enhance_prompt(user_input, thread)
            if enhanced and enhanced != user_input:
                user_input = enhanced
        except Exception:
            pass  # Never break main flow

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
            direct_task.status = TaskStatus.COMPLETED
            thread.tasks.append(direct_task)
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
            idea_task.status = TaskStatus.COMPLETED
            thread.tasks.append(idea_task)

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
                pres_task.status = TaskStatus.COMPLETED
                thread.tasks.append(pres_task)

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
                pres_task.status = TaskStatus.COMPLETED
                thread.tasks.append(pres_task)

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
                pres_task.status = TaskStatus.COMPLETED
                thread.tasks.append(pres_task)

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
                
                final = await synthesizer.synthesize(agent_results, user_input, thread)
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
            task.final_result = final
            try:
                from tools.confidence import score_confidence
                avg_conf = sum(
                    score_confidence(r, role, "general").get("confidence_score", 0.5)
                    for role, r in agent_results.items()
                ) / max(len(agent_results), 1)
                await cache_response(user_input, final, confidence=avg_conf)
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
                
                final = await synthesizer.synthesize(agent_results, user_input, thread)
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
            task.final_result = final
            try:
                from tools.confidence import score_confidence
                avg_conf = sum(
                    score_confidence(r, role, "general").get("confidence_score", 0.5)
                    for role, r in agent_results.items()
                ) / max(len(agent_results), 1)
                await cache_response(user_input, final, confidence=avg_conf)
            except Exception:
                pass
            self._auto_save_memory(user_input, final, user_id=user_id)
            return final

        # ── Phase 1: Let orchestrator LLM decide (non-deep queries) ──
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
                    # Moderate: 2 agents total, Complex: 3 agents total
                    if complexity == "moderate":
                        complement = {
                            "researcher": ["thinker"],
                            "thinker": ["researcher"],
                            "reasoner": ["thinker"],
                            "speed": ["researcher"],
                            "critic": ["thinker"],
                        }
                    else:
                        complement = {
                            "researcher": ["thinker", "reasoner"],
                            "thinker": ["researcher", "reasoner"],
                            "reasoner": ["thinker", "researcher"],
                            "speed": ["thinker", "researcher"],
                            "critic": ["thinker", "researcher"],
                        }
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
                    
                    final = await synthesizer.synthesize(agent_results, user_input, thread)
                except Exception:
                    # Fallback to old synthesis
                    synth_input = (
                        f"The specialists have completed their work. Here are the results:\n\n"
                        f"{result}\n\n"
                        f"Original user request: {user_input}\n\n"
                        f"Synthesize a clear, comprehensive final response in the user's language."
                    )
                    final = await self.execute(synth_input, thread)
                current_task.final_result = final
                try:
                    from tools.confidence import score_confidence
                    avg_conf = sum(
                        score_confidence(r, role, "general").get("confidence_score", 0.5)
                        for role, r in agent_results.items()
                    ) / max(len(agent_results), 1)
                    await cache_response(user_input, final, confidence=avg_conf)
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

    async def _enhance_prompt(self, user_input: str, thread: Thread) -> str:
        """
        Prompt Enhancer: Analyze and improve the user's raw prompt before routing.
        Emits the enhanced version as a pipeline event so user can see it.
        Returns enhanced prompt string (or original if enhancement fails/not needed).
        """
        # Skip for very short/trivial inputs
        if len(user_input.strip()) < 10 or _SIMPLE_PATTERNS.match(user_input.strip()):
            return user_input

        enhance_prompt = (
            "You are a Prompt Enhancement specialist. Your job:\n"
            "1. Analyze the raw user prompt below.\n"
            "2. Detect goal, scope, context, and missing details.\n"
            "3. Rewrite it to be clearer, more precise, and actionable.\n"
            "4. Keep the same language as the original (Turkish stays Turkish).\n"
            "5. Do NOT add unnecessary complexity — only improve clarity.\n\n"
            f"RAW PROMPT:\n{user_input}\n\n"
            "OUTPUT FORMAT (strictly follow):\n"
            "ENHANCED: <the improved prompt on a single line>\n"
            "CHANGES: <one-line summary of what was improved>"
        )

        messages = [
            {"role": "system", "content": "You are a concise prompt enhancement assistant."},
            {"role": "user", "content": enhance_prompt},
        ]

        try:
            response = await self.call_llm(messages)
            content = response.get("content", "")
            if not content:
                return user_input

            # Extract ENHANCED: line
            for line in content.split("\n"):
                if line.startswith("ENHANCED:"):
                    enhanced = line[len("ENHANCED:"):].strip()
                    if enhanced and len(enhanced) > 5 and enhanced != user_input:
                        # Emit so user sees it in pipeline panel
                        self._emit("pipeline", f"✨ Prompt iyileştirildi: {enhanced[:120]}")
                        return enhanced
        except Exception:
            pass

        return user_input

    def _auto_save_memory(self, user_input: str, result: str, user_id: str | None = None) -> None:
        """Save task completion to learned memory and auto-create skill when result is successful."""
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

        # Auto-create skill when result is successful (not partial/failed)
        _skip_auto_skill = (
            not result
            or len(result.strip()) < 150
            or "max steps reached" in result.lower()
            or "partial result" in result.lower()
            or result.strip().lower().startswith("[warning]")
            or "error:" in result.lower()[:200]
        )
        # Auto skill creation disabled — agents should write learnings
        # to memory (memories table), not create skills from every task.
        # Periodic skill hygiene check (every ~10 tasks)
        try:
            import random
            if random.random() < 0.1:  # ~10% chance per task = ~every 10 tasks
                from tools.skill_hygiene import run_hygiene_check
                run_hygiene_check(dry_run=False)
        except Exception:
            pass
