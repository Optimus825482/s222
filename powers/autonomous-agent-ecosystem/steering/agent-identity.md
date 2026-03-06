# Agent Identity — SOUL.md Pattern

Persistent identity files that give each agent personality, memory, and behavioral consistency.

## Problem

Agents lose personality between sessions. Each agent should have:

- A persistent identity (values, communication style, expertise)
- User preference memory (how the user likes to interact)
- Cross-session memory (what happened before)
- Bootstrap protocol (how to initialize on startup)

## Inspired By

OpenClaw's Markdown-based identity system where each agent instance has:

- `SOUL.md` — Core personality and values
- `user.md` — User preferences and interaction history
- `memory.md` — Persistent cross-session knowledge
- `bootstrap.md` — Startup initialization protocol

## File Structure

```
data/agents/{agent_role}/
├── SOUL.md        # Personality, values, expertise
├── user.md        # User preferences
├── memory.md      # Cross-session memory
└── bootstrap.md   # Startup protocol
```

## SOUL.md Template

```markdown
---
agent: "thinker"
model: "minimaxai/minimax-m2.1"
version: 1
last_updated: "2026-03-07"
---

# 🔬 Thinker — Deep Analysis Agent

## Core Identity

I am the deep thinker of the team. I take complex problems and break them
down into their fundamental components. I prefer thoroughness over speed.

## Values

- Accuracy over speed
- Evidence-based reasoning
- Intellectual honesty — I say "I don't know" when I don't
- Collaborative — I build on other agents' work

## Expertise

- Complex reasoning and analysis
- Multi-step problem decomposition
- Mathematical and logical verification
- Research synthesis

## Communication Style

- Structured and methodical
- Uses numbered lists for complex explanations
- Asks clarifying questions before diving in
- Provides confidence levels with answers

## Boundaries

- I defer to Researcher for web searches
- I defer to Speed for quick formatting tasks
- I escalate to Orchestrator when stuck
- I never make claims without evidence
```

## user.md Template

```markdown
---
user: "erkan"
last_updated: "2026-03-07"
---

# User Profile: Erkan

## Communication Preferences

- Language: Turkish for conversation, English for code
- Style: Casual but professional (samimi ama profesyonel)
- Detail level: Concise — no unnecessary explanations

## Technical Context

- Stack: FastAPI + Next.js 14 + PostgreSQL + pgvector
- IDE: Kiro
- OS: Windows
- Prefers: Dark theme, Turkish UI labels

## Interaction Patterns

- Likes quick iterations over long planning
- Prefers seeing working code over architecture docs
- Values practical examples over theory
- Often works in sprint-like bursts
```

## memory.md Template

```markdown
---
agent: "thinker"
entries: 12
last_updated: "2026-03-07"
---

# Cross-Session Memory

## Recent Learnings

- [2026-03-07] Docker build fails when AgentRole type is incomplete — always check all Record<AgentRole, string> objects
- [2026-03-06] Reasoning models need 180s timeout, standard models 90s
- [2026-03-05] OpenClaw agents can interact across instances — they created Crustafarianism on Moltbook

## Recurring Patterns

- User often asks for ROADMAP updates after feature completion
- Frontend changes usually need types.ts + api.ts + component file
- Backend endpoints follow Section numbering pattern in main.py

## Important Decisions

- Autonomous chat uses personality-based prompts per agent
- Post-task meetings are auto-triggered via WebSocket
- Observer agent uses DeepSeek (different base_url)
```

## bootstrap.md Template

```markdown
---
agent: "thinker"
version: 1
---

# Bootstrap Protocol

## On Startup

1. Load SOUL.md — establish identity
2. Load user.md — understand user preferences
3. Load memory.md — restore cross-session context
4. Check pending tasks from last session
5. Report ready status to Orchestrator

## On New Task

1. Check memory.md for related past work
2. Review SOUL.md boundaries — am I the right agent?
3. If not → suggest delegation to appropriate agent
4. If yes → proceed with task using identity-consistent approach

## On Session End

1. Update memory.md with new learnings
2. Update user.md if preferences changed
3. Report session summary to Orchestrator
```

## Backend Implementation

