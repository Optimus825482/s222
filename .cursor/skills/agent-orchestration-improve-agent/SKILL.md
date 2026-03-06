---
name: agent-orchestration-improve-agent
description: "Systematic improvement of existing agents through performance analysis, prompt engineering, and continuous iteration. Use when improving an agent's performance or reliability, analyzing failure modes or prompt quality, running A/B tests or evaluation suites, or designing iterative optimization workflows."
---

# Agent Performance Optimization Workflow

Systematic improvement of existing agents through performance analysis, prompt engineering, and continuous iteration. Use a data-driven approach: baseline metrics, failure analysis, targeted prompt/workflow changes, then validation with tests and staged rollout.

## Use this skill when

- Improving an existing agent's performance or reliability
- Analyzing failure modes, prompt quality, or tool usage
- Running structured A/B tests or evaluation suites
- Designing iterative optimization workflows for agents

## Do not use this skill when

- Building a brand-new agent from scratch
- No metrics, feedback, or test cases are available
- The task is unrelated to agent performance or prompt quality

## Instructions (high level)

1. **Establish baseline** — Collect metrics and representative examples (e.g. `context-manager analyze-agent-performance $ARGUMENTS --days 30`).
2. **Identify failure modes** — Classify by root cause; prioritize high-impact fixes.
3. **Apply improvements** — Prompt/workflow changes with measurable goals (chain-of-thought, few-shot, role refinement, constitutional checks, output format).
4. **Validate** — Test suite + A/B comparison; roll out in stages with rollback triggers.

## Safety

- Do not deploy prompt changes without regression testing.
- Roll back quickly if quality or safety metrics regress.

## Phase 1: Performance analysis and baseline

- **Gather data**: Task completion rate, accuracy, tool usage, latency, token use, user corrections/retries, hallucination/error patterns.
- **Feedback patterns**: Correction patterns, clarification requests, abandonment points, follow-up questions, positive patterns to preserve.
- **Failure classification**: Instruction misunderstanding, output format errors, context loss, tool misuse, constraint violations, edge cases.
- **Baseline report** (quantitative):
  - Task success rate (%)
  - Average corrections per task
  - Tool call efficiency (%)
  - User satisfaction score (1–10)
  - Average response latency
  - Token efficiency ratio

## Phase 2: Prompt engineering improvements

- **Chain-of-thought**: Explicit reasoning steps, self-verification checkpoints, recursive decomposition, reasoning trace for debugging.
- **Few-shot**: Diverse examples (common + edge cases), good/bad examples with explanations, simple→complex order, annotated decision points.
- **Role definition**: Core purpose, expertise domains, behavioral traits, tool proficiency and when to use, constraints, success criteria.
- **Constitutional AI**: Principles (verify accuracy, self-check bias/harm, validate format, completeness, consistency); critique-and-revise loop before output.
- **Output format**: Structured templates, dynamic formatting by complexity, progressive disclosure, markdown/code/tables tuned for readability.

## Phase 3: Testing and validation

- **Test suite**: Golden path, previously failed tasks (regression), edge cases, stress tests, adversarial inputs, cross-domain tasks.
- **A/B testing**: Original vs improved agent; ~100+ tasks per variant; 95% confidence (p < 0.05); effect size; blind human review + automated scoring.
- **Metrics**: Completion rate, correctness, efficiency, tool appropriateness, relevance, hallucination rate, consistency, format compliance, safety, latency, tokens, cost.
- **Human evaluation**: Blind review, standardized rubric, multiple evaluators, preference ranking (A vs B).

## Phase 4: Version control and deployment

- **Versioning**: `agent-name-v[MAJOR].[MINOR].[PATCH]`; git-based prompts; changelog; metrics per version; documented rollback.
- **Staged rollout**: Alpha (internal, ~5%) → Beta (~20%) → Canary (20%→50%→100%) → Full deployment → 7-day monitoring.
- **Rollback triggers**: Success rate drop >10%, critical errors +>5%, complaint spike, cost per task +>20%, safety violations.
- **Rollback process**: Detect → alert → switch to previous stable → analyze root cause → fix and re-test before retry.
- **Monitoring**: Dashboard, anomaly alerts, feedback collection, automated regression, weekly reports.

## Success criteria

- Task success rate improves ≥15%
- User corrections decrease ≥25%
- No increase in safety violations
- Response time within 10% of baseline
- Cost per task increase ≤5%
- Positive user feedback increases

## Continuous improvement

- **Weekly**: Monitor metrics and collect feedback
- **Monthly**: Analyze patterns and plan improvements
- **Quarterly**: Major version updates
- **Post 30-day**: Compare to baseline/targets, document lessons, plan next cycle

For detailed phase steps, commands, code patterns, evaluation protocols, and **prompt analysis structure** (Kiro prompt-engineer), see [reference.md](reference.md).
