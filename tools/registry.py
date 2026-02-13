"""
Tool registry — 12-Factor #4: Tools are structured outputs.
Each agent declares its available tools. LLM returns structured JSON.
"""

from __future__ import annotations

from typing import Any

# ── Shared Tool Definitions ──────────────────────────────────────

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information using SearXNG. Returns titles, URLs, and snippets.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (default 5)"},
            },
            "required": ["query"],
        },
    },
}

WEB_FETCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_fetch",
        "description": "Fetch and extract text content from a URL. Returns page title and cleaned text.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return (default 8000)",
                },
            },
            "required": ["url"],
        },
    },
}

FIND_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "find_skill",
        "description": (
            "Search for relevant skills/knowledge based on a query. "
            "Returns matching skills with descriptions. "
            "Use this to discover what specialized knowledge is available before starting a task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What kind of skill or knowledge you need (e.g. 'security review', 'data analysis', 'code debugging')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max skills to return (default 3)",
                },
            },
            "required": ["query"],
        },
    },
}

SAVE_MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": "save_memory",
        "description": (
            "Save important information to persistent memory for future reference. "
            "Use after completing tasks to remember solutions, user preferences, "
            "learned patterns, or key findings. Categories: general, solution, preference, pattern, research."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The information to remember (be concise but complete)",
                },
                "category": {
                    "type": "string",
                    "enum": ["general", "solution", "preference", "pattern", "research"],
                    "description": "Memory category",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for easier recall (e.g. ['python', 'api', 'bug-fix'])",
                },
            },
            "required": ["content"],
        },
    },
}

RECALL_MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": "recall_memory",
        "description": (
            "Search persistent memory for relevant past knowledge. "
            "Use at the START of tasks to check if similar problems were solved before, "
            "or to recall user preferences and past decisions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for in memory",
                },
                "category": {
                    "type": "string",
                    "enum": ["general", "solution", "preference", "pattern", "research"],
                    "description": "Filter by category (optional)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return (default 5)",
                },
            },
            "required": ["query"],
        },
    },
}

USE_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "use_skill",
        "description": (
            "Load a skill's knowledge/instructions by its ID. "
            "Call find_skill first to discover available skills, then use_skill to load the one you need. "
            "The skill's knowledge will be injected into your context."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "The skill ID from find_skill results (e.g. 'deep-research', 'code-generation')",
                },
            },
            "required": ["skill_id"],
        },
    },
}

# ── Orchestrator Tools ───────────────────────────────────────────

ORCHESTRATOR_TOOLS = [
    SAVE_MEMORY_TOOL,
    RECALL_MEMORY_TOOL,
    {
        "type": "function",
        "function": {
            "name": "decompose_task",
            "description": "Break a complex user request into sub-tasks and assign each to a specialist agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sub_tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string", "description": "What this sub-task should accomplish"},
                                "assigned_agent": {
                                    "type": "string",
                                    "enum": ["thinker", "speed", "researcher", "reasoner"],
                                    "description": "Which specialist agent to assign",
                                },
                                "priority": {"type": "integer", "description": "1=highest priority"},
                                "depends_on": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "IDs of sub-tasks this depends on",
                                },
                                "skills": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Skill IDs to inject into this agent (from find_skill results)",
                                },
                            },
                            "required": ["description", "assigned_agent"],
                        },
                    },
                    "pipeline_type": {
                        "type": "string",
                        "enum": ["sequential", "parallel", "consensus", "iterative"],
                        "description": "How to execute the sub-tasks",
                    },
                    "reasoning": {"type": "string", "description": "Why this decomposition and pipeline"},
                },
                "required": ["sub_tasks", "pipeline_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "direct_response",
            "description": "Respond directly to the user without delegating to specialists. Use for simple questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "response": {"type": "string", "description": "Direct answer to the user"},
                },
                "required": ["response"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize_results",
            "description": "Combine results from multiple specialist agents into a final coherent response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "final_response": {"type": "string", "description": "Synthesized final answer"},
                    "confidence": {"type": "number", "description": "Confidence 0-1"},
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which agents contributed",
                    },
                },
                "required": ["final_response"],
            },
        },
    },
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
]

# ── Researcher Tools ─────────────────────────────────────────────

RESEARCHER_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
]

# ── Thinker Tools ────────────────────────────────────────────────

THINKER_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
]

# ── Speed Tools ──────────────────────────────────────────────────

SPEED_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
]

# ── Reasoner Tools ───────────────────────────────────────────────

REASONER_TOOLS = [
    WEB_SEARCH_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
]

# ── Agent → Tools Mapping ────────────────────────────────────────

AGENT_TOOLS: dict[str, list[dict[str, Any]]] = {
    "orchestrator": ORCHESTRATOR_TOOLS,
    "thinker": THINKER_TOOLS,
    "speed": SPEED_TOOLS,
    "researcher": RESEARCHER_TOOLS,
    "reasoner": REASONER_TOOLS,
}
