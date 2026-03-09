from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)
from deps import get_current_user, _audit
router = APIRouter()

# ── Shared Pydantic Models ───────────────────────────────────────

class MCPServerRequest(BaseModel):
    server_id: str
    url: str
    name: str = ""


class TeachRequest(BaseModel):
    content: str

# ── Skill Creator Endpoints ──────────────────────────────────────

class SkillGradeRequest(BaseModel):
    output_text: str
    expectations: list[str]
    strict: bool = False

class SkillValidateRequest(BaseModel):
    skill_path: str

class SkillBenchmarkRequest(BaseModel):
    workspace_dir: str
    skill_name: str = "unnamed-skill"

class EvalViewerRequest(BaseModel):
    workspace_dir: str
    skill_name: str = "unnamed-skill"
    benchmark_path: str = ""
    output_path: str = ""


@router.post("/api/skill-creator/grade")
async def api_skill_creator_grade(req: SkillGradeRequest):
    """Grade a skill output against expectations."""
    import re as _re
    results = []
    passed_count = 0
    output_lower = req.output_text.lower()

    for exp in req.expectations:
        exp_lower = exp.lower()
        key_terms = [w for w in _re.findall(r'\b\w{3,}\b', exp_lower)]

        if req.strict:
            found = exp_lower in output_lower
            evidence = f"Exact match {'found' if found else 'not found'}"
        else:
            matched_terms = [t for t in key_terms if t in output_lower]
            ratio = len(matched_terms) / max(len(key_terms), 1)
            found = ratio >= 0.6
            if found:
                evidence = f"Matched {len(matched_terms)}/{len(key_terms)} key terms: {', '.join(matched_terms[:5])}"
            else:
                missing = [t for t in key_terms if t not in output_lower]
                evidence = f"Only {len(matched_terms)}/{len(key_terms)} terms found. Missing: {', '.join(missing[:5])}"

        if found:
            passed_count += 1
        results.append({"text": exp, "passed": found, "evidence": evidence})

    total = len(req.expectations)
    return {
        "expectations": results,
        "summary": {
            "passed": passed_count,
            "failed": total - passed_count,
            "total": total,
            "pass_rate": round(passed_count / max(total, 1), 4),
        },
    }


@router.post("/api/skill-creator/validate")
async def api_skill_creator_validate(req: SkillValidateRequest):
    """Validate a SKILL.md file structure and quality."""
    import re as _re
    p = Path(req.skill_path)
    skill_md = p / "SKILL.md" if p.is_dir() else p
    skill_dir = skill_md.parent

    if not skill_md.exists():
        raise HTTPException(404, f"SKILL.md not found at {req.skill_path}")

    content = skill_md.read_text(errors="replace")
    lines = content.split("\n")
    issues, suggestions = [], []
    score = 100

    has_frontmatter = content.startswith("---")
    if not has_frontmatter:
        issues.append("Missing YAML frontmatter")
        score -= 30
    else:
        fm_end = content.find("---", 3)
        if fm_end == -1:
            issues.append("Unclosed YAML frontmatter")
            score -= 20
        else:
            fm = content[3:fm_end].strip()
            if "name:" not in fm:
                issues.append("Missing 'name' in frontmatter")
                score -= 15
            if "description:" not in fm:
                issues.append("Missing 'description' in frontmatter")
                score -= 20
            else:
                desc_match = _re.search(r'description:\s*(.+?)(?:\n[a-z]|\n---)', fm, _re.DOTALL)
                if desc_match:
                    desc = desc_match.group(1).strip().strip('"').strip("'")
                    if len(desc) < 30:
                        issues.append(f"Description too short ({len(desc)} chars)")
                        score -= 10
                    if "use when" not in desc.lower() and "use for" not in desc.lower():
                        suggestions.append("Add 'Use when...' trigger hints to description")

    line_count = len(lines)
    if line_count > 500:
        issues.append(f"SKILL.md is {line_count} lines — max recommended is 500")
        score -= 10

    for subdir, label in [(skill_dir / "references", "references"), (skill_dir / "scripts", "scripts"), (skill_dir / "assets", "assets")]:
        if subdir.exists():
            for f in subdir.iterdir():
                if f.is_file():
                    proper_link = f"(./{label}/{f.name})"
                    if proper_link not in content and f.name not in content:
                        issues.append(f"Bundled file {label}/{f.name} not referenced in SKILL.md")
                        score -= 5

    must_count = len(_re.findall(r'\bMUST\b', content))
    never_count = len(_re.findall(r'\bNEVER\b', content))
    always_count = len(_re.findall(r'\bALWAYS\b', content))
    if must_count + never_count + always_count > 10:
        suggestions.append(f"Found {must_count + never_count + always_count} heavy-handed directives — consider explaining WHY instead")

    score = max(0, min(100, score))
    return {
        "valid": len(issues) == 0,
        "score": score,
        "line_count": line_count,
        "issues": issues,
        "suggestions": suggestions,
        "has_frontmatter": has_frontmatter,
    }


