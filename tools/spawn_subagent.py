"""
Spawn Subagent — Run a one-off specialist agent with custom role and optional skills.
Enables the orchestrator to create and run dynamic subagents on any topic
without being limited to the fixed four (thinker, speed, researcher, reasoner).
"""

from __future__ import annotations

import asyncio
from typing import Any

from openai import AsyncOpenAI

from config import MODELS, NVIDIA_API_KEY, NVIDIA_BASE_URL


def _load_skill_context(skill_id: str) -> str:
    """Load full knowledge for a skill (dynamic_skills first, then skill_finder)."""
    try:
        from tools.dynamic_skills import get_full_skill_context
        ctx = get_full_skill_context(skill_id)
        if ctx:
            return ctx
    except Exception:
        pass
    try:
        from tools.skill_finder import get_skill_knowledge
        kn = get_skill_knowledge(skill_id)
        return kn or ""
    except Exception:
        return ""


async def run_subagent(
    task: str,
    role_description: str,
    skill_ids: list[str] | None = None,
    model_key: str = "thinker",
) -> str:
    """
    Run a one-off specialist agent with a custom role and optional skills.
    Uses the specified model (default: thinker) with a custom system prompt.
    Returns the agent's response text.
    """
    skill_ids = skill_ids or []
    skill_context = ""
    if skill_ids:
        parts = []
        for sid in skill_ids:
            ctx = _load_skill_context(sid)
            if ctx:
                parts.append(f"<skill id=\"{sid}\">\n{ctx}\n</skill>")
        if parts:
            skill_context = (
                "\n\n--- INJECTED SKILLS (follow these protocols) ---\n"
                + "\n\n".join(parts)
                + "\n--- END SKILLS ---\n\n"
            )

    system_content = (
        "You are a specialist subagent. Your role and expertise:\n"
        f"{role_description}\n\n"
        "RULES:\n"
        "- Be focused and concise. Answer only what is asked.\n"
        "- If the task requires skills injected below, follow those protocols.\n"
        "- Do not introduce yourself; go straight to the task.\n"
        "- Output in the same language as the task when possible.\n"
        f"{skill_context}"
    )

    cfg = MODELS.get(model_key) or MODELS["thinker"]
    client = AsyncOpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)

    kwargs: dict[str, Any] = {
        "model": cfg["id"],
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": task},
        ],
        "max_tokens": cfg.get("max_tokens", 4096),
        "temperature": min(cfg.get("temperature", 0.7), 0.9),
    }
    if "top_p" in cfg:
        kwargs["top_p"] = cfg["top_p"]
    if cfg.get("extra_body"):
        kwargs["extra_body"] = cfg["extra_body"]

    response = await client.chat.completions.create(**kwargs)
    content = (response.choices[0].message.content or "").strip()
    return content
