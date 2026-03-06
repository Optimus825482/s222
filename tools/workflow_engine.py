"""
Workflow Engine — chains tools/agents with conditional branching,
error handling, parallel execution, and rollback support.

Enables declarative multi-step workflows where each step can be a tool call,
agent call, condition branch, parallel fan-out, or human approval gate.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from core.models import AgentRole, EventType, Thread

logger = logging.getLogger(__name__)


# ── Data Models ──────────────────────────────────────────────────


@dataclass
class WorkflowStep:
    """Single step in a workflow pipeline."""

    step_id: str
    step_type: Literal["tool_call", "agent_call", "condition", "parallel", "human_approval"]

    # tool_call fields
    tool_name: str | None = None
    tool_args: dict | None = None

    # agent_call fields
    agent_role: str | None = None
    agent_prompt: str | None = None

    # condition fields — {"field", "operator", "value", "then_step", "else_step"}
    condition: dict | None = None

    # parallel fields — step_ids to run concurrently
    parallel_steps: list[str] | None = None

    # error handling
    on_error: Literal["retry", "skip", "abort", "rollback"] = "abort"
    retry_count: int = 2
    compensation: dict | None = None  # rollback action: {"tool_name": str, "tool_args": dict}
    timeout_seconds: int = 60


@dataclass
class Workflow:
    """Declarative workflow definition."""

    workflow_id: str
    name: str
    description: str
    steps: list[WorkflowStep]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Outcome of a workflow execution."""

    workflow_id: str
    status: Literal["completed", "failed", "rolled_back", "partial"]
    step_results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    variables: dict[str, Any] = field(default_factory=dict)


# ── Variable Interpolation ───────────────────────────────────────

_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def interpolate_variables(text: str, variables: dict[str, Any]) -> str:
    """Replace {{variable_name}} placeholders with values from the variables dict."""
    if not text:
        return text

    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        val = variables.get(key)
        if val is None:
            return match.group(0)  # leave unresolved placeholders as-is
        return str(val)

    return _VAR_PATTERN.sub(_replacer, text)


def _interpolate_dict(d: dict | None, variables: dict[str, Any]) -> dict:
    """Deep-interpolate all string values in a dict."""
    if not d:
        return {}
    result = {}
    for k, v in d.items():
        if isinstance(v, str):
            result[k] = interpolate_variables(v, variables)
        elif isinstance(v, dict):
            result[k] = _interpolate_dict(v, variables)
        elif isinstance(v, list):
            result[k] = [
                interpolate_variables(item, variables) if isinstance(item, str) else item
                for item in v
            ]
        else:
            result[k] = v
    return result


# ── Tool Dispatch ────────────────────────────────────────────────

# Maps tool names to their async/sync callables.
# Lazy-loaded to avoid circular imports at module level.

_TOOL_REGISTRY: dict[str, Any] | None = None


def _get_tool_registry() -> dict[str, Any]:
    """Build tool name → callable mapping on first use."""
    global _TOOL_REGISTRY
    if _TOOL_REGISTRY is not None:
        return _TOOL_REGISTRY

    from tools.search import web_search
    from tools.web_fetch import web_fetch
    from tools.code_executor import execute_code
    from tools.rag import query_documents, ingest_document
    from tools.memory import save_memory, recall_memory

    _TOOL_REGISTRY = {
        "web_search": web_search,
        "web_fetch": web_fetch,
        "code_execute": execute_code,
        "execute_code": execute_code,
        "rag_query": query_documents,
        "query_documents": query_documents,
        "rag_ingest": ingest_document,
        "save_memory": save_memory,
        "recall_memory": recall_memory,
    }
    return _TOOL_REGISTRY


# ── Step Executors ───────────────────────────────────────────────


