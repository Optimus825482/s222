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
        "description": "Search the web for current information using Tavily, Exa, or Whoogle (Google proxy). Priority: Tavily → Exa → Whoogle. Returns titles, URLs, and snippets.",
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

YOUTUBE_SUMMARIZER_TOOL = {
    "type": "function",
    "function": {
        "name": "summarize_video",
        "description": (
            "Extract video info, transcript, and summary from a YouTube video. "
            "Returns title, description, metadata, and transcript (from captions or Whisper transcription). "
            "Supports automatic translation to any target language (e.g. 'tr' for Turkish). "
            "Use for researching YouTube content, extracting information from videos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "YouTube video URL (supports various formats: youtube.com, youtu.be, etc.)",
                },
                "language": {
                    "type": "string",
                    "description": "Preferred language code for subtitles (default: 'en')",
                },
                "target_language": {
                    "type": "string",
                    "description": "Target language for translation (e.g. 'tr' for Turkish, 'de' for German). If set, transcript will be auto-translated.",
                },
                "use_whisper_fallback": {
                    "type": "boolean",
                    "description": "Use Whisper transcription if no subtitles available (default: true)",
                },
                "whisper_model": {
                    "type": "string",
                    "enum": ["tiny", "base", "small", "medium", "large"],
                    "description": "Whisper model size for fallback transcription (default: 'base')",
                },
                "max_transcript_chars": {
                    "type": "integer",
                    "description": "Maximum characters to include in transcript (default: 10000)",
                },
            },
            "required": ["url"],
        },
    },
}

YOUTUBE_TRANSCRIPT_TOOL = {
    "type": "function",
    "function": {
        "name": "fetch_transcript",
        "description": (
            "Fetch the transcript/subtitles from a YouTube video. "
            "Returns the full text and timestamped segments. "
            "Fetches whatever language is available, then optionally auto-translates. "
            "Use when you need the raw text content of a YouTube video for analysis, research, or reference."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "YouTube video URL",
                },
                "target_language": {
                    "type": "string",
                    "description": "Auto-translate transcript to this language (e.g. 'tr', 'de', 'fr'). Omit to keep original.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return (default: 15000)",
                },
            },
            "required": ["url"],
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

LIST_MEMORIES_TOOL = {
    "type": "function",
    "function": {
        "name": "list_memories",
        "description": (
            "List stored memories with optional filters. "
            "Use when you need an overview before recall or when auditing saved knowledge."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "general",
                        "solution",
                        "preference",
                        "pattern",
                        "research",
                    ],
                    "description": "Optional category filter",
                },
                "layer": {
                    "type": "string",
                    "enum": ["session", "global"],
                    "description": "Optional memory layer filter",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum memories to list (default 20)",
                },
            },
        },
    },
}

MEMORY_STATS_TOOL = {
    "type": "function",
    "function": {
        "name": "memory_stats",
        "description": "Get memory statistics (counts by category/layer and recency overview).",
        "parameters": {
            "type": "object",
            "properties": {},
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

RAG_LIST_DOCUMENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "rag_list_documents",
        "description": (
            "List ingested RAG documents with metadata (title, chunk count, source). "
            "Use before rag_query to understand available knowledge."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number of documents (default 20)",
                },
                "user_id": {
                    "type": "string",
                    "description": "Optional user filter",
                },
            },
        },
    },
}

LIST_TEACHINGS_TOOL = {
    "type": "function",
    "function": {
        "name": "list_teachings",
        "description": (
            "List teachability entries (user preferences/instructions learned over time). "
            "Use to personalize responses consistently."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "active_only": {
                    "type": "boolean",
                    "description": "Return only active teachings (default true)",
                },
            },
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

# ── Dynamic Subagent (self-improving, long-term, skill-creating team) ─

SPAWN_SUBAGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "spawn_subagent",
        "description": (
            "Create and run a one-off specialist subagent on ANY topic. Use when the fixed agents (thinker, speed, researcher, reasoner) "
            "are not the right fit, or when you need a dedicated expert (e.g. crypto, legal, domain-specific). "
            "The subagent runs with the given role and optional skills, then returns its answer. "
            "Combine with find_skill/use_skill or research_create_skill when the needed expertise is missing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The concrete task or question for this subagent",
                },
                "role_description": {
                    "type": "string",
                    "description": "Expert role and expertise (e.g. 'Cryptocurrency and blockchain expert', 'Legal compliance specialist')",
                },
                "skill_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional skill IDs to inject (from find_skill). Use when the subagent should follow specific protocols.",
                },
                "model_key": {
                    "type": "string",
                    "enum": ["thinker", "researcher", "speed", "reasoner"],
                    "description": "Which model to use (default: thinker for quality, speed for fast/simple)",
                },
            },
            "required": ["task", "role_description"],
        },
    },
}

# ── Agent Performance Tools (agent-orchestration-improve-agent) ───

GET_AGENT_BASELINE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_agent_baseline",
        "description": (
            "Get performance baseline metrics for agents (task success rate, satisfaction, latency, token ratio). "
            "Use when improving agent performance, analyzing failures, or planning prompt/workflow changes. "
            "Optionally filter by agent_role to see one agent's baseline."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent_role": {
                    "type": "string",
                    "description": "Optional: specific agent (thinker, speed, researcher, reasoner). Omit for system-wide baseline.",
                },
            },
        },
    },
}

