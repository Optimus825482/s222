"""
GLM 4.7 — Research Agent.
Web search via SearXNG, web fetch, data gathering, summarization.
"""

from __future__ import annotations

from agents.base import BaseAgent
from core.models import AgentRole, Thread
from tools.registry import RESEARCHER_TOOLS


class ResearcherAgent(BaseAgent):
    role = AgentRole.RESEARCHER
    model_key = "researcher"

    def system_prompt(self) -> str:
        return (
            "You are a Research specialist with web search and fetch capabilities.\n\n"
            "TOOLS AVAILABLE:\n"
            "- web_search: Search the web for current information\n"
            "- web_fetch: Fetch full content from a specific URL\n"
            "- find_skill: Search for relevant skills/knowledge\n"
            "- use_skill: Load a skill's instructions\n\n"
            "APPROACH:\n"
            "- Use web_search to find relevant sources first\n"
            "- Use web_fetch to get detailed content from promising URLs\n"
            "- Use find_skill for specialized research methodologies\n"
            "- Cross-reference multiple sources when possible\n"
            "- Summarize findings clearly with source attribution\n"
            "- Distinguish facts from opinions\n"
            "- If search returns no useful results, state that clearly\n\n"
            "FOCUS AREAS: Current events, technical documentation, market research, "
            "fact-checking, data gathering, literature review.\n\n"
            "Always cite your sources. Accuracy over speed."
        )

    def get_tools(self) -> list[dict]:
        return RESEARCHER_TOOLS

    async def _handle_custom_tool(self, fn_name: str, fn_args: dict, thread: Thread) -> str:
        """Researcher has no extra custom tools — all handled by base."""
        return f"Unknown tool: {fn_name}"