async def _execute_tool_step(
    step: WorkflowStep,
    variables: dict[str, Any],
    thread: Thread | None,
) -> str:
    """Execute a tool_call step and return the result as a string."""
    registry = _get_tool_registry()
    tool_fn = registry.get(step.tool_name or "")
    if tool_fn is None:
        raise ValueError(f"Unknown tool: {step.tool_name}")

    args = _interpolate_dict(step.tool_args, variables)

    if thread:
        thread.add_event(
            EventType.TOOL_CALL,
            f"[workflow] Calling tool '{step.tool_name}' with args: {json.dumps(args, ensure_ascii=False)[:200]}",
        )

    # Call — handle both sync and async tools
    if asyncio.iscoroutinefunction(tool_fn):
        result = await tool_fn(**args)
    else:
        result = await asyncio.to_thread(tool_fn, **args)

    result_str = json.dumps(result, ensure_ascii=False, default=str) if not isinstance(result, str) else result

    if thread:
        thread.add_event(
            EventType.TOOL_RESULT,
            f"[workflow] Tool '{step.tool_name}' returned ({len(result_str)} chars)",
        )

    return result_str


async def _execute_agent_step(
    step: WorkflowStep,
    variables: dict[str, Any],
    thread: Thread | None,
) -> str:
    """Execute an agent_call step via PipelineEngine."""
    from pipelines.engine import PipelineEngine

    role = AgentRole(step.agent_role)
    prompt = interpolate_variables(step.agent_prompt or "", variables)

    if thread:
        thread.add_event(
            EventType.AGENT_START,
            f"[workflow] Agent '{role.value}' starting: {prompt[:120]}...",
            agent_role=role,
        )

    engine = PipelineEngine()
    agent = engine.get_agent(role)
    result = await asyncio.wait_for(
        agent.execute(prompt, thread or Thread()),
        timeout=step.timeout_seconds,
    )

    if thread:
        thread.add_event(
            EventType.AGENT_RESPONSE,
            f"[workflow] Agent '{role.value}' responded ({len(result)} chars)",
            agent_role=role,
        )

    return result


async def _execute_condition_step(
    step: WorkflowStep,
    variables: dict[str, Any],
) -> str:
    """Evaluate a condition and return the next step_id to execute."""
    cond = step.condition
    if not cond:
        raise ValueError(f"Step '{step.step_id}' is a condition but has no condition dict")

    field_name: str = cond["field"]
    operator: str = cond["operator"]
    expected = cond["value"]
    then_step: str = cond["then_step"]
    else_step: str = cond["else_step"]

    actual = variables.get(field_name)

    matched = False
    match operator:
        case "eq" | "==":
            matched = str(actual) == str(expected)
        case "neq" | "!=":
            matched = str(actual) != str(expected)
        case "contains":
            matched = str(expected).lower() in str(actual).lower()
        case "not_contains":
            matched = str(expected).lower() not in str(actual).lower()
        case "gt" | ">":
            matched = float(actual or 0) > float(expected)
        case "lt" | "<":
            matched = float(actual or 0) < float(expected)
        case "gte" | ">=":
            matched = float(actual or 0) >= float(expected)
        case "lte" | "<=":
            matched = float(actual or 0) <= float(expected)
        case "exists":
            matched = actual is not None
        case "empty":
            matched = not actual
        case _:
            raise ValueError(f"Unknown condition operator: {operator}")

    logger.info(
        "Condition '%s': %s %s %s → %s (next: %s)",
        step.step_id, field_name, operator, expected, matched,
        then_step if matched else else_step,
    )
    return then_step if matched else else_step


async def _execute_parallel_steps(
    step_ids: list[str],
    all_steps: dict[str, WorkflowStep],
    variables: dict[str, Any],
    thread: Thread | None,
) -> dict[str, Any]:
    """Run multiple steps concurrently and collect results keyed by step_id."""
    async def _run_one(sid: str) -> tuple[str, Any]:
        s = all_steps.get(sid)
        if s is None:
            return sid, f"[error] Step '{sid}' not found"
        result = await _execute_step(s, variables, thread)
        return sid, result

    tasks = [_run_one(sid) for sid in step_ids]
    pairs = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict[str, Any] = {}
    for item in pairs:
        if isinstance(item, Exception):
            logger.error("Parallel step exception: %s", item)
            continue
        sid, val = item
        results[sid] = val
    return results


async def _execute_step(
    step: WorkflowStep,
    variables: dict[str, Any],
    thread: Thread | None,
) -> Any:
    """Dispatch a single step by its type."""
    match step.step_type:
        case "tool_call":
            return await _execute_tool_step(step, variables, thread)
        case "agent_call":
            return await _execute_agent_step(step, variables, thread)
        case "condition":
            return await _execute_condition_step(step, variables)
        case "parallel":
            step_map = {}  # caller must provide — handled in execute_workflow
            raise RuntimeError("Parallel steps are handled by execute_workflow directly")
        case "human_approval":
            return await _execute_human_approval(step, variables, thread)
        case _:
            raise ValueError(f"Unknown step_type: {step.step_type}")