GET_BEST_AGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "get_best_agent",
        "description": (
            "Get the best-performing agent for a given task type based on historical evaluation scores. "
            "Use when decomposing a task to assign the right specialist (e.g. research, coding, math). "
            "Returns agent_role or null if insufficient data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "description": "Task type: research, coding, math, creative, comparison, planning, summarization, translation, general",
                },
            },
            "required": ["task_type"],
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

# ── Inter-Agent Communication Tools ──────────────────────────────

SEND_AGENT_MESSAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "send_agent_message",
        "description": (
            "Send a message to another agent for collaboration or task delegation. "
            "Use when you need help from another agent, want to delegate a subtask, "
            "or need to share important findings with the team. "
            "Available agents: orchestrator, thinker, researcher, speed, reasoner, critic"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to_agent": {
                    "type": "string",
                    "description": "Target agent role (orchestrator, thinker, researcher, speed, reasoner, critic) or 'broadcast' for all",
                },
                "content": {
                    "type": "string",
                    "description": "Message content - be specific about what you need",
                },
                "message_type": {
                    "type": "string",
                    "enum": ["direct", "collab_request", "task_delegation", "alert"],
                    "description": "Type of message: direct=simple message, collab_request=ask for help, task_delegation=delegate subtask, alert=important notification",
                },
                "requires_response": {
                    "type": "boolean",
                    "description": "Whether you expect a response from the target agent",
                },
                "context": {
                    "type": "object",
                    "description": "Additional context for collaboration requests",
                },
            },
            "required": ["to_agent", "content"],
        },
    },
}

CHECK_AGENT_MESSAGES_TOOL = {
    "type": "function",
    "function": {
        "name": "check_agent_messages",
        "description": (
            "Check for pending messages from other agents. "
            "Use to see if other agents have sent you collaboration requests, "
            "task delegations, or important notifications."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}

SHARE_KNOWLEDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "share_knowledge",
        "description": (
            "Share knowledge with all agents in the team. "
            "Use when you discover something useful that other agents should know. "
            "Examples: user preferences, important findings, context about the task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Knowledge key (e.g. 'user_preference_theme', 'important_finding_1')",
                },
                "value": {
                    "description": "Knowledge value (any type)",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization (e.g. ['preference', 'user'], ['finding', 'research'])",
                },
            },
            "required": ["key", "value"],
        },
    },
}

GET_SHARED_KNOWLEDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_shared_knowledge",
        "description": (
            "Get knowledge shared by other agents. "
            "Use to access team knowledge before starting your task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Knowledge key to retrieve (omit to get all shared knowledge)",
                },
            },
        },
    },
}

SUGGEST_COLLABORATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "suggest_collaborator",
        "description": (
            "Get a suggestion for which agent to collaborate with based on task type. "
            "Use when you need help but aren't sure which agent to ask."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "enum": ["research", "analysis", "code", "math", "review", "planning", "verification"],
                    "description": "Type of task you need help with",
                },
            },
            "required": ["task_type"],
        },
    },
}

# Inter-agent tools combined
INTER_AGENT_TOOLS = [
    SEND_AGENT_MESSAGE_TOOL,
    CHECK_AGENT_MESSAGES_TOOL,
    SHARE_KNOWLEDGE_TOOL,
    GET_SHARED_KNOWLEDGE_TOOL,
    SUGGEST_COLLABORATOR_TOOL,
]

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

GENERATE_CHART_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_chart",
        "description": (
            "Generate a chart/graph from structured data using matplotlib. "
            "Supports bar, line, pie, scatter, histogram, area, heatmap chart types. "
            "Returns a base64-encoded PNG image. Use when the user asks for data visualization, "
            "charts, graphs, or when analysis results should be presented visually."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "histogram", "area", "heatmap"],
                    "description": "Type of chart to generate",
                },
                "data": {
                    "type": "object",
                    "description": (
                        "Chart data. For bar/line/area: {labels: [...], values: [...]} or {labels: [...], datasets: [{label, values}]}. "
                        "For pie: {labels: [...], values: [...]}. For scatter: {x: [...], y: [...]}. "
                        "For histogram: {values: [...], bins: 20}. For heatmap: {matrix: [[...]], xlabels, ylabels}."
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
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
            "required": ["chart_type", "data"],
        },
    },
}

# ── OCR Tool ──────────────────────────────────────────────────────

OCR_TOOL = {
    "type": "function",
    "function": {
        "name": "ocr_extract",
        "description": (
            "Extract text from images (PNG, JPG, WEBP) and PDFs using OCR. "
            "Uses Tesseract/pytesseract for image OCR and pdfplumber for PDF text extraction. "
            "Use when the user provides an image or PDF and wants to extract, read, or analyze its text content. "
            "Supports multiple languages (eng, tur, deu, fra, spa, etc.). "
            "Returns extracted text with character count, word count, and confidence score."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the image or PDF file on disk",
                },
                "file_bytes": {
                    "type": "string",
                    "description": "Base64-encoded file content (alternative to file_path)",
                },
                "filename": {
                    "type": "string",
                    "description": "Original filename (required if using file_bytes)",
                },
                "lang": {
                    "type": "string",
                    "description": "Language code for OCR: eng (English), tur (Turkish), deu (German), fra (French), spa (Spanish), etc.",
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific PDF pages to extract (1-indexed, e.g., [1, 2, 5])",
                },
                "extract_tables": {
                    "type": "boolean",
                    "description": "Extract tables from PDFs as structured data (default: false)",
                },
                "save_output": {
                    "type": "boolean",
                    "description": "Save extracted text to a file (default: false)",
                },
            },
        },
    },
}

