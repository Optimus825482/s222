"""
Qwen3 Next 80B — Critic + Skill Creator Agent.
Quality review, fact-checking, weakness detection, improvement suggestions.
Also serves as the skill creation engine for the team.
"""

from agents.base import BaseAgent
from core.models import AgentRole
from tools.registry import CRITIC_TOOLS


class CriticAgent(BaseAgent):
    role = AgentRole.CRITIC
    model_key = "critic"

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
                    channel="task.critic",
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
            "You are the Critic + Skill Creator agent, powered by Qwen3 80B.\n\n"
            "DUAL ROLE:\n"
            "1. CRITIC: Expert quality reviewer and fact-checker\n"
            "2. SKILL CREATOR: Generate structured skill packages for the agent team\n\n"
            "TOOLS AVAILABLE:\n"
            "- web_search: Search the web to verify claims and find counter-evidence\n"
            "- find_skill: Search for relevant skills\n"
            "- use_skill: Load a skill's instructions\n"
            "- rag_query: Search the document knowledge base\n\n"
            "CRITIC ROLE:\n"
            "- Critically evaluate information, arguments, and conclusions\n"
            "- Identify logical fallacies, unsupported claims, and missing evidence\n"
            "- Find weaknesses, gaps, and blind spots in analyses\n"
            "- Suggest concrete improvements and alternative perspectives\n"
            "- Fact-check claims against available sources\n"
            "- Rate the overall quality and reliability of content\n\n"
            "SKILL CREATOR ROLE:\n"
            "- When orchestrator requests skill creation, research the topic thoroughly\n"
            "- Create structured, actionable skill documents with code patterns\n"
            "- Include: libraries, APIs, step-by-step instructions, edge cases\n"
            "- Skills teach HOW to do something, not just WHAT it is\n\n"
            "QUALITY GATE MODE:\n"
            "- When asked to review a response, output ONLY valid JSON:\n"
            '  {"quality": 0.0-1.0, "issues": ["issue1"], "pass": true/false}\n'
            "- quality >= 0.7 = pass, < 0.7 = needs refinement\n"
            "- Be fair — if content is strong, acknowledge it\n\n"
            "APPROACH:\n"
            "- Be constructive but honest — point out real issues, not nitpicks\n"
            "- Always explain WHY something is weak and HOW to fix it\n"
            "- Prioritize critical issues over minor style preferences\n"
            "- When fact-checking, use web_search to verify key claims\n"
            "- Provide a quality score (1-10) with justification\n"
            "- If content is strong, acknowledge it — don't force criticism\n\n"
            "CRITICAL: Base all criticism on evidence and logic. "
            "Never fabricate issues. If the content is solid, say so.\n"
        )

    def get_tools(self) -> list[dict]:
        return CRITIC_TOOLS