@router.post("/api/skill-creator/benchmark")
async def api_skill_creator_benchmark(req: SkillBenchmarkRequest):
    """Aggregate grading results from workspace into benchmark stats."""
    ws = Path(req.workspace_dir)
    if not ws.is_dir():
        raise HTTPException(404, f"Directory not found: {req.workspace_dir}")

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "skill-creator" / "skills" / "skill-creator"))
        from scripts.aggregate_benchmark import generate_benchmark
        benchmark = generate_benchmark(ws, req.skill_name)
        return benchmark
    except ImportError:
        raise HTTPException(503, "aggregate_benchmark module not available")
    except Exception as e:
        raise HTTPException(500, f"Benchmark error: {e}")


@router.get("/api/skill-creator/search")
async def api_skill_creator_search(query: str = "", max_results: int = 10):
    """Search existing skills by keyword."""
    if not query:
        return []
    try:
        from tools.dynamic_skills import search_skills
        return search_skills(query, max_results=max_results)
    except Exception as e:
        raise HTTPException(500, f"Search error: {e}")


# ── Workflow Engine Endpoints ────────────────────────────────────

@router.get("/api/workflows/templates")
async def api_workflow_templates():
    """List available workflow templates."""
    try:
        from tools.workflow_engine import get_workflow_templates
        return get_workflow_templates()
    except Exception as e:
        raise HTTPException(503, f"Workflow engine error: {e}")


@router.get("/api/workflows/history")
async def api_workflow_history(limit: int = 20, user: dict = Depends(get_current_user)):
    """List recent workflow execution results."""
    try:
        from tools.workflow_engine import list_workflow_results
        return list_workflow_results(limit=limit)
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Workflow engine error: {e}")


class WorkflowRunRequest(BaseModel):
    template: str
    variables: dict = {}
    custom_steps: list[dict] | None = None


