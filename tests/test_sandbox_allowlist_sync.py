from tools import registry, sandbox


def _tool_names(tool_defs: list[dict]) -> set[str]:
    names: set[str] = set()
    for tool in tool_defs:
        if not isinstance(tool, dict):
            continue
        name = tool.get("function", {}).get("name")
        if isinstance(name, str) and name:
            names.add(name)
    return names


def test_allowlist_covers_all_registered_agent_tools() -> None:
    """Every tool exposed to an agent must be sandbox-allowlisted for that role."""
    missing_by_role: dict[str, list[str]] = {}

    for role, tool_defs in registry.AGENT_TOOLS.items():
        required = _tool_names(tool_defs)
        allowed = sandbox.ROLE_ALLOWLIST.get(role, set())
        missing = sorted(required - allowed)
        if missing:
            missing_by_role[role] = missing

    assert not missing_by_role, f"Missing sandbox allowlist entries: {missing_by_role}"
