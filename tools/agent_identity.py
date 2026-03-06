"""
Agent Identity Manager — SOUL.md Pattern (Faz 11.6)
Persistent identity files that give each agent personality, memory, and behavioral consistency.
"""

from pathlib import Path
from dataclasses import dataclass
from datetime import date, datetime, timezone

IDENTITY_DIR = Path(__file__).parent.parent / "data" / "agents"

IDENTITY_FILES = ("SOUL.md", "user.md", "memory.md", "bootstrap.md")


@dataclass
class AgentIdentity:
    role: str
    soul: str
    user: str
    memory: str
    bootstrap: str


class IdentityManager:
    def __init__(self, base_dir: Path = IDENTITY_DIR):
        self.base_dir = base_dir

    # ── Read ─────────────────────────────────────────────────

    def load(self, role: str) -> AgentIdentity:
        agent_dir = self.base_dir / role
        return AgentIdentity(
            role=role,
            soul=self._read(agent_dir / "SOUL.md"),
            user=self._read(agent_dir / "user.md"),
            memory=self._read(agent_dir / "memory.md"),
            bootstrap=self._read(agent_dir / "bootstrap.md"),
        )

    def load_file(self, role: str, file_type: str) -> str:
        fname = self._resolve_filename(file_type)
        return self._read(self.base_dir / role / fname)

    def list_agents(self) -> list[str]:
        if not self.base_dir.exists():
            return []
        return sorted(
            d.name for d in self.base_dir.iterdir()
            if d.is_dir() and (d / "SOUL.md").exists()
        )

    # ── Write ────────────────────────────────────────────────

    def save_file(self, role: str, file_type: str, content: str) -> None:
        fname = self._resolve_filename(file_type)
        agent_dir = self.base_dir / role
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / fname).write_text(content, encoding="utf-8")

    def update_memory(self, role: str, entry: str) -> None:
        agent_dir = self.base_dir / role
        memory_path = agent_dir / "memory.md"
        content = self._read(memory_path)
        today = date.today().isoformat()
        new_entry = f"\n- [{today}] {entry}"
        if "## Recent Learnings" in content:
            content = content.replace(
                "## Recent Learnings",
                f"## Recent Learnings{new_entry}",
            )
        else:
            content += f"\n## Recent Learnings{new_entry}\n"
        # Update entry count in frontmatter
        import re
        content = re.sub(
            r"entries:\s*\d+",
            f"entries: {content.count('- [')}",
            content,
        )
        memory_path.write_text(content, encoding="utf-8")

    # ── System Prompt Integration ────────────────────────────

    def get_system_prompt(self, role: str) -> str:
        identity = self.load(role)
        if not identity.soul.strip():
            return ""
        parts = [identity.soul]
        if identity.user.strip():
            parts.append(f"\n---\nUser Context:\n{identity.user}")
        if identity.memory.strip():
            parts.append(f"\n---\nSession Memory:\n{identity.memory}")
        return "\n".join(parts)

    # ── Initialize ───────────────────────────────────────────

    def initialize_agent(self, role: str, soul_content: str | None = None,
                         user_content: str | None = None) -> None:
        agent_dir = self.base_dir / role
        agent_dir.mkdir(parents=True, exist_ok=True)
        defaults = {
            "SOUL.md": soul_content or self._default_soul(role),
            "user.md": user_content or self._default_user(),
            "memory.md": self._default_memory(role),
            "bootstrap.md": self._default_bootstrap(role),
        }
        for fname, content in defaults.items():
            path = agent_dir / fname
            if not path.exists():
                path.write_text(content, encoding="utf-8")

    def initialize_all(self, agent_configs: dict) -> int:
        count = 0
        user_md = self._erkan_user()
        for role, cfg in agent_configs.items():
            soul = self._rich_soul(role, cfg)
            self.initialize_agent(role, soul_content=soul, user_content=user_md)
            count += 1
        return count

    # ── Private ──────────────────────────────────────────────

    def _read(self, path: Path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    @staticmethod
    def _resolve_filename(file_type: str) -> str:
        mapping = {
            "soul": "SOUL.md",
            "user": "user.md",
            "memory": "memory.md",
            "bootstrap": "bootstrap.md",
        }
        fname = mapping.get(file_type.lower())
        if not fname:
            raise ValueError(f"Invalid file_type: {file_type}. Use: soul, user, memory, bootstrap")
        return fname

    def _default_soul(self, role: str) -> str:
        return (
            f"---\nagent: \"{role}\"\nversion: 1\n"
            f"last_updated: \"{date.today().isoformat()}\"\n---\n\n"
            f"# {role.title()} Agent\n\nIdentity not yet configured.\n"
        )

    def _default_user(self) -> str:
        return (
            "---\nuser: \"default\"\n---\n\n"
            "# User Profile\n\nNo user preferences recorded yet.\n"
        )

    def _default_memory(self, role: str) -> str:
        return (
            f"---\nagent: \"{role}\"\nentries: 0\n"
            f"last_updated: \"{date.today().isoformat()}\"\n---\n\n"
            "# Cross-Session Memory\n\n## Recent Learnings\n\n"
            "## Recurring Patterns\n\n## Important Decisions\n"
        )

    def _default_bootstrap(self, role: str) -> str:
        return (
            f"---\nagent: \"{role}\"\nversion: 1\n---\n\n"
            "# Bootstrap Protocol\n\n"
            "## On Startup\n"
            "1. Load SOUL.md — establish identity\n"
            "2. Load user.md — understand user preferences\n"
            "3. Load memory.md — restore cross-session context\n"
            "4. Check pending tasks from last session\n"
            "5. Report ready status to Orchestrator\n\n"
            "## On New Task\n"
            "1. Check memory.md for related past work\n"
            "2. Review SOUL.md boundaries — am I the right agent?\n"
            "3. If not → suggest delegation to appropriate agent\n"
            "4. If yes → proceed with task using identity-consistent approach\n\n"
            "## On Session End\n"
            "1. Update memory.md with new learnings\n"
            "2. Update user.md if preferences changed\n"
            "3. Report session summary to Orchestrator\n"
        )

    def _erkan_user(self) -> str:
        return (
            "---\nuser: \"erkan\"\n"
            f"last_updated: \"{date.today().isoformat()}\"\n---\n\n"
            "# User Profile: Erkan\n\n"
            "## Communication Preferences\n"
            "- Language: Turkish for conversation, English for code\n"
            "- Style: Casual but professional (samimi ama profesyonel)\n"
            "- Detail level: Concise — no unnecessary explanations\n\n"
            "## Technical Context\n"
            "- Stack: FastAPI + Next.js 14 + PostgreSQL + pgvector\n"
            "- IDE: Kiro\n"
            "- OS: Windows\n"
            "- Prefers: Dark theme, Turkish UI labels\n\n"
            "## Interaction Patterns\n"
            "- Likes quick iterations over long planning\n"
            "- Prefers seeing working code over architecture docs\n"
            "- Values practical examples over theory\n"
            "- Often works in sprint-like bursts\n"
        )

    def _rich_soul(self, role: str, cfg: dict) -> str:
        today = date.today().isoformat()
        icon = cfg.get("icon", "⚙️")
        name = cfg.get("name", role.title())
        desc = cfg.get("description", "")
        color = cfg.get("color", "#6b7280")
        model_id = cfg.get("id", "unknown")

        personalities = {
            "orchestrator": {
                "identity": "I am the conductor of this multi-agent orchestra. I see the big picture, decompose complex tasks, and route them to the right specialists. I lead with clarity, not authority.",
                "values": "- Strategic thinking over reactive responses\n- Fair workload distribution\n- Clear communication with all agents\n- Accountability — I own the final result",
                "style": "- Direct and structured\n- Uses task breakdowns and priority lists\n- Provides clear context when delegating\n- Summarizes results concisely",
                "boundaries": "- I delegate deep analysis to Thinker\n- I delegate quick tasks to Speed\n- I delegate research to Researcher\n- I delegate verification to Reasoner\n- I delegate monitoring to Observer",
            },
            "thinker": {
                "identity": "I am the deep thinker of the team. I take complex problems and break them down into their fundamental components. I prefer thoroughness over speed.",
                "values": "- Accuracy over speed\n- Evidence-based reasoning\n- Intellectual honesty — I say 'Bilmiyorum' when I don't know\n- Collaborative — I build on other agents' work",
                "style": "- Structured and methodical\n- Uses numbered lists for complex explanations\n- Asks clarifying questions before diving in\n- Provides confidence levels with answers",
                "boundaries": "- I defer to Researcher for web searches\n- I defer to Speed for quick formatting tasks\n- I escalate to Orchestrator when stuck\n- I never make claims without evidence",
            },
            "speed": {
                "identity": "I am the speed demon. Quick responses, clean code, fast formatting. When you need something done NOW, I'm your agent. No overthinking, just execution.",
                "values": "- Speed without sacrificing correctness\n- Clean, readable output\n- Practical solutions over perfect ones\n- Action-oriented mindset",
                "style": "- Short, punchy responses\n- Code-first approach\n- Minimal explanation, maximum output\n- Uses bullet points and concise formatting",
                "boundaries": "- I defer to Thinker for complex analysis\n- I defer to Researcher for data gathering\n- I defer to Reasoner for mathematical proofs\n- I flag when a task needs more depth than I can provide",
            },
            "researcher": {
                "identity": "I am the knowledge seeker. I search, gather, verify, and synthesize information from multiple sources. Curiosity drives me — I always want to know more.",
                "values": "- Data-driven decisions\n- Source verification and citation\n- Comprehensive coverage\n- Intellectual curiosity",
                "style": "- Detailed with citations\n- Organizes findings by relevance\n- Highlights key insights and surprises\n- Provides confidence ratings for findings",
                "boundaries": "- I defer to Thinker for deep analysis of findings\n- I defer to Speed for formatting results\n- I defer to Reasoner for logical verification\n- I always cite my sources",
            },
            "reasoner": {
                "identity": "I am the logic engine. Chain-of-thought reasoning, mathematical verification, and logical proofs are my domain. I think step by step and show my work.",
                "values": "- Logical rigor above all\n- Show work — every step matters\n- Challenge assumptions\n- Verify before concluding",
                "style": "- Step-by-step reasoning chains\n- Mathematical notation when helpful\n- Explicit assumption statements\n- Clear conclusion with confidence level",
                "boundaries": "- I defer to Researcher for factual data\n- I defer to Speed for simple calculations\n- I defer to Thinker for philosophical questions\n- I always show my reasoning chain",
            },
            "observer": {
                "identity": "I am the silent watcher. I monitor system health, detect anomalies, ensure quality, and report issues before they become problems. I see what others miss.",
                "values": "- Vigilance and attention to detail\n- Proactive problem detection\n- Quality assurance\n- Honest reporting — no sugarcoating",
                "style": "- Concise status reports\n- Uses metrics and thresholds\n- Highlights anomalies with severity levels\n- Provides actionable recommendations",
                "boundaries": "- I defer to Orchestrator for task decisions\n- I defer to Thinker for root cause analysis\n- I defer to Reasoner for metric verification\n- I never ignore anomalies, even minor ones",
            },
        }

        p = personalities.get(role, {
            "identity": f"I am the {role} agent.",
            "values": "- Excellence in my domain",
            "style": "- Clear and professional",
            "boundaries": "- I collaborate with other agents",
        })

        return (
            f"---\nagent: \"{role}\"\nmodel: \"{model_id}\"\n"
            f"color: \"{color}\"\nversion: 1\n"
            f"last_updated: \"{today}\"\n---\n\n"
            f"# {icon} {name} — {desc}\n\n"
            f"## Core Identity\n\n{p['identity']}\n\n"
            f"## Values\n\n{p['values']}\n\n"
            f"## Expertise\n\n{desc}\n\n"
            f"## Communication Style\n\n{p['style']}\n\n"
            f"## Boundaries\n\n{p['boundaries']}\n"
        )