```python
# tools/agent_identity.py

from pathlib import Path
from dataclasses import dataclass
import yaml

IDENTITY_DIR = Path("data/agents")

@dataclass
class AgentIdentity:
    role: str
    soul: str       # SOUL.md content
    user: str       # user.md content
    memory: str     # memory.md content
    bootstrap: str  # bootstrap.md content

class IdentityManager:
    def __init__(self, base_dir: Path = IDENTITY_DIR):
        self.base_dir = base_dir

    def load(self, role: str) -> AgentIdentity:
        agent_dir = self.base_dir / role
        return AgentIdentity(
            role=role,
            soul=self._read(agent_dir / "SOUL.md"),
            user=self._read(agent_dir / "user.md"),
            memory=self._read(agent_dir / "memory.md"),
            bootstrap=self._read(agent_dir / "bootstrap.md"),
        )

    def update_memory(self, role: str, entry: str):
        """Append a new memory entry."""
        agent_dir = self.base_dir / role
        memory_path = agent_dir / "memory.md"
        content = self._read(memory_path)
        # Append under "## Recent Learnings"
        from datetime import date
        new_entry = f"\n- [{date.today()}] {entry}"
        content = content.replace(
            "## Recent Learnings",
            f"## Recent Learnings{new_entry}",
        )
        memory_path.write_text(content, encoding="utf-8")

    def get_system_prompt(self, role: str) -> str:
        """Build system prompt from identity files."""
        identity = self.load(role)
        return f"""{identity.soul}

---
User Context:
{identity.user}

---
Session Memory:
{identity.memory}"""

    def initialize_agent(self, role: str):
        """Create default identity files for a new agent."""
        agent_dir = self.base_dir / role
        agent_dir.mkdir(parents=True, exist_ok=True)
        # Create template files if they don't exist
        for filename, template_fn in [
            ("SOUL.md", self._default_soul),
            ("user.md", self._default_user),
            ("memory.md", self._default_memory),
            ("bootstrap.md", self._default_bootstrap),
        ]:
            path = agent_dir / filename
            if not path.exists():
                path.write_text(template_fn(role), encoding="utf-8")

    def _read(self, path: Path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _default_soul(self, role: str) -> str:
        return f"---\nagent: \"{role}\"\n---\n\n# {role.title()} Agent\n\nIdentity not yet configured.\n"

    def _default_user(self, role: str) -> str:
        return f"---\nuser: \"default\"\n---\n\n# User Profile\n\nNo user preferences recorded yet.\n"

    def _default_memory(self, role: str) -> str:
        return f"---\nagent: \"{role}\"\nentries: 0\n---\n\n# Cross-Session Memory\n\n## Recent Learnings\n\n## Recurring Patterns\n\n## Important Decisions\n"

    def _default_bootstrap(self, role: str) -> str:
        return f"---\nagent: \"{role}\"\n---\n\n# Bootstrap Protocol\n\n## On Startup\n1. Load identity files\n2. Report ready\n"
```

### FastAPI Endpoints

```python
@app.get("/api/agents/{role}/identity")
async def get_agent_identity(role: str):
    """Get all identity files for an agent."""
    mgr = IdentityManager()
    identity = mgr.load(role)
    return {
        "role": role,
        "soul": identity.soul,
        "user": identity.user,
        "memory": identity.memory,
        "bootstrap": identity.bootstrap,
    }

@app.put("/api/agents/{role}/identity/{file_type}")
async def update_identity_file(role: str, file_type: str, content: str):
    """Update a specific identity file (soul, user, memory, bootstrap)."""
    pass

@app.post("/api/agents/{role}/memory")
async def add_memory_entry(role: str, entry: str):
    """Add a new memory entry for an agent."""
    mgr = IdentityManager()
    mgr.update_memory(role, entry)
    return {"status": "ok"}
```

## Frontend Component

```tsx
// components/agent-identity-editor.tsx

// Tabbed editor for each identity file (SOUL, User, Memory, Bootstrap)
// Markdown preview with syntax highlighting
// Per-agent selector dropdown
// Memory timeline view
// "Initialize All Agents" button for first-time setup
```

## Implementation Checklist

- [ ] Create `data/agents/{role}/` directories for all 6 agents
- [ ] Create `tools/agent_identity.py` with `IdentityManager`
- [ ] Generate default SOUL.md for each agent based on config.py roles
- [ ] Integrate identity loading into agent system prompt construction
- [ ] Memory auto-update after task completion
- [ ] REST endpoints for identity CRUD
- [ ] Frontend: `AgentIdentityEditor` component
- [ ] Bootstrap protocol execution on app startup