OCR_STATUS_TOOL = {
    "type": "function",
    "function": {
        "name": "ocr_status",
        "description": (
            "Check OCR service status and capabilities. "
            "Returns information about installed dependencies, supported formats, and available languages. "
            "Use before ocr_extract to verify OCR is available."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}

# ── Webhook System Tools ──────────────────────────────────────────

WEBHOOK_SUBSCRIBE_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_subscribe",
        "description": (
            "Create a webhook subscription to receive events at an external URL. "
            "The system will POST event data to the specified URL when matching events occur. "
            "Supports signature verification (HMAC-SHA256), custom headers, and event filtering. "
            "Use to integrate with external systems (CI/CD, monitoring, Slack, custom backends)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Subscription name (e.g., 'CI Pipeline Notifier', 'Slack Integration')",
                },
                "url": {
                    "type": "string",
                    "description": "Webhook URL to receive POST requests (must be HTTPS in production)",
                },
                "events": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Event types to subscribe to (e.g., ['agent.task.complete', 'workflow.completed'])",
                },
                "secret": {
                    "type": "string",
                    "description": "Optional secret for HMAC-SHA256 signature (auto-generated if omitted)",
                },
                "filters": {
                    "type": "object",
                    "description": "Optional filters: only trigger when payload matches these key-value pairs",
                },
                "headers": {
                    "type": "object",
                    "description": "Optional custom headers to include in webhook requests",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["name", "url", "events"],
        },
    },
}

WEBHOOK_UNSUBSCRIBE_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_unsubscribe",
        "description": (
            "Delete a webhook subscription. "
            "No more events will be sent to the subscribed URL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "subscription_id": {
                    "type": "string",
                    "description": "Subscription ID to delete",
                },
            },
            "required": ["subscription_id"],
        },
    },
}

WEBHOOK_LIST_SUBSCRIPTIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_list_subscriptions",
        "description": (
            "List all webhook subscriptions with optional filters. "
            "Use to see what webhooks are configured and their status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "disabled"],
                    "description": "Filter by subscription status",
                },
                "event_type": {
                    "type": "string",
                    "description": "Filter by event type (subscriptions that include this event)",
                },
            },
        },
    },
}

WEBHOOK_TRIGGER_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_trigger",
        "description": (
            "Manually trigger a webhook event to all matching subscriptions. "
            "Use for testing webhooks or triggering external integrations. "
            "The event will be dispatched to all active subscriptions that subscribe to this event type."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "Event type to trigger (e.g., 'agent.task.complete', 'custom.event')",
                },
                "data": {
                    "type": "object",
                    "description": "Event data payload to send",
                },
                "source": {
                    "type": "string",
                    "description": "Source identifier (default: 'agent')",
                },
            },
            "required": ["event_type", "data"],
        },
    },
}

WEBHOOK_SEND_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_send",
        "description": (
            "Send a one-time webhook POST request to an external URL. "
            "Includes HMAC-SHA256 signature for verification by the receiver. "
            "Use for ad-hoc integrations without creating a subscription."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target webhook URL",
                },
                "payload": {
                    "type": "object",
                    "description": "JSON payload to send",
                },
                "secret": {
                    "type": "string",
                    "description": "Secret for HMAC signature (required for verification)",
                },
                "headers": {
                    "type": "object",
                    "description": "Additional headers to include",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["url", "payload", "secret"],
        },
    },
}

WEBHOOK_RECEIVE_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_receive",
        "description": (
            "Receive and log an incoming webhook with optional signature verification. "
            "Use when external systems send webhooks to this platform. "
            "Returns verification status and logs the webhook for processing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source identifier (e.g., 'github', 'stripe', 'custom')",
                },
                "payload": {
                    "type": "object",
                    "description": "Webhook payload received",
                },
                "headers": {
                    "type": "object",
                    "description": "Request headers from the webhook",
                    "additionalProperties": {"type": "string"},
                },
                "signature": {
                    "type": "string",
                    "description": "Signature header value (e.g., X-Hub-Signature-256)",
                },
                "expected_secret": {
                    "type": "string",
                    "description": "Secret to verify signature (if signature is provided)",
                },
                "event_type": {
                    "type": "string",
                    "description": "Event type extracted from payload (optional)",
                },
            },
            "required": ["source", "payload"],
        },
    },
}

WEBHOOK_DELIVERY_HISTORY_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_delivery_history",
        "description": (
            "Get webhook delivery history with optional filters. "
            "Use to debug webhook issues, check delivery status, or retry failed deliveries."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "subscription_id": {
                    "type": "string",
                    "description": "Filter by subscription ID",
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "delivered", "failed", "retrying"],
                    "description": "Filter by delivery status",
                },
                "event_type": {
                    "type": "string",
                    "description": "Filter by event type",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default 50)",
                },
            },
        },
    },
}

WEBHOOK_RETRY_DELIVERY_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_retry_delivery",
        "description": (
            "Retry a failed webhook delivery. "
            "Use when a webhook delivery failed and you want to attempt redelivery."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "delivery_id": {
                    "type": "string",
                    "description": "Delivery ID to retry",
                },
            },
            "required": ["delivery_id"],
        },
    },
}

WEBHOOK_STATS_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_stats",
        "description": (
            "Get webhook system statistics. "
            "Returns counts of subscriptions, deliveries, incoming webhooks, and success rates."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}