@router.post("/api/workflows/run")
async def api_run_workflow(req: WorkflowRunRequest, user: dict = Depends(get_current_user)):
    """Execute a workflow template or custom workflow."""
    try:
        from tools.workflow_engine import (
            WORKFLOW_TEMPLATES, create_workflow, execute_workflow, WorkflowStep, Workflow
        )
        from core.models import Thread as ThreadModel

        # Support both dict key ("research-and-report") and workflow_id ("tpl-research-and-report")
        resolved_key = None
        if req.template != "custom":
            if req.template in WORKFLOW_TEMPLATES:
                resolved_key = req.template
            else:
                # Lookup by workflow_id (e.g. "tpl-research-and-report")
                for k, wf in WORKFLOW_TEMPLATES.items():
                    if wf.workflow_id == req.template:
                        resolved_key = k
                        break

        if resolved_key is not None:
            tpl_workflow = WORKFLOW_TEMPLATES[resolved_key]
            workflow = Workflow(
                workflow_id=f"{resolved_key}-{int(__import__('time').time())}",
                name=tpl_workflow.name,
                description=tpl_workflow.description,
                steps=list(tpl_workflow.steps),
                variables={**tpl_workflow.variables, **(req.variables or {})},
            )
        elif req.template == "custom" and req.custom_steps:
            steps = [WorkflowStep(**s) for s in req.custom_steps]
            workflow = Workflow(
                workflow_id=f"custom-{int(__import__('time').time())}",
                name="Custom Workflow",
                description="User-defined workflow",
                steps=steps,
                variables=req.variables,
            )
        else:
            raise HTTPException(400, f"Unknown template: {req.template}")

        thread = ThreadModel()
        result = await execute_workflow(workflow, thread)
        return {
            "workflow_id": result.workflow_id,
            "status": result.status,
            "step_results": result.step_results,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "variables": result.variables,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Workflow execution error: {e}")


@router.get("/api/workflows/history/{workflow_id}")
async def api_workflow_detail(workflow_id: str, user: dict = Depends(get_current_user)):
    """Get detailed execution result for a specific workflow run."""
    try:
        from tools.workflow_engine import list_workflow_results
        results = list_workflow_results(limit=200)
        match = next((r for r in results if r.get("workflow_id") == workflow_id), None)
        if not match:
            raise HTTPException(404, "Workflow result not found")
        return match
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Error: {e}")


class ScheduleCreateRequest(BaseModel):
    template: str
    cron: str  # crontab expression: "*/30 * * * *"
    variables: dict = {}


class AIWorkflowImproveRequest(BaseModel):
    prompt: str


class AIWorkflowGenerateRequest(BaseModel):
    prompt: str


@router.get("/api/workflows/schedules")
async def api_list_schedules(user: dict = Depends(get_current_user)):
    """List all scheduled workflows."""
    try:
        from tools.workflow_scheduler import list_schedules
        return list_schedules()
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Scheduler module error: {e}")


@router.post("/api/workflows/schedules")
async def api_create_schedule(req: ScheduleCreateRequest, user: dict = Depends(get_current_user)):
    """Create a new cron-scheduled workflow."""
    try:
        from tools.workflow_scheduler import add_schedule
        return add_schedule(
            schedule_id=None,
            template=req.template,
            cron_expr=req.cron,
            variables=req.variables,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(503, f"Schedule error: {e}")


@router.delete("/api/workflows/schedules/{schedule_id}")
async def api_delete_schedule(schedule_id: str, user: dict = Depends(get_current_user)):
    """Delete a scheduled workflow."""
    try:
        from tools.workflow_scheduler import remove_schedule
        ok = remove_schedule(schedule_id)
        if not ok:
            raise HTTPException(404, "Schedule not found")
        return {"status": "deleted", "schedule_id": schedule_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Error: {e}")


@router.post("/api/workflows/schedules/{schedule_id}/toggle")
async def api_toggle_schedule(schedule_id: str, user: dict = Depends(get_current_user)):
    """Toggle a scheduled workflow on/off."""
    try:
        from tools.workflow_scheduler import toggle_schedule
        return toggle_schedule(schedule_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(503, f"Error: {e}")


@router.patch("/api/workflows/schedules/{schedule_id}")
async def api_patch_toggle_schedule(schedule_id: str, user: dict = Depends(get_current_user)):
    """PATCH toggle — frontend compat alias for POST .../toggle."""
    try:
        from tools.workflow_scheduler import toggle_schedule
        return toggle_schedule(schedule_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(503, f"Error: {e}")


# ── Domain Expert Endpoints ──────────────────────────────────────

@router.get("/api/domains")
async def api_list_domains():
    """List available domain expertise modules."""
    try:
        from tools.domain_skills import list_domains
        return list_domains()
    except Exception as e:
        raise HTTPException(503, f"Domain skills error: {e}")


@router.get("/api/domains/{domain_id}/tools")
async def api_domain_tools(domain_id: str):
    """List tools available in a specific domain."""
    try:
        from tools.domain_skills import get_domain_tools
        tools = get_domain_tools(domain_id)
        if tools is None:
            raise HTTPException(404, f"Domain not found: {domain_id}")
        return tools
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Domain skills error: {e}")


class DomainExpertRequest(BaseModel):
    domain: str
    tool_name: str
    arguments: dict = {}


@router.post("/api/domains/execute")
async def api_execute_domain_tool(req: DomainExpertRequest, user: dict = Depends(get_current_user)):
    """Execute a domain-specific tool."""
    try:
        from tools.domain_skills import execute_domain_tool
        result = await execute_domain_tool(req.domain, req.tool_name, req.arguments)
        return result
    except Exception as e:
        raise HTTPException(503, f"Domain execution error: {e}")

# ── Domain Auto-Discovery & Marketplace ──────────────────────────

class DomainDetectRequest(BaseModel):
    query: str
    top_k: int = 3

@router.post("/api/domains/auto-detect")
async def api_auto_detect_domain(req: DomainDetectRequest, user: dict = Depends(get_current_user)):
    """Auto-detect relevant domain(s) from a user query."""
    try:
        from tools.domain_skills import auto_detect_domain
        results = auto_detect_domain(req.query, req.top_k)
        return {"query": req.query, "matches": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(503, f"Domain detection error: {e}")

@router.get("/api/domains/marketplace")
async def api_domain_marketplace():
    """Get all domain skills with marketplace metadata."""
    try:
        from tools.domain_skills import get_marketplace_data
        return get_marketplace_data()
    except Exception as e:
        raise HTTPException(503, f"Marketplace error: {e}")

@router.post("/api/domains/discover")
async def api_discover_domains(user: dict = Depends(get_current_user)):
    """Trigger domain skill auto-discovery scan."""
    try:
        from tools.domain_skills import discover_domain_skills
        return discover_domain_skills()
    except Exception as e:
        raise HTTPException(503, f"Discovery error: {e}")

@router.post("/api/domains/{domain_id}/toggle")
async def api_toggle_domain(domain_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Enable or disable a domain skill."""
    try:
        from tools.domain_skills import toggle_domain_skill
        enabled = body.get("enabled", True)
        return toggle_domain_skill(domain_id, enabled)
    except Exception as e:
        raise HTTPException(503, f"Toggle error: {e}")

@router.get("/api/marketplace/catalog")
async def api_marketplace_catalog(
    category: str | None = None,
    search: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get unified skill marketplace catalog."""
    try:
        from tools.domain_skills import get_marketplace_catalog
        catalog = get_marketplace_catalog()

        # Filter by category
        if category and category != "all":
            catalog = [item for item in catalog if item.get("category") == category]

        # Search filter
        if search:
            search_lower = search.lower()
            catalog = [
                item for item in catalog
                if search_lower in item.get("name", "").lower()
                or search_lower in item.get("name_tr", "").lower()
                or search_lower in item.get("description", "").lower()
                or any(search_lower in tag.lower() for tag in item.get("tags", []))
            ]

        return {
            "items": catalog,
            "total": len(catalog),
            "categories": list(set(item.get("category", "other") for item in catalog)),
        }
    except Exception as e:
        raise HTTPException(503, f"Marketplace error: {e}")

@router.get("/api/marketplace/stats")
async def api_marketplace_stats(user: dict = Depends(get_current_user)):
    """Get marketplace statistics."""
    try:
        from tools.domain_skills import list_domains, get_marketplace_catalog
        domains = list_domains()
        catalog = get_marketplace_catalog()
        domain_items = [c for c in catalog if c["type"] == "domain"]
        skill_items = [c for c in catalog if c["type"] == "skill"]
        total_tools = sum(d.get("tool_count", 0) for d in domains)
        return {
            "total_items": len(catalog),
            "domain_count": len(domain_items),
            "skill_count": len(skill_items),
            "total_tools": total_tools,
            "categories": list(set(c.get("category", "other") for c in catalog)),
            "installed_count": len([c for c in catalog if c.get("installed")]),
        }
    except Exception as e:
        raise HTTPException(503, f"Marketplace stats error: {e}")



@router.get("/api/mcp/servers")
async def api_mcp_servers():
    try:
        from tools.mcp_client import list_servers
        return list_servers()
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"MCP module error: {e}")


@router.post("/api/mcp/servers")
async def api_add_mcp_server(req: MCPServerRequest):
    try:
        from tools.mcp_client import register_server
        return register_server(req.server_id, req.url, req.name)
    except Exception as e:
        raise HTTPException(503, f"MCP module error: {e}")


@router.post("/api/mcp/seed")
async def api_mcp_seed(overwrite: bool = False):
    """Re-seed default MCP servers. Use overwrite=true to reset configs."""
    try:
        from tools.mcp_client import seed_default_servers, DEFAULT_MCP_SERVERS
        count = seed_default_servers(overwrite=overwrite)
        return {
            "seeded": count,
            "total_defaults": len(DEFAULT_MCP_SERVERS),
            "message": f"{count} server kaydedildi" if count else "Tüm server'lar zaten kayıtlı",
        }
    except Exception as e:
        raise HTTPException(503, f"MCP seed error: {e}")


@router.get("/api/mcp/servers/{server_id}/tools")
async def api_mcp_tools(server_id: str):
    try:
        from tools.mcp_client import discover_tools
        return await discover_tools(server_id)
    except Exception as e:
        raise HTTPException(503, f"MCP module error: {e}")


@router.get("/api/teachability")
async def api_get_teachings():
    try:
        from tools.teachability import get_all_teachings
        return get_all_teachings()
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Teachability module error: {e}")


@router.post("/api/teachability")
async def api_add_teaching(req: TeachRequest):
    try:
        from tools.teachability import save_teaching
        return save_teaching(req.content)
    except Exception as e:
        raise HTTPException(503, f"Teachability module error: {e}")


@router.get("/api/eval/stats")
async def api_eval_stats():
    """Per-agent evaluation stats (task count, avg score)."""
    try:
        from tools.agent_eval import get_agent_stats
        return get_agent_stats()
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Eval module error: {e}")


@router.get("/api/eval/baseline")
async def api_eval_baseline(agent_role: str | None = None):
    """
    Performance baseline report (agent-orchestration-improve-agent skill).
    Returns: task_success_rate_pct, user_satisfaction_score, avg_latency_ms,
    token_efficiency_ratio, total_tasks, success_count.
    """
    try:
        from tools.agent_eval import get_performance_baseline
        return get_performance_baseline(agent_role)
    except Exception as e:
        raise HTTPException(503, "Baseline unavailable") from e


# ── AI Workflow Assistant Endpoints ──────────────────────────────

@router.post("/api/workflows/ai-improve-prompt")
async def api_ai_improve_workflow_prompt(req: AIWorkflowImproveRequest, user: dict = Depends(get_current_user)):
    """Improve a natural-language workflow description into a clear, structured prompt."""
    import httpx
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt boş olamaz")
    if not DEEPSEEK_API_KEY:
        raise HTTPException(503, "DeepSeek API anahtarı yapılandırılmamış")

    system = (
        "You are a workflow design assistant. The user describes a workflow in natural language (often in Turkish). "
        "Your job is to rewrite their description into a clear, structured workflow specification that an AI can parse. "
        "Output ONLY the improved prompt in the SAME LANGUAGE as the input. "
        "Make it specific: clarify steps, tools to use, agents to involve, conditions, and expected outputs. "
        "Do not add explanations or quotes. Output nothing but the improved workflow description."
    )
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1000,
        "temperature": 0.4,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            )
            if r.status_code != 200:
                raise HTTPException(502, f"DeepSeek hatası: {r.status_code}")
            data = r.json()
            choice = (data.get("choices") or [{}])[0]
            improved = (choice.get("message") or {}).get("content") or prompt
            improved = improved.strip().strip('"').strip("'")
            return {"improved_prompt": improved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Prompt iyileştirme hatası: {str(e)}")


@router.post("/api/workflows/ai-generate")
async def api_ai_generate_workflow(req: AIWorkflowGenerateRequest, user: dict = Depends(get_current_user)):
    """Generate a complete workflow definition from a natural-language prompt using DeepSeek."""
    import httpx
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt boş olamaz")
    if not DEEPSEEK_API_KEY:
        raise HTTPException(503, "DeepSeek API anahtarı yapılandırılmamış")

    # Build available tools/agents list for context
    tools_list = ", ".join([
        "web_search", "web_fetch", "code_execute", "rag_query", "rag_ingest",
        "save_memory", "recall_memory", "generate_image", "generate_chart",
        "mcp_call", "domain_expert", "decompose_task", "synthesize_results",
    ])
    agents_list = "thinker, speed, researcher, reasoner, critic"

    system = f"""You are a workflow generator for a multi-agent system. Given a natural-language description, generate a valid JSON workflow definition.

Available tools: {tools_list}
Available agents: {agents_list}

Output ONLY valid JSON with this exact structure (no markdown, no explanation):
{{
  "name": "Workflow Name",
  "description": "Brief description",
  "steps": [
    {{
      "step_id": "step_0",
      "step_type": "tool_call",
      "tool_name": "web_search",
      "tool_args": {{"query": "example"}},
      "on_error": "skip"
    }},
    {{
      "step_id": "step_1",
      "step_type": "agent_call",
      "agent_role": "thinker",
      "agent_prompt": "Analyze the results from {{{{step_0}}}}",
      "on_error": "rollback"
    }},
    {{
      "step_id": "step_2",
      "step_type": "condition",
      "condition": {{"field": "step_1", "operator": "contains", "value": "error", "then_step": "step_3", "else_step": "step_4"}},
      "on_error": "abort"
    }},
    {{
      "step_id": "step_3",
      "step_type": "parallel",
      "parallel_steps": ["step_4", "step_5"],
      "on_error": "rollback"
    }}
  ],
  "variables": {{}}
}}

Rules:
- step_type must be one of: tool_call, agent_call, condition, parallel
- Use {{{{step_id}}}} syntax to reference previous step outputs in prompts/args
- Keep workflows practical: 2-8 steps
- on_error: "skip" | "abort" | "rollback" | "retry"
- For agent_call: agent_role must be one of: {agents_list}
- For tool_call: tool_name must be from the available tools list
- Output ONLY the JSON object, nothing else"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2000,
        "temperature": 0.3,
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            )
            if r.status_code != 200:
                raise HTTPException(502, f"DeepSeek hatası: {r.status_code}")
            data = r.json()
            choice = (data.get("choices") or [{}])[0]
            raw = (choice.get("message") or {}).get("content") or ""
            raw = raw.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines).strip()

            import json as _json
            try:
                workflow_def = _json.loads(raw)
            except _json.JSONDecodeError:
                raise HTTPException(502, f"DeepSeek geçersiz JSON döndürdü: {raw[:200]}")

            # Validate basic structure
            if "steps" not in workflow_def or not isinstance(workflow_def["steps"], list):
                raise HTTPException(502, "Oluşturulan workflow'da 'steps' alanı eksik")

            return {
                "workflow": workflow_def,
                "raw_response": raw[:500],
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Workflow oluşturma hatası: {str(e)}")


# ── Presentation Archive Endpoints ────────────────────────────────

import json as _json
from datetime import datetime, timezone
from pathlib import Path as _Path

PRESENTATIONS_FILE = _Path(__file__).parent.parent / "data" / "presentations.json"

def _ensure_presentations_file():
    """Ensure presentations JSON file exists."""
    PRESENTATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not PRESENTATIONS_FILE.exists():
        PRESENTATIONS_FILE.write_text("[]", encoding="utf-8")

def _load_presentations() -> list[dict]:
    """Load presentations from JSON file."""
    _ensure_presentations_file()
    try:
        return _json.loads(PRESENTATIONS_FILE.read_text(encoding="utf-8"))
    except:
        return []

def _save_presentations(data: list[dict]):
    """Save presentations to JSON file."""
    _ensure_presentations_file()
    PRESENTATIONS_FILE.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class PresentationSaveRequest(BaseModel):
    title: str
    slides: list[dict]
    theme: str = "geist"
    style: str = "professional"
    palette_name: str = "Professional Blue"


class PresentationUpdateRequest(BaseModel):
    presentation_id: str
    title: str | None = None
    slides: list[dict] | None = None


@router.post("/api/presentations/save")
async def api_save_presentation(req: PresentationSaveRequest, user=Depends(get_current_user)):
    """Save a presentation to archive."""
    presentations = _load_presentations()
    
    presentation_id = f"pres-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    presentation = {
        "id": presentation_id,
        "title": req.title,
        "slides": req.slides,
        "slide_count": len(req.slides),
        "theme": req.theme,
        "style": req.style,
        "palette_name": req.palette_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "user": user.get("sub", "anonymous") if user else "anonymous",
    }
    
    presentations.insert(0, presentation)  # En başa ekle
    
    # Maksimum 50 sunum tut
    if len(presentations) > 50:
        presentations = presentations[:50]
    
    _save_presentations(presentations)
    _audit(user, "presentation_save", req.title)
    
    return {"success": True, "presentation_id": presentation_id, "presentation": presentation}


@router.get("/api/presentations/list")
async def api_list_presentations(user=Depends(get_current_user)):
    """List all saved presentations."""
    presentations = _load_presentations()
    
    # Sadece özet bilgileri döndür
    summaries = [
        {
            "id": p["id"],
            "title": p["title"],
            "slide_count": p["slide_count"],
            "theme": p.get("theme", "geist"),
            "style": p.get("style", "professional"),
            "palette_name": p.get("palette_name", "Professional Blue"),
            "created_at": p["created_at"],
            "updated_at": p.get("updated_at", p["created_at"]),
        }
        for p in presentations
    ]
    
    return {"presentations": summaries}


@router.get("/api/presentations/{presentation_id}")
async def api_get_presentation(presentation_id: str, user=Depends(get_current_user)):
    """Get a specific presentation by ID."""
    presentations = _load_presentations()
    
    for p in presentations:
        if p["id"] == presentation_id:
            return {"presentation": p}
    
    raise HTTPException(404, f"Sunum bulunamadı: {presentation_id}")


@router.delete("/api/presentations/{presentation_id}")
async def api_delete_presentation(presentation_id: str, user=Depends(get_current_user)):
    """Delete a presentation."""
    presentations = _load_presentations()
    
    for i, p in enumerate(presentations):
        if p["id"] == presentation_id:
            deleted = presentations.pop(i)
            _save_presentations(presentations)
            _audit(user, "presentation_delete", deleted["title"])
            return {"success": True, "deleted_id": presentation_id}
    
    raise HTTPException(404, f"Sunum bulunamadı: {presentation_id}")


@router.put("/api/presentations/{presentation_id}")
async def api_update_presentation(presentation_id: str, req: PresentationUpdateRequest, user=Depends(get_current_user)):
    """Update a presentation."""
    presentations = _load_presentations()
    
    for p in presentations:
        if p["id"] == presentation_id:
            if req.title:
                p["title"] = req.title
            if req.slides:
                p["slides"] = req.slides
                p["slide_count"] = len(req.slides)
            p["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_presentations(presentations)
            _audit(user, "presentation_update", p["title"])
            return {"success": True, "presentation": p}
    
    raise HTTPException(404, f"Sunum bulunamadı: {presentation_id}")


# ── User Feedback Endpoints (RLHF) ───────────────────────────────────────

class FeedbackRequest(BaseModel):
    thread_id: str
    agent_role: str
    rating: str  # "positive", "negative", "neutral"
    message_id: str = ""
    feedback_text: str = ""
    task_input: str = ""
    task_output: str = ""


class FeedbackStatsRequest(BaseModel):
    agent_role: str = ""
    days: int = 7


@router.post("/api/feedback/submit")
async def api_submit_feedback(req: FeedbackRequest, user=Depends(get_current_user)):
    """Submit user feedback for a response (👍👎)."""
    from tools.user_feedback import submit_feedback
    
    result = submit_feedback(
        thread_id=req.thread_id,
        agent_role=req.agent_role,
        rating=req.rating,
        message_id=req.message_id or None,
        user_id=user.get("user_id") if user else None,
        feedback_text=req.feedback_text or None,
        task_input=req.task_input or None,
        task_output=req.task_output or None,
    )
    
    if result["success"]:
        _audit(user, "feedback_submit", f"{req.rating} for {req.agent_role}")
    
    return result


@router.get("/api/feedback/thread/{thread_id}")
async def api_get_thread_feedback(thread_id: str, user=Depends(get_current_user)):
    """Get all feedback for a thread."""
    from tools.user_feedback import get_feedback_for_thread
    
    feedback = get_feedback_for_thread(thread_id)
    return {"feedback": feedback}


@router.get("/api/feedback/stats")
async def api_get_feedback_stats(agent_role: str = "", user=Depends(get_current_user)):
    """Get aggregated feedback stats for agents."""
    from tools.user_feedback import get_agent_feedback_stats
    
    stats = get_agent_feedback_stats(agent_role or None)
    return {"stats": stats}


@router.get("/api/feedback/leaderboard")
async def api_get_feedback_leaderboard(limit: int = 10, user=Depends(get_current_user)):
    """Get agents ranked by satisfaction rate."""
    from tools.user_feedback import get_feedback_leaderboard
    
    leaderboard = get_feedback_leaderboard(limit)
    return {"leaderboard": leaderboard}


@router.get("/api/feedback/trends")
async def api_get_feedback_trends(days: int = 7, user=Depends(get_current_user)):
    """Get feedback trends over time."""
    from tools.user_feedback import get_feedback_trends
    
    trends = get_feedback_trends(days)
    return trends


@router.get("/api/feedback/rlhf-data")
async def api_get_rlhf_data(limit: int = 100, user=Depends(get_current_user)):
    """Get training data for RLHF."""
    from tools.user_feedback import get_rlhf_training_data
    
    data = get_rlhf_training_data(limit)
    return data