async def _execute_human_approval(
    step: WorkflowStep,
    variables: dict[str, Any],
    thread: Thread | None,
) -> str:
    """Gate execution until human approval is received (or auto-approve in headless mode)."""
    prompt_text = interpolate_variables(step.agent_prompt or "Approval required to continue.", variables)

    if thread:
        thread.add_event(
            EventType.HUMAN_REQUEST,
            f"[workflow] Human approval requested: {prompt_text}",
        )

    # Try the human_loop tool if available; otherwise auto-approve with warning
    try:
        from tools.human_loop import request_human_approval
        approved = await request_human_approval(prompt_text)
        if not approved:
            raise RuntimeError(f"Human rejected step '{step.step_id}': {prompt_text}")
    except ImportError:
        logger.warning("human_loop not available — auto-approving step '%s'", step.step_id)

    if thread:
        thread.add_event(
            EventType.HUMAN_RESPONSE,
            f"[workflow] Step '{step.step_id}' approved",
        )

    return "approved"


async def _rollback(
    executed_steps: list[str],
    all_steps: dict[str, WorkflowStep],
    variables: dict[str, Any],
) -> None:
    """Execute compensation actions in reverse order for rolled-back steps."""
    for step_id in reversed(executed_steps):
        step = all_steps.get(step_id)
        if not step or not step.compensation:
            continue

        comp = step.compensation
        tool_name = comp.get("tool_name")
        tool_args = _interpolate_dict(comp.get("tool_args", {}), variables)

        logger.info("Rolling back step '%s' via tool '%s'", step_id, tool_name)
        try:
            registry = _get_tool_registry()
            fn = registry.get(tool_name or "")
            if fn is None:
                logger.warning("Compensation tool '%s' not found — skipping", tool_name)
                continue
            if asyncio.iscoroutinefunction(fn):
                await fn(**tool_args)
            else:
                await asyncio.to_thread(fn, **tool_args)
        except Exception as e:
            logger.error("Rollback failed for step '%s': %s", step_id, e)


# ── Main Workflow Executor ───────────────────────────────────────