WEBHOOK_PAUSE_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_pause",
        "description": (
            "Pause a webhook subscription (stop sending webhooks temporarily). "
            "Use when the target endpoint is down or during maintenance."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "subscription_id": {
                    "type": "string",
                    "description": "Subscription ID to pause",
                },
            },
            "required": ["subscription_id"],
        },
    },
}

WEBHOOK_RESUME_TOOL = {
    "type": "function",
    "function": {
        "name": "webhook_resume",
        "description": (
            "Resume a paused webhook subscription. "
            "Webhooks will be sent to the subscription URL again."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "subscription_id": {
                    "type": "string",
                    "description": "Subscription ID to resume",
                },
            },
            "required": ["subscription_id"],
        },
    },
}

# Webhook tools combined
WEBHOOK_TOOLS = [
    WEBHOOK_SUBSCRIBE_TOOL,
    WEBHOOK_UNSUBSCRIBE_TOOL,
    WEBHOOK_LIST_SUBSCRIPTIONS_TOOL,
    WEBHOOK_TRIGGER_TOOL,
    WEBHOOK_SEND_TOOL,
    WEBHOOK_RECEIVE_TOOL,
    WEBHOOK_DELIVERY_HISTORY_TOOL,
    WEBHOOK_RETRY_DELIVERY_TOOL,
    WEBHOOK_STATS_TOOL,
    WEBHOOK_PAUSE_TOOL,
    WEBHOOK_RESUME_TOOL,
]

# ── Email Sender Tools ─────────────────────────────────────────────

EMAIL_SEND_TOOL = {
    "type": "function",
    "function": {
        "name": "email_send",
        "description": (
            "Send an email via SMTP. Supports HTML and plain text, CC/BCC, attachments, "
            "and custom headers. Works with Gmail, Outlook, Yahoo, and custom SMTP servers. "
            "Use for sending notifications, reports, alerts, or any email communication. "
            "For Gmail/Outlook, use App Passwords instead of regular passwords."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "smtp_host": {
                    "type": "string",
                    "description": "SMTP server hostname (e.g., 'smtp.gmail.com', 'smtp.office365.com')",
                },
                "smtp_port": {
                    "type": "integer",
                    "description": "SMTP port (default: 587 for TLS, 465 for SSL)",
                },
                "smtp_user": {
                    "type": "string",
                    "description": "SMTP username (usually email address)",
                },
                "smtp_password": {
                    "type": "string",
                    "description": "SMTP password or App Password for Gmail/Outlook",
                },
                "use_tls": {
                    "type": "boolean",
                    "description": "Use STARTTLS (default: true)",
                },
                "use_ssl": {
                    "type": "boolean",
                    "description": "Use SMTP over SSL (default: false, use for port 465)",
                },
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Recipient email address(es)",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                },
                "body": {
                    "type": "string",
                    "description": "Plain text body (optional if html_body provided)",
                },
                "html_body": {
                    "type": "string",
                    "description": "HTML body for rich formatting (optional)",
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CC recipient(s) (optional)",
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "BCC recipient(s) (optional)",
                },
                "reply_to": {
                    "type": "string",
                    "description": "Reply-to email address (optional)",
                },
                "from_name": {
                    "type": "string",
                    "description": "Display name for sender (optional)",
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "Attachment filename"},
                            "file_path": {"type": "string", "description": "Path to file on disk"},
                            "content_base64": {"type": "string", "description": "Base64-encoded file content"},
                            "content_type": {"type": "string", "description": "MIME type (auto-detected from filename)"},
                        },
                    },
                    "description": "File attachments (optional)",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high"],
                    "description": "Email priority (default: normal)",
                },
            },
            "required": ["smtp_host", "smtp_user", "smtp_password", "to", "subject"],
        },
    },
}

EMAIL_SEND_TEMPLATE_TOOL = {
    "type": "function",
    "function": {
        "name": "email_send_template",
        "description": (
            "Send an email using a pre-defined template. Templates support variable substitution. "
            "Built-in templates: 'welcome', 'password_reset', 'notification', 'weekly_report', 'simple'. "
            "Use for common email patterns like welcome emails, password resets, notifications. "
            "Templates automatically handle HTML and plain text versions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "smtp_host": {
                    "type": "string",
                    "description": "SMTP server hostname",
                },
                "smtp_port": {
                    "type": "integer",
                    "description": "SMTP port (default: 587)",
                },
                "smtp_user": {
                    "type": "string",
                    "description": "SMTP username",
                },
                "smtp_password": {
                    "type": "string",
                    "description": "SMTP password or App Password",
                },
                "use_tls": {
                    "type": "boolean",
                    "description": "Use STARTTLS (default: true)",
                },
                "use_ssl": {
                    "type": "boolean",
                    "description": "Use SMTP over SSL (default: false)",
                },
                "template_name": {
                    "type": "string",
                    "description": "Template name: welcome, password_reset, notification, weekly_report, simple",
                    "enum": ["welcome", "password_reset", "notification", "weekly_report", "simple"],
                },
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Recipient email address(es)",
                },
                "variables": {
                    "type": "object",
                    "description": "Template variables to substitute (e.g., {'user_name': 'John', 'company_name': 'Acme'})",
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CC recipient(s) (optional)",
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "BCC recipient(s) (optional)",
                },
                "from_name": {
                    "type": "string",
                    "description": "Display name for sender (optional)",
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "file_path": {"type": "string"},
                            "content_base64": {"type": "string"},
                        },
                    },
                    "description": "File attachments (optional)",
                },
            },
            "required": ["smtp_host", "smtp_user", "smtp_password", "template_name", "to", "variables"],
        },
    },
}

