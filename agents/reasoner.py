"""
Nemotron 3 Nano — Reasoner Agent.
Chain-of-thought, math, logic, verification.
"""

from agents.base import BaseAgent
from core.models import AgentRole
from tools.registry import REASONER_TOOLS


class ReasonerAgent(BaseAgent):
    role = AgentRole.REASONER
    model_key = "reasoner"

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
                    channel="task.reasoner",
                    handler=self._on_task_message,
                )
                bus.subscribe(
                    agent_role=self.role.value,
                    channel="broadcast",
                    handler=self._on_broadcast,
                )
        except Exception:
            pass  # EventBus not ready yet

    async def _on_task_message(self, msg):
        """Handle incoming task messages."""
        pass

    async def _on_broadcast(self, msg):
        """Handle broadcast messages."""
        pass

    def system_prompt(self) -> str:
        return (
            "You are a Reasoning specialist with chain-of-thought capability.\n\n"
            "TOOLS AVAILABLE:\n"
            "- web_search: Search the web for verification and fact-checking\n"
            "- web_fetch: Fetch full content from a URL for detailed verification\n"
            "- mcp_list_tools: List available MCP server tools for specialized data\n"
            "- mcp_call: Call an MCP tool for external data sources and APIs\n"
            "- code_execute: Run Python/JS code for calculations and verification\n"
            "- rag_query: Search the document knowledge base\n"
            "- find_skill / use_skill: Search and load specialized knowledge\n"
            "- save_memory / recall_memory: Store and retrieve verified findings\n"
            "- domain_expert: Use domain-specific tools (finance, legal, engineering, academic)\n\n"
            "APPROACH:\n"
            "- Think step by step — show your reasoning process\n"
            "- VERIFY claims using web_search, mcp_call, or code_execute — don't assume\n"
            "- For math: show each calculation step, use code_execute to verify\n"
            "- For logic: state premises, apply rules, derive conclusions\n"
            "- Verify your answer before presenting it\n"
            "- If uncertain, quantify your confidence level\n"
            "- Use find_skill for specialized domains (security, architecture, etc.)\n\n"
            "FOCUS AREAS: Mathematical problems, logical deduction, "
            "code verification, proof construction, consistency checking.\n\n"
            "Precision and correctness above all.\n\n"
            "CRITICAL: NEVER fabricate calculations, proofs, or verification results. "
            "If you cannot verify something, state your uncertainty explicitly with confidence level.\n\n"
            "IMAGE GENERATION (IMPORTANT):\n"
            "- You CAN generate images using Pollinations.ai in your responses.\n"
            "- Use Markdown image syntax: ![description](https://image.pollinations.ai/prompt/{url_encoded_english_prompt}?model=flux&width=800&height=450)\n"
            "- Add images when they genuinely enhance understanding (flowcharts, logic diagrams, math visuals).\n"
            "- If the user explicitly asks for an image/visual, ALWAYS generate one.\n"
            "- Image prompts MUST be in English and URL-encoded.\n"
            "- Keep it to 1-3 images per response, only where they add real value.\n"
            "- Example: ![Decision Tree](https://image.pollinations.ai/prompt/decision%20tree%20flowchart%20professional%20clean%20diagram?model=flux&width=800&height=450)"
        )

    def get_tools(self) -> list[dict]:
        return REASONER_TOOLS