async def execute_workflow(
    workflow: Workflow,
    thread: Thread | None = None,
) -> WorkflowResult:
    """
    Execute a full workflow: iterate steps, handle conditions, parallel fan-out,
    retries, error policies, and rollback.

    Each step's result is stored in workflow.variables under its step_id,
    making it available for interpolation in subsequent steps.
    """
    t0 = time.monotonic()
    variables = dict(workflow.variables)
    step_map: dict[str, WorkflowStep] = {s.step_id: s for s in workflow.steps}
    step_results: dict[str, Any] = {}
    executed_steps: list[str] = []

    if thread:
        thread.add_event(
            EventType.PIPELINE_START,
            f"[workflow] Starting '{workflow.name}' ({len(workflow.steps)} steps)",
        )

    # Build ordered execution list (linear by default; conditions/parallel alter flow)
    step_order = [s.step_id for s in workflow.steps]
    idx = 0

    while idx < len(step_order):
        step_id = step_order[idx]
        step = step_map.get(step_id)
        if step is None:
            logger.warning("Step '%s' not found in workflow — skipping", step_id)
            idx += 1
            continue

        # ── Parallel fan-out ─────────────────────────────────────
        if step.step_type == "parallel" and step.parallel_steps:
            try:
                parallel_results = await asyncio.wait_for(
                    _execute_parallel_steps(step.parallel_steps, step_map, variables, thread),
                    timeout=step.timeout_seconds,
                )
                step_results[step_id] = parallel_results
                for sid, val in parallel_results.items():
                    variables[sid] = val
                    step_results[sid] = val
                    executed_steps.append(sid)
                variables[step_id] = json.dumps(parallel_results, ensure_ascii=False, default=str)
                executed_steps.append(step_id)
                idx += 1
                continue
            except Exception as e:
                return await _handle_step_error(
                    step, e, variables, step_results, executed_steps,
                    step_map, workflow, t0, thread,
                )

        # ── Condition branching ──────────────────────────────────
        if step.step_type == "condition":
            try:
                next_step_id = await _execute_condition_step(step, variables)
                step_results[step_id] = next_step_id
                executed_steps.append(step_id)
                # Jump to the target step
                if next_step_id in step_map:
                    try:
                        target_idx = step_order.index(next_step_id)
                        idx = target_idx
                    except ValueError:
                        # Target not in linear order — append and jump
                        step_order.append(next_step_id)
                        idx = len(step_order) - 1
                else:
                    idx += 1
                continue
            except Exception as e:
                return await _handle_step_error(
                    step, e, variables, step_results, executed_steps,
                    step_map, workflow, t0, thread,
                )

        # ── Normal step execution with retry ─────────────────────
        last_error: Exception | None = None
        attempts = step.retry_count + 1 if step.on_error == "retry" else 1

        for attempt in range(1, attempts + 1):
            try:
                result = await asyncio.wait_for(
                    _execute_step(step, variables, thread),
                    timeout=step.timeout_seconds,
                )
                step_results[step_id] = result
                variables[step_id] = result
                executed_steps.append(step_id)
                last_error = None
                break
            except Exception as e:
                last_error = e
                logger.warning(
                    "Step '%s' attempt %d/%d failed: %s",
                    step_id, attempt, attempts, e,
                )
                if attempt < attempts:
                    await asyncio.sleep(min(attempt * 0.5, 3))  # backoff

        if last_error is not None:
            err_result = await _handle_step_error(
                step, last_error, variables, step_results, executed_steps,
                step_map, workflow, t0, thread,
            )
            if err_result is not None:
                return err_result
            # on_error == "skip" returns None from _handle_step_error → continue

        idx += 1

    # ── Success ──────────────────────────────────────────────────
    duration_ms = (time.monotonic() - t0) * 1000

    if thread:
        thread.add_event(
            EventType.PIPELINE_COMPLETE,
            f"[workflow] '{workflow.name}' completed in {duration_ms:.0f}ms",
        )

    result = WorkflowResult(
        workflow_id=workflow.workflow_id,
        status="completed",
        step_results=step_results,
        duration_ms=duration_ms,
        variables=variables,
    )

    # Persist to PostgreSQL (fire-and-forget)
    try:
        save_workflow_result(result)
    except Exception as e:
        logger.warning("Failed to persist workflow result: %s", e)

    return result


async def _handle_step_error(
    step: WorkflowStep,
    error: Exception,
    variables: dict[str, Any],
    step_results: dict[str, Any],
    executed_steps: list[str],
    step_map: dict[str, WorkflowStep],
    workflow: Workflow,
    t0: float,
    thread: Thread | None,
) -> WorkflowResult | None:
    """
    Apply the step's on_error policy.
    Returns a WorkflowResult for abort/rollback, or None for skip (continue).
    """
    error_msg = f"Step '{step.step_id}' failed: {error}"
    logger.error(error_msg)

    if thread:
        thread.add_event(EventType.ERROR, f"[workflow] {error_msg}")

    duration_ms = (time.monotonic() - t0) * 1000

    match step.on_error:
        case "skip":
            step_results[step.step_id] = f"[skipped] {error}"
            variables[step.step_id] = None
            return None  # signal caller to continue

        case "rollback":
            await _rollback(executed_steps, step_map, variables)
            return WorkflowResult(
                workflow_id=workflow.workflow_id,
                status="rolled_back",
                step_results=step_results,
                error=error_msg,
                duration_ms=duration_ms,
                variables=variables,
            )

        case "abort" | _:
            return WorkflowResult(
                workflow_id=workflow.workflow_id,
                status="failed",
                step_results=step_results,
                error=error_msg,
                duration_ms=duration_ms,
                variables=variables,
            )


# ── Template Workflows ───────────────────────────────────────────

