"""
Idea-to-Project Pipeline — Transform a raw idea into a professional project.
Inspired by Autogen AgentBuilder + Langgraph Plan-and-Execute.

Flow: Idea → PRD → Architecture → Task Breakdown → File Structure → Boilerplate Code
Each phase uses specialist agents and can pause for human approval.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Output directory for generated projects
PROJECTS_DIR = Path(__file__).parent.parent / "data" / "projects"


# ── Project Templates ────────────────────────────────────────────

PROJECT_TEMPLATES = {
    "web-app": {
        "name": "Web Application",
        "stack": "Next.js + TypeScript + Tailwind + Prisma + PostgreSQL",
        "structure": [
            "src/app/layout.tsx",
            "src/app/page.tsx",
            "src/app/api/",
            "src/components/",
            "src/lib/",
            "prisma/schema.prisma",
            "package.json",
            "tsconfig.json",
            "tailwind.config.ts",
            ".env.example",
            "README.md",
        ],
    },
    "api-service": {
        "name": "API Service",
        "stack": "FastAPI + Python + SQLAlchemy + PostgreSQL",
        "structure": [
            "app/main.py",
            "app/api/routes/",
            "app/models/",
            "app/schemas/",
            "app/services/",
            "app/core/config.py",
            "app/core/database.py",
            "alembic/",
            "requirements.txt",
            "Dockerfile",
            ".env.example",
            "README.md",
        ],
    },
    "mobile-app": {
        "name": "Mobile Application",
        "stack": "React Native + Expo + TypeScript + Supabase",
        "structure": [
            "app/(tabs)/index.tsx",
            "app/(tabs)/explore.tsx",
            "components/",
            "hooks/",
            "lib/supabase.ts",
            "package.json",
            "tsconfig.json",
            "app.json",
            "README.md",
        ],
    },
    "cli-tool": {
        "name": "CLI Tool",
        "stack": "Python + Click + Rich",
        "structure": [
            "src/cli.py",
            "src/commands/",
            "src/utils/",
            "pyproject.toml",
            "README.md",
        ],
    },
    "ai-agent": {
        "name": "AI Agent",
        "stack": "Python + LangChain/LangGraph + OpenAI + FastAPI",
        "structure": [
            "agent/main.py",
            "agent/tools/",
            "agent/prompts/",
            "agent/memory/",
            "api/server.py",
            "requirements.txt",
            "Dockerfile",
            ".env.example",
            "README.md",
        ],
    },
    "data-pipeline": {
        "name": "Data Pipeline",
        "stack": "Python + Apache Airflow + dbt + PostgreSQL",
        "structure": [
            "dags/",
            "models/",
            "transformations/",
            "tests/",
            "config/",
            "requirements.txt",
            "README.md",
        ],
    },
    "custom": {
        "name": "Custom Project",
        "stack": "Agent determines based on requirements",
        "structure": [],
    },
}


# ── Phase Definitions ────────────────────────────────────────────

PHASES = [
    {
        "id": "analyze",
        "name": "Fikir Analizi",
        "description": "Fikri analiz et, hedef kitleyi belirle, temel gereksinimleri çıkar",
        "agent": "thinker",
        "prompt_template": (
            "IDEA-TO-PROJECT: PHASE 1 — IDEA ANALYSIS\n\n"
            "User's raw idea: {idea}\n\n"
            "Analyze this idea thoroughly:\n"
            "1. What problem does it solve?\n"
            "2. Who is the target audience?\n"
            "3. What are the core features (MVP)?\n"
            "4. What are nice-to-have features (v2)?\n"
            "5. What similar products exist? How is this different?\n"
            "6. What are the main technical challenges?\n"
            "7. Estimated complexity (simple/medium/complex)\n\n"
            "Output as structured analysis. Be specific and actionable."
        ),
    },
    {
        "id": "prd",
        "name": "PRD Oluşturma",
        "description": "Product Requirements Document oluştur",
        "agent": "thinker",
        "prompt_template": (
            "IDEA-TO-PROJECT: PHASE 2 — PRD (Product Requirements Document)\n\n"
            "Original idea: {idea}\n"
            "Analysis from Phase 1:\n{prev_result}\n\n"
            "Create a professional PRD with:\n"
            "1. Project Name & One-liner\n"
            "2. Problem Statement\n"
            "3. Target Users & Personas\n"
            "4. Functional Requirements (numbered, prioritized P0/P1/P2)\n"
            "5. Non-Functional Requirements (performance, security, scalability)\n"
            "6. User Stories (As a [user], I want [action], so that [benefit])\n"
            "7. Success Metrics (KPIs)\n"
            "8. Out of Scope (what we're NOT building)\n"
            "9. Risks & Mitigations\n\n"
            "Be specific. This PRD should be ready for a dev team to implement."
        ),
    },
    {
        "id": "architecture",
        "name": "Teknik Mimari",
        "description": "Tech stack seçimi ve sistem mimarisi tasarımı",
        "agent": "reasoner",
        "prompt_template": (
            "IDEA-TO-PROJECT: PHASE 3 — TECHNICAL ARCHITECTURE\n\n"
            "Original idea: {idea}\n"
            "PRD from Phase 2:\n{prev_result}\n\n"
            "Design the technical architecture:\n"
            "1. Recommended Tech Stack (with justification for each choice)\n"
            "2. System Architecture Diagram (describe in text/mermaid)\n"
            "3. Database Schema (tables, relationships, key fields)\n"
            "4. API Endpoints (REST/GraphQL — list main endpoints)\n"
            "5. Authentication & Authorization strategy\n"
            "6. Deployment Architecture (cloud provider, services)\n"
            "7. Third-party Integrations needed\n"
            "8. Scalability considerations\n\n"
            "Choose modern, production-ready technologies. Justify trade-offs."
        ),
    },
    {
        "id": "tasks",
        "name": "Task Breakdown",
        "description": "İmplementasyon görevlerini sprint'lere böl",
        "agent": "speed",
        "prompt_template": (
            "IDEA-TO-PROJECT: PHASE 4 — TASK BREAKDOWN\n\n"
            "Original idea: {idea}\n"
            "Architecture from Phase 3:\n{prev_result}\n\n"
            "Create a detailed implementation plan:\n\n"
            "SPRINT 1 (MVP — 1-2 weeks):\n"
            "- List specific tasks with estimated hours\n"
            "- Include setup, core features, basic UI\n\n"
            "SPRINT 2 (Enhancement — 1-2 weeks):\n"
            "- Additional features, polish, testing\n\n"
            "SPRINT 3 (Launch — 1 week):\n"
            "- Deployment, monitoring, documentation\n\n"
            "For each task:\n"
            "- [ ] Task name (estimated hours) — brief description\n"
            "- Dependencies if any\n\n"
            "Be realistic with estimates. Include testing tasks."
        ),
    },
    {
        "id": "scaffold",
        "name": "Proje İskeleti",
        "description": "Dosya yapısı ve boilerplate kod üretimi",
        "agent": "speed",
        "prompt_template": (
            "IDEA-TO-PROJECT: PHASE 5 — PROJECT SCAFFOLD\n\n"
            "Original idea: {idea}\n"
            "Architecture:\n{prev_result}\n\n"
            "Generate the complete project file structure and key boilerplate files.\n\n"
            "For each file, provide:\n"
            "```filename: path/to/file.ext\n"
            "// file content here\n"
            "```\n\n"
            "Include at minimum:\n"
            "1. Project config files (package.json / pyproject.toml / etc.)\n"
            "2. Main entry point\n"
            "3. Database schema/models\n"
            "4. API route stubs\n"
            "5. Environment config (.env.example)\n"
            "6. README.md with setup instructions\n"
            "7. Dockerfile if applicable\n\n"
            "Write REAL, working code — not pseudocode. "
            "Include proper imports, types, and error handling."
        ),
    },
]


def get_phase_prompt(phase_id: str, idea: str, prev_result: str = "") -> str:
    """Build the prompt for a specific phase."""
    for phase in PHASES:
        if phase["id"] == phase_id:
            return phase["prompt_template"].format(
                idea=idea,
                prev_result=prev_result or "(no previous result)",
            )
    return ""


def get_phase_agent(phase_id: str) -> str:
    """Get the assigned agent role for a phase."""
    for phase in PHASES:
        if phase["id"] == phase_id:
            return phase["agent"]
    return "thinker"


def detect_project_type(idea: str) -> str:
    """Auto-detect project type from idea description."""
    idea_lower = idea.lower()

    patterns = {
        "mobile-app": r"(mobil|mobile|ios|android|react native|flutter|expo|uygulama|app\b)",
        "api-service": r"(api|backend|microservice|rest|graphql|fastapi|express|sunucu|server)",
        "cli-tool": r"(cli|command.?line|terminal|komut|script|otomasyon|automation)",
        "ai-agent": r"(agent|ai|yapay.?zeka|llm|chatbot|gpt|model|rag|langchain)",
        "data-pipeline": r"(data|veri|pipeline|etl|airflow|dbt|analytics|analitik)",
        "web-app": r"(web|site|sayfa|page|dashboard|panel|portal|e-?commerce|blog|saas)",
    }

    for ptype, pattern in patterns.items():
        if re.search(pattern, idea_lower):
            return ptype

    return "web-app"  # default


def save_project_output(project_name: str, phase_id: str, content: str) -> Path:
    """Save phase output to project directory."""
    safe_name = re.sub(r'[^\w\-]', '_', project_name.lower())[:50]
    project_dir = PROJECTS_DIR / safe_name
    project_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{phase_id}.md"
    filepath = project_dir / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath


def get_project_summary(project_name: str) -> dict[str, Any]:
    """Get summary of all phases for a project."""
    safe_name = re.sub(r'[^\w\-]', '_', project_name.lower())[:50]
    project_dir = PROJECTS_DIR / safe_name

    if not project_dir.exists():
        return {"name": project_name, "phases": {}, "exists": False}

    phases = {}
    for phase in PHASES:
        filepath = project_dir / f"{phase['id']}.md"
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            phases[phase["id"]] = {
                "name": phase["name"],
                "status": "completed",
                "preview": content[:200],
                "full_path": str(filepath),
            }
        else:
            phases[phase["id"]] = {
                "name": phase["name"],
                "status": "pending",
            }

    return {"name": project_name, "phases": phases, "exists": True}
