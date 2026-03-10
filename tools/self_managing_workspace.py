"""
Self-Managing Workspace — Inspired by pi-mom's workspace pattern.

Agents can create, manage, and execute their own tools (skills) autonomously.
Each agent gets an isolated workspace directory with persistent state.

Key concepts from mom adapted to multi-agent:
- Agent-scoped workspaces (like mom's channel directories)
- Self-created CLI tools/scripts (skills with executable components)
- Persistent MEMORY.md per workspace (complementing Qdrant)
- Workspace-level scratch directories for intermediate work
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "data/workspaces"))
MAX_SCRIPT_EXECUTION_TIME = 30  # seconds
MAX_OUTPUT_SIZE = 50_000  # characters

# Allowed script interpreters
INTERPRETERS = {
    ".py": ["python", "-u"],
    ".js": ["node"],
    ".sh": ["bash"],
    ".ts": ["npx", "tsx"],
}

# Blocked patterns in scripts (security)
BLOCKED_PATTERNS = [
    "rm -rf /",
    "format c:",
    ":(){ :|:& };:",  # fork bomb
    "dd if=/dev/zero",
    "> /dev/sda",
]


# ── Workspace Manager ────────────────────────────────────────────

class AgentWorkspace:
    """
    Isolated workspace for an agent, inspired by mom's per-channel directories.

    Structure:
        data/workspaces/{agent_role}/
        ├── MEMORY.md           # Agent-local memory (quick notes, not Qdrant)
        ├── skills/             # Agent-created executable skills
        │   └── {skill_name}/
        │       ├── SKILL.md    # Skill description + usage
        │       └── *.py/sh/js  # Executable scripts
        ├── scratch/            # Temporary working directory
        └── state.json          # Workspace metadata
    """

    def __init__(self, agent_role: str):
        self.agent_role = agent_role
        self.root = WORKSPACE_ROOT / agent_role
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Create workspace directory structure if missing."""
        (self.root / "skills").mkdir(parents=True, exist_ok=True)
        (self.root / "scratch").mkdir(parents=True, exist_ok=True)

        state_path = self.root / "state.json"
        if not state_path.exists():
            state_path.write_text(json.dumps({
                "agent_role": self.agent_role,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "skill_count": 0,
                "last_active": None,
            }, indent=2), encoding="utf-8")

        memory_path = self.root / "MEMORY.md"
        if not memory_path.exists():
            memory_path.write_text(
                f"# {self.agent_role.title()} Agent Memory\n\n"
                "Quick notes and workspace-local context.\n\n",
                encoding="utf-8",
            )

    # ── Skill Management ─────────────────────────────────────────

    def create_skill(
        self,
        skill_name: str,
        description: str,
        usage_instructions: str,
        scripts: dict[str, str],
    ) -> dict[str, Any]:
        """
        Create an executable skill in this agent's workspace.

        Args:
            skill_name: kebab-case name (e.g. 'data-analyzer')
            description: What the skill does
            usage_instructions: How to invoke it (markdown)
            scripts: {'script.py': 'code content', ...}

        Returns:
            Skill metadata dict
        """
        clean_name = skill_name.lower().replace(" ", "-").strip()
        skill_dir = self.root / "skills" / clean_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        skill_md = (
            f"---\n"
            f"name: {clean_name}\n"
            f"description: {description}\n"
            f"agent: {self.agent_role}\n"
            f"created: {datetime.now(timezone.utc).isoformat()}\n"
            f"---\n\n"
            f"# {skill_name}\n\n"
            f"{description}\n\n"
            f"## Usage\n\n"
            f"{usage_instructions}\n"
        )
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

        # Write script files
        for filename, content in scripts.items():
            script_path = skill_dir / filename
            script_path.write_text(content, encoding="utf-8")
            # Make shell scripts executable
            if filename.endswith(".sh"):
                script_path.chmod(0o755)

        # Update state
        self._update_state(skill_count_delta=1)

        logger.info(
            "[Workspace:%s] Created skill '%s' with %d scripts",
            self.agent_role, clean_name, len(scripts),
        )
        return {
            "skill_name": clean_name,
            "path": str(skill_dir),
            "scripts": list(scripts.keys()),
            "agent": self.agent_role,
        }

    def execute_skill_script(
        self,
        skill_name: str,
        script_name: str,
        args: list[str] | None = None,
        stdin_data: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a script from an agent's skill.

        Returns:
            {success, stdout, stderr, execution_time_ms}
        """
        skill_dir = self.root / "skills" / skill_name
        script_path = skill_dir / script_name

        if not script_path.exists():
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Script not found: {skill_name}/{script_name}",
                "execution_time_ms": 0,
            }

        # Security check
        content = script_path.read_text(encoding="utf-8")
        for pattern in BLOCKED_PATTERNS:
            if pattern in content:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Blocked dangerous pattern in script: {pattern}",
                    "execution_time_ms": 0,
                }

        # Determine interpreter
        suffix = script_path.suffix
        interpreter = INTERPRETERS.get(suffix)
        if not interpreter:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"No interpreter for {suffix}",
                "execution_time_ms": 0,
            }

        cmd = interpreter + [str(script_path)] + (args or [])

        t0 = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=MAX_SCRIPT_EXECUTION_TIME,
                cwd=str(skill_dir),
                input=stdin_data,
            )
            elapsed = (time.monotonic() - t0) * 1000

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:MAX_OUTPUT_SIZE],
                "stderr": result.stderr[:MAX_OUTPUT_SIZE],
                "execution_time_ms": round(elapsed, 1),
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Timeout after {MAX_SCRIPT_EXECUTION_TIME}s",
                "execution_time_ms": MAX_SCRIPT_EXECUTION_TIME * 1000,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"{type(e).__name__}: {e}",
                "execution_time_ms": 0,
            }

    def list_skills(self) -> list[dict[str, Any]]:
        """List all skills in this agent's workspace."""
        skills_dir = self.root / "skills"
        results = []
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            desc = ""
            if skill_md.exists():
                # Parse description from frontmatter
                text = skill_md.read_text(encoding="utf-8")
                for line in text.split("\n"):
                    if line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip()
                        break

            scripts = [
                f.name for f in skill_dir.iterdir()
                if f.is_file() and f.suffix in INTERPRETERS
            ]
            results.append({
                "name": skill_dir.name,
                "description": desc,
                "scripts": scripts,
                "path": str(skill_dir),
            })
        return results

    def get_skill_md(self, skill_name: str) -> str | None:
        """Read a skill's SKILL.md content."""
        path = self.root / "skills" / skill_name / "SKILL.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    # ── Scratch Space ────────────────────────────────────────────

    def write_scratch(self, filename: str, content: str) -> str:
        """Write a file to scratch space. Returns full path."""
        path = self.root / "scratch" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def read_scratch(self, filename: str) -> str | None:
        """Read a file from scratch space."""
        path = self.root / "scratch" / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def list_scratch(self) -> list[str]:
        """List files in scratch space."""
        scratch = self.root / "scratch"
        return [f.name for f in scratch.iterdir() if f.is_file()]

    # ── Memory (workspace-local, complements Qdrant) ─────────────

    def append_memory(self, note: str) -> None:
        """Append a note to workspace-local MEMORY.md."""
        path = self.root / "MEMORY.md"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n- [{ts}] {note}\n")

    def read_memory(self) -> str:
        """Read workspace-local MEMORY.md."""
        path = self.root / "MEMORY.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    # ── State Management ─────────────────────────────────────────

    def _update_state(self, skill_count_delta: int = 0) -> None:
        """Update workspace state.json."""
        state_path = self.root / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["skill_count"] = state.get("skill_count", 0) + skill_count_delta
        state["last_active"] = datetime.now(timezone.utc).isoformat()
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def get_state(self) -> dict[str, Any]:
        """Get workspace state."""
        state_path = self.root / "state.json"
        return json.loads(state_path.read_text(encoding="utf-8"))


# ── Global Workspace (shared across all agents) ─────────────────

class SharedWorkspaceManager:
    """
    Manages global skills accessible to all agents.
    Like mom's /workspace/skills/ vs /workspace/<channel>/skills/.
    """

    def __init__(self):
        self.global_skills_dir = WORKSPACE_ROOT / "_shared" / "skills"
        self.global_skills_dir.mkdir(parents=True, exist_ok=True)

    def get_agent_workspace(self, agent_role: str) -> AgentWorkspace:
        """Get or create an agent's workspace."""
        return AgentWorkspace(agent_role)

    def list_all_skills(self) -> dict[str, list[dict]]:
        """List skills across all agent workspaces + global."""
        result = {"_shared": []}

        # Global skills
        for skill_dir in sorted(self.global_skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                desc = ""
                if skill_md.exists():
                    for line in skill_md.read_text(encoding="utf-8").split("\n"):
                        if line.startswith("description:"):
                            desc = line.split(":", 1)[1].strip()
                            break
                result["_shared"].append({
                    "name": skill_dir.name,
                    "description": desc,
                })

        # Per-agent skills
        if WORKSPACE_ROOT.exists():
            for agent_dir in sorted(WORKSPACE_ROOT.iterdir()):
                if agent_dir.is_dir() and agent_dir.name != "_shared":
                    ws = AgentWorkspace(agent_dir.name)
                    skills = ws.list_skills()
                    if skills:
                        result[agent_dir.name] = skills

        return result

    def get_workspace_stats(self) -> dict[str, Any]:
        """Get overall workspace statistics."""
        stats = {"agents": {}, "total_skills": 0}
        if WORKSPACE_ROOT.exists():
            for agent_dir in WORKSPACE_ROOT.iterdir():
                if agent_dir.is_dir() and agent_dir.name != "_shared":
                    ws = AgentWorkspace(agent_dir.name)
                    state = ws.get_state()
                    skills = ws.list_skills()
                    stats["agents"][agent_dir.name] = {
                        "skill_count": len(skills),
                        "last_active": state.get("last_active"),
                    }
                    stats["total_skills"] += len(skills)
        return stats


# ── Singleton ────────────────────────────────────────────────────

_manager: SharedWorkspaceManager | None = None


def get_workspace_manager() -> SharedWorkspaceManager:
    global _manager
    if _manager is None:
        _manager = SharedWorkspaceManager()
    return _manager