WORKFLOW_TEMPLATES: dict[str, Workflow] = {
    "research-and-report": Workflow(
        workflow_id="tpl-research-and-report",
        name="Research and Report",
        description="Researcher searches → Thinker analyzes → Speed formats → save to memory",
        steps=[
            WorkflowStep(
                step_id="search",
                step_type="tool_call",
                tool_name="web_search",
                tool_args={"query": "{{topic}}", "max_results": 5},
                on_error="retry",
                retry_count=2,
            ),
            WorkflowStep(
                step_id="analyze",
                step_type="agent_call",
                agent_role="thinker",
                agent_prompt=(
                    "Analyze the following search results about '{{topic}}':\n\n"
                    "{{search}}\n\n"
                    "Provide a structured analysis with key findings, patterns, and insights."
                ),
                timeout_seconds=90,
            ),
            WorkflowStep(
                step_id="format",
                step_type="agent_call",
                agent_role="speed",
                agent_prompt=(
                    "Format the following analysis into a clean, readable report:\n\n"
                    "{{analyze}}\n\n"
                    "Use clear headings, bullet points, and a summary section."
                ),
                timeout_seconds=60,
            ),
            WorkflowStep(
                step_id="save",
                step_type="tool_call",
                tool_name="save_memory",
                tool_args={
                    "content": "Research report on '{{topic}}': {{format}}",
                    "category": "research",
                },
                on_error="skip",
            ),
        ],
        variables={"topic": ""},
    ),
    "code-review-pipeline": Workflow(
        workflow_id="tpl-code-review-pipeline",
        name="Code Review Pipeline",
        description="Lint code → Thinker reviews → Reasoner verifies → Speed formats report",
        steps=[
            WorkflowStep(
                step_id="lint",
                step_type="tool_call",
                tool_name="code_execute",
                tool_args={"code": "{{code}}", "language": "{{language}}"},
                on_error="skip",
                timeout_seconds=30,
            ),
            WorkflowStep(
                step_id="review",
                step_type="agent_call",
                agent_role="thinker",
                agent_prompt=(
                    "Review this code for bugs, security issues, and best practices:\n\n"
                    "```{{language}}\n{{code}}\n```\n\n"
                    "Lint output:\n{{lint}}\n\n"
                    "Provide detailed findings with severity levels."
                ),
                timeout_seconds=90,
            ),
            WorkflowStep(
                step_id="verify",
                step_type="agent_call",
                agent_role="reasoner",
                agent_prompt=(
                    "Verify and challenge this code review. Are the findings accurate? "
                    "Any false positives or missed issues?\n\n"
                    "Review:\n{{review}}\n\n"
                    "Original code:\n```{{language}}\n{{code}}\n```"
                ),
                timeout_seconds=90,
            ),
            WorkflowStep(
                step_id="report",
                step_type="agent_call",
                agent_role="speed",
                agent_prompt=(
                    "Create a final code review report combining these findings:\n\n"
                    "Review: {{review}}\n\nVerification: {{verify}}\n\n"
                    "Format as: Summary → Critical Issues → Warnings → Suggestions"
                ),
                timeout_seconds=60,
            ),
        ],
        variables={"code": "", "language": "python"},
    ),
    "deep-analysis": Workflow(
        workflow_id="tpl-deep-analysis",
        name="Deep Analysis",
        description="Parallel research/think/reason → synthesize → save to memory",
        steps=[
            WorkflowStep(
                step_id="gather",
                step_type="parallel",
                parallel_steps=["research", "think", "reason"],
                timeout_seconds=120,
            ),
            WorkflowStep(
                step_id="research",
                step_type="agent_call",
                agent_role="researcher",
                agent_prompt="Research and gather evidence about: {{topic}}",
                timeout_seconds=90,
            ),
            WorkflowStep(
                step_id="think",
                step_type="agent_call",
                agent_role="thinker",
                agent_prompt="Provide deep strategic analysis of: {{topic}}",
                timeout_seconds=90,
            ),
            WorkflowStep(
                step_id="reason",
                step_type="agent_call",
                agent_role="reasoner",
                agent_prompt="Identify risks, edge cases, and logical flaws in: {{topic}}",
                timeout_seconds=90,
            ),
            WorkflowStep(
                step_id="synthesize",
                step_type="agent_call",
                agent_role="speed",
                agent_prompt=(
                    "Synthesize these parallel analyses into a unified report:\n\n"
                    "Research: {{research}}\n\n"
                    "Strategic Analysis: {{think}}\n\n"
                    "Risk Assessment: {{reason}}\n\n"
                    "Create a comprehensive summary with actionable conclusions."
                ),
                timeout_seconds=90,
            ),
            WorkflowStep(
                step_id="persist",
                step_type="tool_call",
                tool_name="save_memory",
                tool_args={
                    "content": "Deep analysis on '{{topic}}': {{synthesize}}",
                    "category": "research",
                },
                on_error="skip",
            ),
        ],
        variables={"topic": ""},
    ),
}


