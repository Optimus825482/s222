"""
Tool Call Sandbox — validates and restricts agent tool calls.

Prevents dangerous operations by enforcing:
- Allowlisted tool names per agent role
- Argument validation (no path traversal, no shell injection)
- Rate limiting per tool per agent
- Audit logging of all tool calls

Usage:
    from tools.sandbox import validate_tool_call, SandboxViolation

    try:
        validate_tool_call("researcher", "code_execute", {"code": "import os; os.system('rm -rf /')"})
    except SandboxViolation as e:
        print(f"Blocked: {e}")
"""

from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sandbox")

# ── Exceptions ───────────────────────────────────────────────────


class SandboxViolation(Exception):
    """Raised when a tool call violates sandbox policy."""

    def __init__(self, tool: str, reason: str, severity: str = "high"):
        self.tool = tool
        self.reason = reason
        self.severity = severity
        super().__init__(f"[Sandbox:{severity}] {tool}: {reason}")


# ── Policy Configuration ─────────────────────────────────────────

# Tools each agent role is allowed to call
ROLE_ALLOWLIST: dict[str, set[str]] = {
    "orchestrator": {
        "web_search",
        "web_fetch",
        "save_memory",
        "recall_memory",
        "list_memories",
        "memory_stats",
        "find_skill",
        "use_skill",
        "rag_query",
        "rag_ingest",
        "rag_list_documents",
        "list_teachings",
        "request_approval",
        "spawn_subagent",
        "send_agent_message",
        "check_agent_messages",
        "get_agent_baseline",
        "get_best_agent",
        "self_evaluate",
        "mcp_call",
        "mcp_list_tools",
        "generate_image",
        "generate_chart",
        "create_skill",
        "code_execute",
        # Orchestrator-specific tools
        "decompose_task",
        "direct_response",
        "research_create_skill",
        "generate_presentation",
        "check_error_patterns",
        "check_budget",
        # Self-Managing Workspace (pi-mom inspired)
        "workspace_create_skill",
        "workspace_run_script",
        "workspace_list_skills",
        "workspace_scratch_write",
        "workspace_scratch_read",
        # Agent Events (pi-mom inspired)
        "agent_event_create",
        "agent_event_list",
        "agent_event_delete",
        # Context History Search
        "search_thread_history",
    },
    "thinker": {
        "web_search",
        "web_fetch",
        "save_memory",
        "recall_memory",
        "find_skill",
        "use_skill",
        "rag_query",
        "code_execute",
        "self_evaluate",
        "mcp_call",
        "mcp_list_tools",
        "generate_image",
        "generate_chart",
        "workspace_create_skill",
        "workspace_run_script",
        "workspace_list_skills",
        "workspace_scratch_write",
        "workspace_scratch_read",
        "search_thread_history",
    },
    "speed": {
        "web_search",
        "web_fetch",
        "save_memory",
        "recall_memory",
        "find_skill",
        "use_skill",
        "rag_query",
        "code_execute",
        "self_evaluate",
        "mcp_call",
        "mcp_list_tools",
        "generate_image",
        "generate_chart",
        "workspace_create_skill",
        "workspace_run_script",
        "workspace_list_skills",
        "workspace_scratch_write",
        "workspace_scratch_read",
        "search_thread_history",
    },
    "researcher": {
        "web_search",
        "web_fetch",
        "save_memory",
        "recall_memory",
        "find_skill",
        "use_skill",
        "rag_query",
        "rag_ingest",
        "code_execute",
        "self_evaluate",
        "mcp_call",
        "mcp_list_tools",
        "generate_image",
        "generate_chart",
        "workspace_create_skill",
        "workspace_run_script",
        "workspace_list_skills",
        "workspace_scratch_write",
        "workspace_scratch_read",
        "search_thread_history",
    },
    "reasoner": {
        "web_search",
        "web_fetch",
        "save_memory",
        "recall_memory",
        "find_skill",
        "use_skill",
        "rag_query",
        "code_execute",
        "self_evaluate",
        "mcp_call",
        "mcp_list_tools",
        "generate_image",
        "generate_chart",
        "workspace_create_skill",
        "workspace_run_script",
        "workspace_list_skills",
        "workspace_scratch_write",
        "workspace_scratch_read",
        "search_thread_history",
    },
    "critic": {
        "web_search",
        "web_fetch",
        "save_memory",
        "recall_memory",
        "find_skill",
        "use_skill",
        "rag_query",
        "code_execute",
        "self_evaluate",
        "mcp_call",
        "mcp_list_tools",
        "generate_image",
        "generate_chart",
        "workspace_create_skill",
        "workspace_run_script",
        "workspace_list_skills",
        "workspace_scratch_write",
        "workspace_scratch_read",
        "search_thread_history",
    },
}


def _sync_allowlist_with_registry() -> None:
    """Keep ROLE_ALLOWLIST aligned with tools.registry.AGENT_TOOLS.

    This prevents runtime sandbox blocks when a tool is exposed to an agent
    in registry but forgotten in static ROLE_ALLOWLIST.
    """
    try:
        from tools.registry import AGENT_TOOLS

        for role, tools in AGENT_TOOLS.items():
            tool_names = {
                t.get("function", {}).get("name") for t in tools if isinstance(t, dict)
            }
            tool_names.discard(None)
            ROLE_ALLOWLIST.setdefault(role, set()).update(tool_names)
    except Exception as e:
        logger.warning("Failed to sync sandbox allowlist with registry: %s", e)


