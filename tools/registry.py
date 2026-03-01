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

# ── Code Execution Tool ─────────────────────────────────────────

CODE_EXECUTE_TOOL = {
    "type": "function",
    "function": {
        "name": "code_execute",
        "description": (
            "Execute code in a sandboxed environment. Supports Python, JavaScript, Bash. "
            "Use for calculations, data processing, testing code snippets, or generating outputs. "
            "Returns stdout, stderr, and execution status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The code to execute",
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "bash"],
                    "description": "Programming language (default: python)",
                },
            },
            "required": ["code"],
        },
    },
}

# ── RAG Document Tools ───────────────────────────────────────────

RAG_INGEST_TOOL = {
    "type": "function",
    "function": {
        "name": "rag_ingest",
        "description": (
            "Ingest a document into the knowledge base for later retrieval. "
            "Provide text content with a title. The document will be chunked, "
            "embedded, and stored for semantic search."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Document text content to ingest",
                },
                "title": {
                    "type": "string",
                    "description": "Document title for identification",
                },
                "source": {
                    "type": "string",
                    "description": "Source URL or file path (optional)",
                },
            },
            "required": ["content", "title"],
        },
    },
}

RAG_QUERY_TOOL = {
    "type": "function",
    "function": {
        "name": "rag_query",
        "description": (
            "Search the document knowledge base for relevant information. "
            "Returns matching document chunks ranked by semantic similarity. "
            "Use when the user asks about previously ingested documents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max chunks to return (default 5)",
                },
            },
            "required": ["query"],
        },
    },
}

# ── Idea-to-Project Tool ────────────────────────────────────────

IDEA_TO_PROJECT_TOOL = {
    "type": "function",
    "function": {
        "name": "idea_to_project",
        "description": (
            "Transform a raw idea into a professional project plan. "
            "Runs a multi-phase pipeline: Idea Analysis → PRD → Architecture → "
            "Task Breakdown → Project Scaffold. Each phase builds on the previous. "
            "Use when user describes a project idea they want to build."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "idea": {
                    "type": "string",
                    "description": "The user's project idea description",
                },
                "project_type": {
                    "type": "string",
                    "enum": ["web-app", "api-service", "mobile-app", "cli-tool", "ai-agent", "data-pipeline", "custom"],
                    "description": "Project type (auto-detected if not specified)",
                },
                "phase": {
                    "type": "string",
                    "enum": ["analyze", "prd", "architecture", "tasks", "scaffold", "all"],
                    "description": "Which phase to run (default: all)",
                },
            },
            "required": ["idea"],
        },
    },
}

# ── Human Approval Tool ──────────────────────────────────────────

REQUEST_APPROVAL_TOOL = {
    "type": "function",
    "function": {
        "name": "request_approval",
        "description": (
            "Request human approval before performing a critical action. "
            "Use for: code execution, file modifications, external API calls, "
            "deployments, or any action with side effects. "
            "Returns approval status and any user modifications."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Type of action requiring approval",
                },
                "description": {
                    "type": "string",
                    "description": "Clear description of what will happen",
                },
                "details": {
                    "type": "object",
                    "description": "Additional details about the action",
                },
            },
            "required": ["action", "description"],
        },
    },
}

# ── Self-Evaluate Tool ───────────────────────────────────────────

SELF_EVALUATE_TOOL = {
    "type": "function",
    "function": {
        "name": "self_evaluate",
        "description": (
            "Evaluate the quality of your own response before sending it. "
            "Scores accuracy, completeness, clarity, actionability, and depth. "
            "If score is below threshold, triggers self-improvement loop."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "The response to evaluate",
                },
                "question": {
                    "type": "string",
                    "description": "The original question/task",
                },
            },
            "required": ["response", "question"],
        },
    },
}

# ── MCP Tool ──────────────────────────────────────────────────────

MCP_CALL_TOOL = {
    "type": "function",
    "function": {
        "name": "mcp_call",
        "description": (
            "Call a tool on an external MCP (Model Context Protocol) server. "
            "Use to interact with external services like GitHub, Slack, databases, etc. "
            "First use mcp_list_tools to discover available tools on a server."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "string",
                    "description": "MCP server ID (e.g. 'github', 'slack', 'postgres')",
                },
                "tool_name": {
                    "type": "string",
                    "description": "Tool name on the server",
                },
                "arguments": {
                    "type": "object",
                    "description": "Tool arguments as key-value pairs",
                },
            },
            "required": ["server_id", "tool_name"],
        },
    },
}

MCP_LIST_TOOLS_TOOL = {
    "type": "function",
    "function": {
        "name": "mcp_list_tools",
        "description": (
            "List available tools on MCP servers. "
            "Returns tool names and descriptions for each registered server. "
            "Use before mcp_call to discover what tools are available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "string",
                    "description": "Specific server ID to list tools for (optional, lists all if omitted)",
                },
            },
        },
    },
}

# ── Dynamic Skill Management Tools ──────────────────────────────