# ── Helper Functions ─────────────────────────────────────────────


def create_workflow(
    name: str,
    description: str,
    steps_config: list[dict[str, Any]],
    variables: dict[str, Any] | None = None,
) -> Workflow:
    """Create a Workflow from a list of step dicts (convenience builder)."""
    steps = []
    for cfg in steps_config:
        step = WorkflowStep(
            step_id=cfg.get("step_id", f"step-{uuid.uuid4().hex[:6]}"),
            step_type=cfg.get("step_type", "tool_call"),
            tool_name=cfg.get("tool_name"),
            tool_args=cfg.get("tool_args"),
            agent_role=cfg.get("agent_role"),
            agent_prompt=cfg.get("agent_prompt"),
            condition=cfg.get("condition"),
            parallel_steps=cfg.get("parallel_steps"),
            on_error=cfg.get("on_error", "abort"),
            retry_count=cfg.get("retry_count", 2),
            compensation=cfg.get("compensation"),
            timeout_seconds=cfg.get("timeout_seconds", 60),
        )
        steps.append(step)

    return Workflow(
        workflow_id=f"wf-{uuid.uuid4().hex[:8]}",
        name=name,
        description=description,
        steps=steps,
        variables=variables or {},
    )


def get_workflow_templates() -> list[dict[str, Any]]:
    """Return metadata for all available workflow templates."""
    return [
        {
            "id": wf.workflow_id,
            "name": wf.name,
            "description": wf.description,
            "step_count": len(wf.steps),
            "required_variables": list(wf.variables.keys()),
        }
        for wf in WORKFLOW_TEMPLATES.values()
    ]


def get_template(template_name: str, variables: dict[str, Any] | None = None) -> Workflow:
    """
    Clone a template workflow with fresh IDs and optional variable overrides.
    Raises KeyError if template_name is not found.
    """
    tpl = WORKFLOW_TEMPLATES.get(template_name)
    if tpl is None:
        available = ", ".join(WORKFLOW_TEMPLATES.keys())
        raise KeyError(f"Template '{template_name}' not found. Available: {available}")

    import copy
    wf = copy.deepcopy(tpl)
    wf.workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
    if variables:
        wf.variables.update(variables)
    return wf


# ── PostgreSQL Persistence ───────────────────────────────────────

_TABLE_CREATED = False


def _ensure_table() -> None:
    """Create workflow_results table if it doesn't exist."""
    global _TABLE_CREATED
    if _TABLE_CREATED:
        return

    from tools.pg_connection import db_conn

    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workflow_results (
                    id              SERIAL PRIMARY KEY,
                    workflow_id     TEXT NOT NULL,
                    status          TEXT NOT NULL,
                    step_results    JSONB NOT NULL DEFAULT '{}',
                    error           TEXT,
                    duration_ms     REAL NOT NULL DEFAULT 0,
                    variables       JSONB NOT NULL DEFAULT '{}',
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_wfr_workflow_id ON workflow_results(workflow_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_wfr_created ON workflow_results(created_at DESC)
            """)
        conn.commit()

    _TABLE_CREATED = True


def save_workflow_result(result: WorkflowResult) -> None:
    """Persist a workflow execution result to PostgreSQL."""
    _ensure_table()

    from tools.pg_connection import get_conn, release_conn

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflow_results
                    (workflow_id, status, step_results, error, duration_ms, variables)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    result.workflow_id,
                    result.status,
                    json.dumps(result.step_results, ensure_ascii=False, default=str),
                    result.error,
                    result.duration_ms,
                    json.dumps(result.variables, ensure_ascii=False, default=str),
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_conn(conn)


def list_workflow_results(limit: int = 20) -> list[dict[str, Any]]:
    """Retrieve recent workflow execution results."""
    _ensure_table()

    from tools.pg_connection import get_conn, release_conn

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, workflow_id, status, step_results, error,
                       duration_ms, variables, created_at
                FROM workflow_results
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows] if rows else []
    finally:
        release_conn(conn)
