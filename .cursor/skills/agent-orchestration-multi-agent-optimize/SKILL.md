---
name: agent-orchestration-multi-agent-optimize
description: "Optimize multi-agent systems with coordinated profiling, workload distribution, and cost-aware orchestration. Use when improving agent performance, throughput, or reliability; profiling agent workflows for bottlenecks; or designing orchestration for complex workflows."
---

# Multi-Agent Optimization Toolkit

Optimize multi-agent coordination, throughput, latency, and cost through profiling, context/window optimization, coordination efficiency, and staged rollout with rollback.

## Use this skill when

- Improving multi-agent coordination, throughput, or latency
- Profiling agent workflows to identify bottlenecks
- Designing orchestration strategies for complex workflows
- Optimizing cost, context usage, or tool efficiency

## Do not use this skill when

- Tuning only a single agent prompt
- No measurable metrics or evaluation data exist
- The task is unrelated to multi-agent orchestration

## Instructions (high level)

1. **Establish baseline** — Define metrics and target performance goals.
2. **Profile workloads** — Identify coordination bottlenecks (DB, app, frontend agents).
3. **Apply changes** — Orchestration and cost controls incrementally.
4. **Validate** — Repeatable tests and rollbacks; avoid system-wide regressions.

## Safety

- Do not deploy orchestration changes without regression testing.
- Roll out gradually to prevent system-wide regressions.

## Core capabilities

- Multi-agent performance profiling (DB, application, frontend layers)
- Context window optimization (compression, relevance filtering, token budget)
- Coordination efficiency (parallel execution, minimal inter-agent overhead, workload distribution)
- Parallel execution (async, partitioning, dynamic allocation, minimal blocking)
- Cost optimization (token tracking, model selection, caching, prompt efficiency)
- Latency reduction (predictive caching, context pre-warming, memoization)
- Quality vs speed tradeoffs with defined thresholds
- Monitoring and continuous improvement (dashboards, feedback loops)

## Arguments

- `$TARGET`: System/application to optimize
- `$PERFORMANCE_GOALS`: Metrics and objectives
- `$OPTIMIZATION_SCOPE`: quick-win vs comprehensive
- `$BUDGET_CONSTRAINTS`: Cost and resource limits
- `$QUALITY_METRICS`: Performance quality thresholds

## Key principles

- **Profiling**: Distributed monitoring; real-time metrics; performance signature tracking per agent (DB queries, app CPU/memory, frontend rendering/network).
- **Context**: Semantic compression, relevance filtering, dynamic resizing, token budget management.
- **Orchestration**: Parallel execution, minimal communication overhead, dynamic workload distribution, fault-tolerant interactions.
- **Cost**: Token usage tracking, adaptive model selection, caching and result reuse.
- **Quality vs speed**: Define performance thresholds and acceptable degradation; choose compromises explicitly.

## Considerations

- Always measure before and after optimization.
- Maintain stability during changes.
- Balance performance gains with resource consumption.
- Implement gradual, reversible changes.

For profiling/orchestration code patterns, **orchestration patterns** (parallel/pipeline/swarm), **orchestrator rules**, **performance framework** (Kiro), context compression, cost-tracking, and reference workflows, see [reference.md](reference.md).