EMAIL_LIST_TEMPLATES_TOOL = {
    "type": "function",
    "function": {
        "name": "email_list_templates",
        "description": (
            "List available email templates and their variables. "
            "Use to discover which templates exist and what variables they require."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}

EMAIL_TEST_SMTP_TOOL = {
    "type": "function",
    "function": {
        "name": "email_test_smtp",
        "description": (
            "Test SMTP connection without sending an email. "
            "Use to verify SMTP credentials before sending important emails. "
            "Returns connection status and server info."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "smtp_host": {
                    "type": "string",
                    "description": "SMTP server hostname",
                },
                "smtp_port": {
                    "type": "integer",
                    "description": "SMTP port (default: 587)",
                },
                "smtp_user": {
                    "type": "string",
                    "description": "SMTP username",
                },
                "smtp_password": {
                    "type": "string",
                    "description": "SMTP password or App Password",
                },
                "use_tls": {
                    "type": "boolean",
                    "description": "Use STARTTLS (default: true)",
                },
                "use_ssl": {
                    "type": "boolean",
                    "description": "Use SMTP over SSL (default: false)",
                },
            },
            "required": ["smtp_host", "smtp_user", "smtp_password"],
        },
    },
}

# ── Workflow Engine Tools ─────────────────────────────────────────

RUN_WORKFLOW_TOOL = {
    "type": "function",
    "function": {
        "name": "run_workflow",
        "description": (
            "Execute a multi-step workflow with conditional branching, parallel execution, "
            "error handling, and rollback. Use for complex multi-tool chains that need "
            "orchestrated execution. Available templates: research-and-report, code-review-pipeline, deep-analysis. "
            "Can also run custom workflows by providing steps directly."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "description": "Workflow template name (research-and-report, code-review-pipeline, deep-analysis) or 'custom'",
                },
                "variables": {
                    "type": "object",
                    "description": "Variables to inject into the workflow (e.g. {'topic': 'AI trends', 'language': 'tr'})",
                },
                "custom_steps": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Custom workflow steps (only when template='custom')",
                },
            },
            "required": ["template", "variables"],
        },
    },
}

LIST_WORKFLOWS_TOOL = {
    "type": "function",
    "function": {
        "name": "list_workflows",
        "description": "List available workflow templates and recent workflow execution results.",
        "parameters": {
            "type": "object",
            "properties": {
                "include_history": {
                    "type": "boolean",
                    "description": "Include recent execution history (default false)",
                },
            },
        },
    },
}

# ── Domain Expert Tools ──────────────────────────────────────────

DOMAIN_EXPERT_TOOL = {
    "type": "function",
    "function": {
        "name": "domain_expert",
        "description": (
            "Access specialized domain expertise for calculations and analysis. "
            "Domains: finance (DCF, NPV, IRR, WACC, ratios), legal (contract analysis, KVKK/GDPR), "
            "engineering (system design, load estimation, architecture), academic (literature review, methodology). "
            "Use when a task requires domain-specific calculations or structured analysis."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "enum": ["finance", "legal", "engineering", "academic"],
                    "description": "Domain area",
                },
                "tool_name": {
                    "type": "string",
                    "description": "Specific tool within the domain (e.g. 'calculate_dcf', 'check_kvkk_compliance')",
                },
                "arguments": {
                    "type": "object",
                    "description": "Tool-specific arguments",
                },
            },
            "required": ["domain", "tool_name", "arguments"],
        },
    },
}

LIST_DOMAIN_TOOLS_TOOL = {
    "type": "function",
    "function": {
        "name": "list_domain_tools",
        "description": "List available domain expertise tools and their capabilities. Use to discover what domain-specific calculations and analyses are available.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "enum": ["finance", "legal", "engineering", "academic"],
                    "description": "Optional: filter by specific domain",
                },
            },
        },
    },
}

# ── Budget Check Tool ─────────────────────────────────────────────

CHECK_BUDGET_TOOL = {
    "type": "function",
    "function": {
        "name": "check_budget",
        "description": (
            "Check current API cost budget status before expensive operations. "
            "Returns remaining budget, current spend, and whether the operation is within limits. "
            "Use proactively before spawning multiple sub-agents or running large workflows."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Time window in hours to check (default 24)",
                },
            },
        },
    },
}

# ── Error Pattern Check Tool ─────────────────────────────────────

CHECK_ERROR_PATTERNS_TOOL = {
    "type": "function",
    "function": {
        "name": "check_error_patterns",
        "description": (
            "Check for known recurring error patterns and get recommendations. "
            "Use when encountering errors to see if they match known patterns, "
            "or proactively before starting tasks to be aware of current system issues."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Time window in hours to analyze (default 24)",
                },
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Filter by minimum severity (optional)",
                },
            },
        },
    },
}

# ── Self-Managing Workspace Tools (pi-mom inspired) ──────────────

WORKSPACE_CREATE_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "workspace_create_skill",
        "description": (
            "Create an executable skill (script + docs) in your agent workspace. "
            "Unlike create_skill which stores knowledge, this creates RUNNABLE scripts "
            "that you can execute later. Inspired by pi-mom's self-managing tools. "
            "Example: create a data-analyzer skill with a Python script that processes CSV files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Kebab-case skill name (e.g. 'data-analyzer', 'log-parser')",
                },
                "description": {
                    "type": "string",
                    "description": "What this skill does",
                },
                "usage_instructions": {
                    "type": "string",
                    "description": "Markdown instructions on how to use the skill",
                },
                "scripts": {
                    "type": "object",
                    "description": "Script files: {'main.py': 'code', 'helper.sh': 'code'}",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["skill_name", "description", "scripts"],
        },
    },
}

