# Self-Skill Creation — Runtime Skill Generation

Agents that learn by creating their own reusable skills during task execution.

## Problem

Currently skills are manually authored. Autonomous agents should:

- Recognize repeating patterns and extract them as skills
- Store skills as Markdown files (OpenClaw SOUL.md pattern)
- Validate skills before activation
- Share skills across agents

## Architecture

```
Agent executes task
    │
    ▼
┌──────────────────────────────────┐
│  Pattern Detector                │
│  "Have I done this 3+ times?"   │
└──────────┬───────────────────────┘
           │ yes
           ▼
┌──────────────────────────────────┐
│  Skill Extractor                 │
│  Extract: trigger, steps, tools  │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Skill Validator                 │
│  ├─ Syntax check                │
│  ├─ Duplicate detection         │
│  ├─ Safety review               │
│  └─ Dry-run test                │
└──────────┬───────────────────────┘
           │ pass
           ▼
┌──────────────────────────────────┐
│  Skill Registry                  │
│  ├─ data/skills/{id}/SKILL.md   │
│  ├─ SQLite index                │
│  └─ Cross-agent broadcast       │
└──────────────────────────────────┘
```

## Skill File Format

Following OpenClaw's Markdown-based identity pattern:

```markdown
---
name: "auto-generated-skill-name"
description: "What this skill does and when to use it"
trigger: "keyword or pattern that activates this skill"
created_by: "thinker"
created_at: "2026-03-07T10:00:00Z"
version: 1
confidence: 0.85
usage_count: 0
---

# Skill: Auto-Generated Skill Name

## When to Use

Describe the trigger conditions.

## Steps

1. Step one
2. Step two
3. Step three

## Tools Required

- tool_name_1
- tool_name_2

## Example

Input: "..."
Output: "..."
```

## Backend Implementation

### Skill Generator

```python
# tools/self_skill.py

import hashlib
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

@dataclass
class GeneratedSkill:
    name: str
    description: str
    trigger: str
    steps: list[str]
    tools: list[str]
    created_by: str
    confidence: float

class SelfSkillEngine:
    def __init__(self, skills_dir: Path, db_path: Path):
        self.skills_dir = skills_dir
        self.db_path = db_path
        self._pattern_buffer: dict[str, list[dict]] = {}  # agent -> recent tasks

    async def observe_task(self, agent_role: str, task: dict):
        """Record task execution for pattern detection."""
        if agent_role not in self._pattern_buffer:
            self._pattern_buffer[agent_role] = []
        self._pattern_buffer[agent_role].append(task)
        # Keep last 50 tasks per agent
        self._pattern_buffer[agent_role] = self._pattern_buffer[agent_role][-50:]

    async def detect_patterns(self, agent_role: str) -> list[dict]:
        """Find repeating task patterns (3+ occurrences)."""
        tasks = self._pattern_buffer.get(agent_role, [])
        # Group by tool sequence signature
        signatures: dict[str, list[dict]] = {}
        for task in tasks:
            sig = self._task_signature(task)
            signatures.setdefault(sig, []).append(task)
        return [
            {"signature": sig, "count": len(group), "examples": group[:3]}
            for sig, group in signatures.items()
            if len(group) >= 3
        ]

    async def generate_skill(self, pattern: dict, agent) -> GeneratedSkill:
        """Ask agent to extract a reusable skill from pattern."""
        prompt = f"""Analyze these {pattern['count']} similar tasks and extract a reusable skill.

Examples:
{json.dumps(pattern['examples'], indent=2, default=str)}

Return JSON with: name, description, trigger, steps (list), tools (list)."""

        result = await agent.generate(prompt)
        return GeneratedSkill(**result, created_by=agent.role, confidence=0.85)

    async def validate_skill(self, skill: GeneratedSkill) -> dict:
        """Validate before activation."""
        errors = []
        if not skill.name or len(skill.name) < 3:
            errors.append("Name too short")
        if not skill.steps:
            errors.append("No steps defined")
        if await self._is_duplicate(skill):
            errors.append("Duplicate skill detected")
        return {"valid": len(errors) == 0, "errors": errors}

    async def save_skill(self, skill: GeneratedSkill) -> str:
        """Save as Markdown file + register in DB."""
        skill_id = f"auto-{hashlib.md5(skill.name.encode()).hexdigest()[:8]}"
        skill_dir = self.skills_dir / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        md_content = self._render_markdown(skill, skill_id)
        (skill_dir / "SKILL.md").write_text(md_content, encoding="utf-8")

        # Register in SQLite
        await self._register_in_db(skill_id, skill)
        return skill_id

    async def share_skill(self, skill_id: str, target_agents: list[str]):
        """Broadcast skill availability to other agents."""
        # Notify via internal event system
        pass

    def _task_signature(self, task: dict) -> str:
        tools = tuple(sorted(task.get("tools_used", [])))
        return hashlib.md5(str(tools).encode()).hexdigest()[:12]

    async def _is_duplicate(self, skill: GeneratedSkill) -> bool:
        # Check existing skills for similarity
        return False

    def _render_markdown(self, skill: GeneratedSkill, skill_id: str) -> str:
        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(skill.steps))
        tools_md = "\n".join(f"- {t}" for t in skill.tools)
        return f"""---
name: "{skill_id}"
description: "{skill.description}"
trigger: "{skill.trigger}"
created_by: "{skill.created_by}"
created_at: "{datetime.now().isoformat()}"
version: 1
confidence: {skill.confidence}
usage_count: 0
---

# Skill: {skill.name}

## When to Use
{skill.trigger}

## Steps
{steps_md}

## Tools Required
{tools_md}
"""
```

### FastAPI Endpoints

```python
@app.get("/api/self-skills")
async def list_self_skills():
    """List all auto-generated skills."""
    pass

@app.post("/api/self-skills/detect")
async def detect_skill_patterns(agent_role: str):
    """Trigger pattern detection for an agent."""
    pass

@app.post("/api/self-skills/generate")
async def generate_skill_from_pattern(pattern_id: str):
    """Generate a skill from detected pattern."""
    pass

@app.delete("/api/self-skills/{skill_id}")
async def delete_self_skill(skill_id: str):
    """Remove an auto-generated skill."""
    pass
```

## Frontend Component

```tsx
// components/self-skill-panel.tsx

// Display: list of auto-generated skills with confidence scores
// Pattern detection status per agent
// Skill preview (rendered Markdown)
// Enable/disable toggle per skill
// "Generate from pattern" button
// Cross-agent sharing controls
```

## Implementation Checklist

- [ ] Create `tools/self_skill.py` with `SelfSkillEngine`
- [ ] Integrate pattern observation into task execution pipeline
- [ ] Implement pattern detection (3+ occurrence threshold)
- [ ] Skill generation via agent LLM call
- [ ] Validation pipeline (syntax, duplicate, safety)
- [ ] Markdown file storage in `data/skills/`
- [ ] SQLite registry for fast lookup
- [ ] REST endpoints for skill management
- [ ] Frontend: `SelfSkillPanel` component
- [ ] Cross-agent skill sharing broadcast
