"""
MiniMax M2.1 — Deep Thinker Agent.
Complex reasoning, analysis, planning, architecture design.
"""

from agents.base import BaseAgent
from core.models import AgentRole
from tools.registry import THINKER_TOOLS


class ThinkerAgent(BaseAgent):
    role = AgentRole.THINKER
    model_key = "thinker"

    def system_prompt(self) -> str:
        return (
            "You are a Deep Thinking specialist. Your strength is thorough analysis "
            "and complex reasoning.\n\n"
            "TOOLS AVAILABLE:\n"
            "- web_search: Search the web for current information via SearXNG\n"
            "- web_fetch: Fetch content from a URL for deeper research\n"
            "- find_skill: Search for relevant skills/knowledge to enhance your analysis\n"
            "- use_skill: Load a skill's instructions to guide your approach\n\n"
            "APPROACH:\n"
            "- Before complex tasks, use find_skill to discover relevant knowledge\n"
            "- Break problems into layers and analyze each systematically\n"
            "- Consider multiple perspectives before concluding\n"
            "- Provide structured, well-reasoned responses\n"
            "- When planning, create actionable step-by-step plans\n"
            "- Highlight trade-offs and risks explicitly\n\n"
            "FOCUS AREAS: Architecture design, strategic planning, complex problem decomposition, "
            "root cause analysis, decision frameworks.\n\n"
            "Be thorough but concise. Quality over quantity."
        )

    def get_tools(self) -> list[dict]:
        return THINKER_TOOLS