WORKSPACE_RUN_SCRIPT_TOOL = {
    "type": "function",
    "function": {
        "name": "workspace_run_script",
        "description": (
            "Execute a script from your workspace skills. "
            "Runs in a sandboxed subprocess with timeout protection. "
            "Use after workspace_create_skill to run the tools you created."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Skill name containing the script",
                },
                "script_name": {
                    "type": "string",
                    "description": "Script filename to execute (e.g. 'main.py')",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command-line arguments to pass",
                },
                "stdin_data": {
                    "type": "string",
                    "description": "Data to pipe to stdin",
                },
            },
            "required": ["skill_name", "script_name"],
        },
    },
}

WORKSPACE_LIST_SKILLS_TOOL = {
    "type": "function",
    "function": {
        "name": "workspace_list_skills",
        "description": "List all executable skills in your agent workspace.",
        "parameters": {"type": "object", "properties": {}},
    },
}

WORKSPACE_SCRATCH_WRITE_TOOL = {
    "type": "function",
    "function": {
        "name": "workspace_scratch_write",
        "description": (
            "Write a file to your scratch space for intermediate work. "
            "Use for temp data, intermediate results, or working files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename to write"},
                "content": {"type": "string", "description": "File content"},
            },
            "required": ["filename", "content"],
        },
    },
}

WORKSPACE_SCRATCH_READ_TOOL = {
    "type": "function",
    "function": {
        "name": "workspace_scratch_read",
        "description": "Read a file from your scratch space.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename to read"},
            },
            "required": ["filename"],
        },
    },
}

# Workspace tools combined
WORKSPACE_TOOLS = [
    WORKSPACE_CREATE_SKILL_TOOL,
    WORKSPACE_RUN_SCRIPT_TOOL,
    WORKSPACE_LIST_SKILLS_TOOL,
    WORKSPACE_SCRATCH_WRITE_TOOL,
    WORKSPACE_SCRATCH_READ_TOOL,
]

# ── Agent Event Tools (pi-mom inspired) ──────────────────────────

AGENT_EVENT_CREATE_TOOL = {
    "type": "function",
    "function": {
        "name": "agent_event_create",
        "description": (
            "Create a scheduled event that wakes up an agent. Three types: "
            "immediate (triggers now), one-shot (triggers at specific time, auto-deletes), "
            "periodic (triggers on cron schedule, persists). "
            "Use for reminders, periodic checks, or triggering agent actions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "enum": ["immediate", "one-shot", "periodic"],
                    "description": "Event type",
                },
                "target_agent": {
                    "type": "string",
                    "enum": ["orchestrator", "thinker", "researcher", "reasoner", "speed", "critic"],
                    "description": "Which agent to wake up",
                },
                "message": {
                    "type": "string",
                    "description": "Message/instruction for the agent when triggered",
                },
                "schedule": {
                    "type": "string",
                    "description": "Cron expression for periodic events (e.g. '0 9 * * 1-5' for weekdays at 9am)",
                },
                "trigger_at": {
                    "type": "string",
                    "description": "ISO datetime for one-shot events (e.g. '2026-03-15T09:00:00+03:00')",
                },
            },
            "required": ["event_type", "target_agent", "message"],
        },
    },
}

AGENT_EVENT_LIST_TOOL = {
    "type": "function",
    "function": {
        "name": "agent_event_list",
        "description": "List active agent events with optional filters.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_agent": {
                    "type": "string",
                    "description": "Filter by target agent",
                },
            },
        },
    },
}

AGENT_EVENT_DELETE_TOOL = {
    "type": "function",
    "function": {
        "name": "agent_event_delete",
        "description": "Delete a scheduled agent event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Event ID to delete"},
            },
            "required": ["event_id"],
        },
    },
}

# Agent event tools combined
AGENT_EVENT_TOOLS = [
    AGENT_EVENT_CREATE_TOOL,
    AGENT_EVENT_LIST_TOOL,
    AGENT_EVENT_DELETE_TOOL,
]

# ── Context Search Tool (pi-mom's grep on log.jsonl) ─────────────

SEARCH_THREAD_HISTORY_TOOL = {
    "type": "function",
    "function": {
        "name": "search_thread_history",
        "description": (
            "Search through full thread event history for older context. "
            "Like grepping through conversation logs when the current context "
            "has been compacted. Use when you need to recall something from "
            "earlier in the conversation that may have been summarized away."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term (case-insensitive)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                },
            },
            "required": ["query"],
        },
    },
}

# ── Orchestrator Tools ───────────────────────────────────────────