_sync_allowlist_with_registry()

# Dangerous patterns in code execution
_DANGEROUS_CODE_PATTERNS = [
    re.compile(r"os\.system\s*\(", re.IGNORECASE),
    re.compile(r"subprocess\.(run|call|Popen|check_output)\s*\(", re.IGNORECASE),
    re.compile(r"shutil\.rmtree\s*\(", re.IGNORECASE),
    re.compile(r"__import__\s*\(", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"open\s*\([^)]*['\"]w['\"]", re.IGNORECASE),
    re.compile(r"rm\s+-rf", re.IGNORECASE),
    re.compile(r"format\s*\(\s*['\"]c:", re.IGNORECASE),
]

# Path traversal patterns
_PATH_TRAVERSAL = re.compile(r"\.\./|\.\.\\|%2e%2e", re.IGNORECASE)

# Max tool calls per agent per minute
_TOOL_RATE_LIMIT = 30


# ── Rate Limiter ─────────────────────────────────────────────────

@dataclass
class _ToolRateLimiter:
    window: float = 60.0
    max_calls: int = _TOOL_RATE_LIMIT
    _hits: dict[str, list[float]] = field(default_factory=dict)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window
        hits = self._hits.get(key, [])
        hits = [t for t in hits if t > cutoff]
        if len(hits) >= self.max_calls:
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


_rate_limiter = _ToolRateLimiter()

# ── Audit Log ────────────────────────────────────────────────────

_audit_log: list[dict[str, Any]] = []
_MAX_AUDIT_LOG = 1000


def get_audit_log(limit: int = 50) -> list[dict[str, Any]]:
    """Get recent sandbox audit entries."""
    return _audit_log[-limit:]


def _audit(agent_role: str, tool: str, status: str, detail: str = "") -> None:
    """Record a sandbox audit entry."""
    entry = {
        "timestamp": time.time(),
        "agent_role": agent_role,
        "tool": tool,
        "status": status,
        "detail": detail[:200],
    }
    _audit_log.append(entry)
    if len(_audit_log) > _MAX_AUDIT_LOG:
        _audit_log.pop(0)

    if status == "blocked":
        logger.warning("SANDBOX BLOCKED: %s → %s: %s", agent_role, tool, detail)


# ── Validators ───────────────────────────────────────────────────

def _validate_code_execute(args: dict[str, Any]) -> None:
    """Check code_execute arguments for dangerous patterns."""
    code = args.get("code", "")
    for pattern in _DANGEROUS_CODE_PATTERNS:
        if pattern.search(code):
            raise SandboxViolation(
                "code_execute",
                f"Dangerous code pattern detected: {pattern.pattern}",
                severity="critical",
            )


def _validate_path_args(args: dict[str, Any]) -> None:
    """Check all string arguments for path traversal."""
    for key, value in args.items():
        if isinstance(value, str) and _PATH_TRAVERSAL.search(value):
            raise SandboxViolation(
                "path_traversal",
                f"Path traversal detected in argument '{key}': {value[:50]}",
                severity="critical",
            )


def _validate_web_fetch(args: dict[str, Any]) -> None:
    """Validate web_fetch URLs — block internal/private IPs."""
    url = args.get("url", "")
    blocked = [
        "127.0.0.1", "localhost", "0.0.0.0",
        "169.254.", "10.", "192.168.", "172.16.",
    ]
    for pattern in blocked:
        if pattern in url.lower():
            raise SandboxViolation(
                "web_fetch",
                f"Internal/private URL blocked: {url[:80]}",
                severity="high",
            )


# ── Main Validation ──────────────────────────────────────────────

def validate_tool_call(
    agent_role: str,
    tool_name: str,
    args: dict[str, Any] | None = None,
) -> None:
    """
    Validate a tool call against sandbox policies.

    Raises SandboxViolation if the call is not allowed.
    """
    args = args or {}

    # 1. Role allowlist check
    allowed = ROLE_ALLOWLIST.get(agent_role, set())
    if tool_name not in allowed:
        _audit(agent_role, tool_name, "blocked", "not in role allowlist")
        raise SandboxViolation(
            tool_name,
            f"Agent '{agent_role}' is not allowed to call '{tool_name}'",
            severity="high",
        )

    # 2. Rate limit check
    rate_key = f"{agent_role}:{tool_name}"
    if not _rate_limiter.check(rate_key):
        _audit(agent_role, tool_name, "blocked", "rate limit exceeded")
        raise SandboxViolation(
            tool_name,
            f"Rate limit exceeded for {agent_role}:{tool_name}",
            severity="medium",
        )

    # 3. Path traversal check on all args
    _validate_path_args(args)

    # 4. Tool-specific validation
    if tool_name == "code_execute":
        _validate_code_execute(args)

    if tool_name == "web_fetch":
        _validate_web_fetch(args)

    # 5. Audit success
    _audit(agent_role, tool_name, "allowed")
