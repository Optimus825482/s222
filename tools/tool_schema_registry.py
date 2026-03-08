"""
Tool Schema Registry — Faz 14.3

Central registry for tool JSON Schemas.
- Extracts schemas from tools/registry.py
- Registers with pi-gateway on startup
- Provides local validation via jsonschema
- Tracks validation stats
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from config import PI_GATEWAY_URL, PI_GATEWAY_ENABLED

logger = logging.getLogger(__name__)

# ── Local validation stats ──

_stats: dict[str, Any] = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "by_tool": {},
    "last_sync": None,
    "gateway_registered": 0,
}


def _get_all_tool_schemas() -> list[dict]:
    """Extract all tool definitions from registry.py."""
    try:
        from tools.registry import AGENT_TOOLS
        all_tools: list[dict] = []
        seen: set[str] = set()
        for _role, tools in AGENT_TOOLS.items():
            for tool in tools:
                fn = tool.get("function", {})
                name = fn.get("name")
                if name and name not in seen:
                    seen.add(name)
                    all_tools.append(tool)
        return all_tools
    except Exception as e:
        logger.warning("Failed to load tool schemas from registry: %s", e)
        return []


async def register_with_gateway() -> dict[str, Any]:
    """Register all tool schemas with pi-gateway (Faz 14.3)."""
    if not PI_GATEWAY_ENABLED or not PI_GATEWAY_URL:
        return {"status": "skipped", "reason": "gateway not enabled"}

    tools = _get_all_tool_schemas()
    if not tools:
        return {"status": "skipped", "reason": "no tools found"}

    url = f"{PI_GATEWAY_URL}/v1/tools/register"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"tools": tools})
            result = resp.json()
            _stats["last_sync"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _stats["gateway_registered"] = result.get("registered", 0)
            logger.info(
                "Registered %d tool schemas with gateway (%d errors)",
                result.get("registered", 0),
                len(result.get("errors", [])),
            )
            return result
    except Exception as e:
        logger.warning("Failed to register tools with gateway: %s", e)
        return {"status": "error", "error": str(e)}


def validate_tool_args(tool_name: str, args: dict) -> dict[str, Any]:
    """Validate tool arguments against JSON Schema locally.

    Returns {"valid": True} or {"valid": False, "errors": [...], "correction_prompt": "..."}.
    """
    _stats["total"] += 1
    if tool_name not in _stats["by_tool"]:
        _stats["by_tool"][tool_name] = {"passed": 0, "failed": 0}

    # Find schema for this tool
    schema = _find_schema(tool_name)
    if not schema:
        _stats["passed"] += 1
        _stats["by_tool"][tool_name]["passed"] += 1
        return {"valid": True}

    # Validate using jsonschema
    try:
        import jsonschema
        jsonschema.validate(instance=args, schema=schema)
        _stats["passed"] += 1
        _stats["by_tool"][tool_name]["passed"] += 1
        return {"valid": True}
    except jsonschema.ValidationError as e:
        _stats["failed"] += 1
        _stats["by_tool"][tool_name]["failed"] += 1

        error_path = "/".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        error_detail = {
            "path": error_path,
            "message": e.message,
            "validator": e.validator,
        }

        # Build correction prompt for LLM retry
        correction = _build_correction_prompt(tool_name, schema, args, [error_detail])

        return {
            "valid": False,
            "errors": [error_detail],
            "correction_prompt": correction,
        }
    except ImportError:
        # jsonschema not installed — pass through
        _stats["passed"] += 1
        _stats["by_tool"][tool_name]["passed"] += 1
        return {"valid": True}
    except Exception:
        _stats["passed"] += 1
        _stats["by_tool"][tool_name]["passed"] += 1
        return {"valid": True}


# ── Schema cache ──

_schema_cache: dict[str, dict | None] = {}


def _find_schema(tool_name: str) -> dict | None:
    """Find JSON Schema parameters for a tool by name."""
    if tool_name in _schema_cache:
        return _schema_cache[tool_name]

    try:
        from tools.registry import AGENT_TOOLS
        for _role, tools in AGENT_TOOLS.items():
            for tool in tools:
                fn = tool.get("function", {})
                if fn.get("name") == tool_name:
                    schema = fn.get("parameters")
                    _schema_cache[tool_name] = schema
                    return schema
    except Exception:
        pass

    _schema_cache[tool_name] = None
    return None


def _build_correction_prompt(
    tool_name: str,
    schema: dict,
    invalid_args: dict,
    errors: list[dict],
) -> str:
    """Build a correction prompt that helps LLM fix invalid tool arguments."""
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    error_lines = []
    for err in errors:
        error_lines.append(f"- {err['path']}: {err['message']}")

    prop_lines = []
    for pname, pdef in properties.items():
        ptype = pdef.get("type", "any")
        req = " (REQUIRED)" if pname in required else ""
        desc = pdef.get("description", "")
        enum_vals = pdef.get("enum")
        enum_str = f" — allowed: {enum_vals}" if enum_vals else ""
        prop_lines.append(f"  - {pname}: {ptype}{req}{enum_str} — {desc}")

    return (
        f"Your call to '{tool_name}' had invalid arguments.\n"
        f"Errors:\n{''.join(error_lines)}\n\n"
        f"Expected schema for '{tool_name}':\n{''.join(prop_lines)}\n\n"
        f"Please call '{tool_name}' again with corrected arguments."
    )


async def get_gateway_stats() -> dict[str, Any]:
    """Fetch validation stats from gateway."""
    if not PI_GATEWAY_ENABLED or not PI_GATEWAY_URL:
        return {"status": "gateway_disabled"}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{PI_GATEWAY_URL}/v1/tools/validation-stats")
            return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_local_stats() -> dict[str, Any]:
    """Get local validation statistics."""
    return dict(_stats)


def get_all_schemas_summary() -> list[dict]:
    """Get summary of all registered tool schemas."""
    tools = _get_all_tool_schemas()
    result = []
    for tool in tools:
        fn = tool.get("function", {})
        params = fn.get("parameters", {})
        props = params.get("properties", {})
        required = params.get("required", [])
        result.append({
            "name": fn.get("name"),
            "description": (fn.get("description") or "")[:100],
            "param_count": len(props),
            "required_count": len(required),
            "required_params": required,
        })
    return result