ORCHESTRATOR_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    YOUTUBE_SUMMARIZER_TOOL,
    YOUTUBE_TRANSCRIPT_TOOL,
    SAVE_MEMORY_TOOL,
    RECALL_MEMORY_TOOL,
    LIST_MEMORIES_TOOL,
    MEMORY_STATS_TOOL,
    {
        "type": "function",
        "function": {
            "name": "decompose_task",
            "description": "Break a complex user request into sub-tasks and assign each to a specialist agent. With 2+ sub-tasks, ALL run at the same time (multiparallel).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sub_tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {
                                    "type": "string",
                                    "description": "What this sub-task should accomplish",
                                },
                                "assigned_agent": {
                                    "type": "string",
                                    "enum": [
                                        "thinker",
                                        "speed",
                                        "researcher",
                                        "reasoner",
                                        "critic",
                                    ],
                                    "description": "Which specialist agent to assign",
                                },
                                "priority": {
                                    "type": "integer",
                                    "description": "1=highest priority",
                                },
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
                        "enum": [
                            "sequential",
                            "parallel",
                            "consensus",
                            "iterative",
                            "deep_research",
                        ],
                        "description": "With 2+ sub-tasks they always run in parallel (same time). Use 'parallel' or 'deep_research' for multi-agent work.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this decomposition and pipeline",
                    },
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
                    "response": {
                        "type": "string",
                        "description": "Direct answer to the user",
                    },
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
                    "final_response": {
                        "type": "string",
                        "description": "Synthesized final answer",
                    },
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
    RAG_LIST_DOCUMENTS_TOOL,
    LIST_TEACHINGS_TOOL,
    IDEA_TO_PROJECT_TOOL,
    SPAWN_SUBAGENT_TOOL,
    REQUEST_APPROVAL_TOOL,
    GET_AGENT_BASELINE_TOOL,
    GET_BEST_AGENT_TOOL,
    SELF_EVALUATE_TOOL,
    MCP_CALL_TOOL,
    MCP_LIST_TOOLS_TOOL,
    CREATE_SKILL_TOOL,
    RESEARCH_CREATE_SKILL_TOOL,
    GENERATE_IMAGE_TOOL,
    GENERATE_CHART_TOOL,
    OCR_TOOL,
    OCR_STATUS_TOOL,
    RUN_WORKFLOW_TOOL,
    LIST_WORKFLOWS_TOOL,
    DOMAIN_EXPERT_TOOL,
    LIST_DOMAIN_TOOLS_TOOL,
    CHECK_BUDGET_TOOL,
    CHECK_ERROR_PATTERNS_TOOL,
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
    # Email Tools
    EMAIL_SEND_TOOL,
    EMAIL_SEND_TEMPLATE_TOOL,
    EMAIL_LIST_TEMPLATES_TOOL,
    EMAIL_TEST_SMTP_TOOL,
    # Inter-Agent Communication
    SEND_AGENT_MESSAGE_TOOL,
    CHECK_AGENT_MESSAGES_TOOL,
    SHARE_KNOWLEDGE_TOOL,
    GET_SHARED_KNOWLEDGE_TOOL,
    SUGGEST_COLLABORATOR_TOOL,
    # Self-Managing Workspace (pi-mom inspired)
    *WORKSPACE_TOOLS,
    # Agent Events (pi-mom inspired)
    *AGENT_EVENT_TOOLS,
    # Context History Search
    SEARCH_THREAD_HISTORY_TOOL,
]

# ── Researcher Tools ─────────────────────────────────────────────

RESEARCHER_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    YOUTUBE_SUMMARIZER_TOOL,
    YOUTUBE_TRANSCRIPT_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    LIST_MEMORIES_TOOL,
    MEMORY_STATS_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
    CREATE_SKILL_TOOL,
    RAG_QUERY_TOOL,
    RAG_LIST_DOCUMENTS_TOOL,
    LIST_TEACHINGS_TOOL,
    GENERATE_IMAGE_TOOL,
    GENERATE_CHART_TOOL,
    OCR_TOOL,
    OCR_STATUS_TOOL,
    DOMAIN_EXPERT_TOOL,
    LIST_DOMAIN_TOOLS_TOOL,
    MCP_CALL_TOOL,
    MCP_LIST_TOOLS_TOOL,
    # Email Tools
    EMAIL_SEND_TOOL,
    EMAIL_SEND_TEMPLATE_TOOL,
    EMAIL_LIST_TEMPLATES_TOOL,
    EMAIL_TEST_SMTP_TOOL,
    # Inter-Agent Communication
    SEND_AGENT_MESSAGE_TOOL,
    CHECK_AGENT_MESSAGES_TOOL,
    SHARE_KNOWLEDGE_TOOL,
    GET_SHARED_KNOWLEDGE_TOOL,
    SUGGEST_COLLABORATOR_TOOL,
    # Self-Managing Workspace
    *WORKSPACE_TOOLS,
    SEARCH_THREAD_HISTORY_TOOL,
]

# ── Thinker Tools ────────────────────────────────────────────────

THINKER_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    YOUTUBE_TRANSCRIPT_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    LIST_MEMORIES_TOOL,
    MEMORY_STATS_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
    CREATE_SKILL_TOOL,
    RAG_QUERY_TOOL,
    RAG_LIST_DOCUMENTS_TOOL,
    LIST_TEACHINGS_TOOL,
    GET_AGENT_BASELINE_TOOL,
    GENERATE_IMAGE_TOOL,
    GENERATE_CHART_TOOL,
    OCR_TOOL,
    OCR_STATUS_TOOL,
    DOMAIN_EXPERT_TOOL,
    LIST_DOMAIN_TOOLS_TOOL,
    MCP_CALL_TOOL,
    MCP_LIST_TOOLS_TOOL,
    # Email Tools
    EMAIL_SEND_TOOL,
    EMAIL_SEND_TEMPLATE_TOOL,
    EMAIL_LIST_TEMPLATES_TOOL,
    EMAIL_TEST_SMTP_TOOL,
    # Inter-Agent Communication
    SEND_AGENT_MESSAGE_TOOL,
    CHECK_AGENT_MESSAGES_TOOL,
    SHARE_KNOWLEDGE_TOOL,
    GET_SHARED_KNOWLEDGE_TOOL,
    SUGGEST_COLLABORATOR_TOOL,
    # Self-Managing Workspace
    *WORKSPACE_TOOLS,
    SEARCH_THREAD_HISTORY_TOOL,
]