CREATE_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "create_skill",
        "description": (
            "Create a new reusable skill (capability) package. "
            "A skill is a structured knowledge+instructions package that gives agents a specific ABILITY. "
            "Example: 'astrolojik-hesaplama' skill teaches agents HOW to do astrological calculations. "
            "Use when a task requires specialized capability that doesn't exist yet."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "Unique kebab-case ID (e.g. 'astrolojik-hesaplama', 'sentiment-analysis')",
                },
                "name": {
                    "type": "string",
                    "description": "Human-readable skill name (e.g. 'Astrolojik Hesaplama Yeteneği')",
                },
                "description": {
                    "type": "string",
                    "description": "What capability this skill provides and when to use it",
                },
                "knowledge": {
                    "type": "string",
                    "description": (
                        "The actual instructions, methods, libraries, APIs, formulas, and step-by-step "
                        "procedures that teach an agent HOW to perform this capability. "
                        "Must be detailed and actionable — not just a description."
                    ),
                },
                "category": {
                    "type": "string",
                    "description": "Skill category (e.g. 'coding', 'research', 'analysis', 'science', 'finance')",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords for search matching",
                },
                "references": {
                    "type": "object",
                    "description": "Optional reference files: {'filename.md': 'content'} for detailed docs",
                    "additionalProperties": {"type": "string"},
                },
                "scripts": {
                    "type": "object",
                    "description": "Optional script files: {'script.py': 'code'} for executable utilities",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["skill_id", "name", "description", "knowledge"],
        },
    },
}

RESEARCH_CREATE_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "research_create_skill",
        "description": (
            "Research a topic via web search, then create a structured skill (capability) package. "
            "Use this BEFORE starting any complex task that requires specialized knowledge. "
            "Example: Before building an astrology app, research astrological calculation methods, "
            "libraries, and APIs, then create an 'astrolojik-hesaplama' skill that all agents can use. "
            "This is the PRIMARY way to give agents new capabilities at runtime."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "What capability to research (e.g. 'astrological calculations with Python')",
                },
                "skill_id": {
                    "type": "string",
                    "description": "Desired skill ID in kebab-case (e.g. 'astrolojik-hesaplama')",
                },
                "skill_name": {
                    "type": "string",
                    "description": "Human-readable name (e.g. 'Astrolojik Hesaplama Yeteneği')",
                },
                "category": {
                    "type": "string",
                    "description": "Skill category",
                },
                "search_queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific web search queries to research (2-4 queries recommended)",
                },
            },
            "required": ["topic", "skill_id", "skill_name"],
        },
    },
}

# ── Image Generation Tool ────────────────────────────────────────

GENERATE_IMAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "Generate an image using Pollinations.ai and return a downloadable URL. "
            "Use when the user asks for an image, visual, illustration, diagram, or when "
            "a report would benefit from a visual. The image is generated via AI (Flux model). "
            "Returns a markdown image embed and a direct download URL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Image description in English (be specific and descriptive)",
                },
                "width": {
                    "type": "integer",
                    "description": "Image width in pixels (default 800)",
                },
                "height": {
                    "type": "integer",
                    "description": "Image height in pixels (default 450)",
                },
            },
            "required": ["prompt"],
        },
    },
}

# ── Orchestrator Tools ───────────────────────────────────────────

ORCHESTRATOR_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
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
                        "enum": ["sequential", "parallel", "consensus", "iterative", "deep_research"],
                        "description": "How to execute the sub-tasks. Use 'parallel' for most tasks, 'deep_research' for complex research.",
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
    CODE_EXECUTE_TOOL,
    RAG_INGEST_TOOL,
    RAG_QUERY_TOOL,
    IDEA_TO_PROJECT_TOOL,
    REQUEST_APPROVAL_TOOL,
    SELF_EVALUATE_TOOL,
    MCP_CALL_TOOL,
    MCP_LIST_TOOLS_TOOL,
    CREATE_SKILL_TOOL,
    RESEARCH_CREATE_SKILL_TOOL,
    GENERATE_IMAGE_TOOL,
    {
        "type": "function",
        "function": {
            "name": "generate_presentation",
            "description": (
                "Generate a professional PPTX presentation with AI-generated visuals. "
                "Researches the topic, creates structured slides, and generates images via Pollinations.ai. "
                "Use when user asks for a presentation, sunum, slayt, or PPTX."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Presentation topic",
                    },
                    "slide_count": {
                        "type": "integer",
                        "description": "Number of content slides (default 10)",
                    },
                    "language": {
                        "type": "string",
                        "enum": ["tr", "en"],
                        "description": "Presentation language (default: tr)",
                    },
                },
                "required": ["topic"],
            },
        },
    },
]

# ── Researcher Tools ─────────────────────────────────────────────

RESEARCHER_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
    CREATE_SKILL_TOOL,
    RAG_QUERY_TOOL,
    GENERATE_IMAGE_TOOL,
]

# ── Thinker Tools ────────────────────────────────────────────────

THINKER_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
    CREATE_SKILL_TOOL,
    RAG_QUERY_TOOL,
    GENERATE_IMAGE_TOOL,
]

# ── Speed Tools ──────────────────────────────────────────────────

SPEED_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
    CREATE_SKILL_TOOL,
    CODE_EXECUTE_TOOL,
    RAG_QUERY_TOOL,
    GENERATE_IMAGE_TOOL,
]

# ── Reasoner Tools ───────────────────────────────────────────────

REASONER_TOOLS = [
    WEB_SEARCH_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
    CREATE_SKILL_TOOL,
    CODE_EXECUTE_TOOL,
    RAG_QUERY_TOOL,
    GENERATE_IMAGE_TOOL,
]

# ── Agent → Tools Mapping ────────────────────────────────────────

AGENT_TOOLS: dict[str, list[dict[str, Any]]] = {
    "orchestrator": ORCHESTRATOR_TOOLS,
    "thinker": THINKER_TOOLS,
    "speed": SPEED_TOOLS,
    "researcher": RESEARCHER_TOOLS,
    "reasoner": REASONER_TOOLS,
}