# ── Speed Tools ──────────────────────────────────────────────────

SPEED_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    YOUTUBE_TRANSCRIPT_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    LIST_MEMORIES_TOOL,
    MEMORY_STATS_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
    CREATE_SKILL_TOOL,
    CODE_EXECUTE_TOOL,
    RAG_QUERY_TOOL,
    RAG_LIST_DOCUMENTS_TOOL,
    LIST_TEACHINGS_TOOL,
    GENERATE_IMAGE_TOOL,
    GENERATE_CHART_TOOL,
    OCR_TOOL,
    OCR_STATUS_TOOL,
    DOMAIN_EXPERT_TOOL,
    LIST_DOMAIN_TOOLS_TOOL,
    MCP_CALL_TOOL,
    MCP_LIST_TOOLS_TOOL,
    # Email Tools
    EMAIL_SEND_TOOL,
    EMAIL_SEND_TEMPLATE_TOOL,
    EMAIL_LIST_TEMPLATES_TOOL,
    EMAIL_TEST_SMTP_TOOL,
    # Inter-Agent Communication
    SEND_AGENT_MESSAGE_TOOL,
    CHECK_AGENT_MESSAGES_TOOL,
    SHARE_KNOWLEDGE_TOOL,
    GET_SHARED_KNOWLEDGE_TOOL,
    SUGGEST_COLLABORATOR_TOOL,
    # Self-Managing Workspace
    *WORKSPACE_TOOLS,
    SEARCH_THREAD_HISTORY_TOOL,
]

# ── Reasoner Tools ───────────────────────────────────────────────

REASONER_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    YOUTUBE_TRANSCRIPT_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    LIST_MEMORIES_TOOL,
    MEMORY_STATS_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
    CREATE_SKILL_TOOL,
    CODE_EXECUTE_TOOL,
    RAG_QUERY_TOOL,
    RAG_LIST_DOCUMENTS_TOOL,
    LIST_TEACHINGS_TOOL,
    GENERATE_IMAGE_TOOL,
    GENERATE_CHART_TOOL,
    OCR_TOOL,
    OCR_STATUS_TOOL,
    DOMAIN_EXPERT_TOOL,
    LIST_DOMAIN_TOOLS_TOOL,
    MCP_CALL_TOOL,
    MCP_LIST_TOOLS_TOOL,
    # Email Tools
    EMAIL_SEND_TOOL,
    EMAIL_SEND_TEMPLATE_TOOL,
    EMAIL_LIST_TEMPLATES_TOOL,
    EMAIL_TEST_SMTP_TOOL,
    # Inter-Agent Communication
    SEND_AGENT_MESSAGE_TOOL,
    CHECK_AGENT_MESSAGES_TOOL,
    SHARE_KNOWLEDGE_TOOL,
    GET_SHARED_KNOWLEDGE_TOOL,
    SUGGEST_COLLABORATOR_TOOL,
    # Self-Managing Workspace
    *WORKSPACE_TOOLS,
    SEARCH_THREAD_HISTORY_TOOL,
]

# ── Critic Tools (DeepSeek) ────────────────────────────────────────

CRITIC_TOOLS = [
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    YOUTUBE_TRANSCRIPT_TOOL,
    FIND_SKILL_TOOL,
    USE_SKILL_TOOL,
    RAG_QUERY_TOOL,
    RAG_LIST_DOCUMENTS_TOOL,
    CODE_EXECUTE_TOOL,
    RECALL_MEMORY_TOOL,
    SAVE_MEMORY_TOOL,
    LIST_MEMORIES_TOOL,
    MEMORY_STATS_TOOL,
    LIST_TEACHINGS_TOOL,
    GENERATE_IMAGE_TOOL,
    GENERATE_CHART_TOOL,
    OCR_TOOL,
    OCR_STATUS_TOOL,
    DOMAIN_EXPERT_TOOL,
    LIST_DOMAIN_TOOLS_TOOL,
    MCP_CALL_TOOL,
    MCP_LIST_TOOLS_TOOL,
    # Email Tools
    EMAIL_SEND_TOOL,
    EMAIL_SEND_TEMPLATE_TOOL,
    EMAIL_LIST_TEMPLATES_TOOL,
    EMAIL_TEST_SMTP_TOOL,
    # Inter-Agent Communication
    SEND_AGENT_MESSAGE_TOOL,
    CHECK_AGENT_MESSAGES_TOOL,
    SHARE_KNOWLEDGE_TOOL,
    GET_SHARED_KNOWLEDGE_TOOL,
    SUGGEST_COLLABORATOR_TOOL,
    # Self-Managing Workspace
    *WORKSPACE_TOOLS,
    SEARCH_THREAD_HISTORY_TOOL,
]

# ── Agent → Tools Mapping ────────────────────────────────────────

AGENT_TOOLS: dict[str, list[dict[str, Any]]] = {
    "orchestrator": ORCHESTRATOR_TOOLS,
    "thinker": THINKER_TOOLS,
    "speed": SPEED_TOOLS,
    "researcher": RESEARCHER_TOOLS,
    "reasoner": REASONER_TOOLS,
    "critic": CRITIC_TOOLS,
}
