# Multi-Agent Optimization — Reference

## Profiling agents

- **Database Performance Agent**: Query execution time, index utilization, resource consumption.
- **Application Performance Agent**: CPU/memory profiling, algorithmic complexity, concurrency/async.
- **Frontend Performance Agent**: Rendering metrics, network requests, Core Web Vitals.

## Profiling code pattern

```python
def multi_agent_profiler(target_system):
    agents = [
        DatabasePerformanceAgent(target_system),
        ApplicationPerformanceAgent(target_system),
        FrontendPerformanceAgent(target_system)
    ]
    performance_profile = {}
    for agent in agents:
        performance_profile[agent.__class__.__name__] = agent.profile()
    return aggregate_performance_metrics(performance_profile)
```

## Context compression

```python
def compress_context(context, max_tokens=4000):
    compressed_context = semantic_truncate(
        context,
        max_tokens=max_tokens,
        importance_threshold=0.7
    )
    return compressed_context
```

Techniques: semantic compression, relevance filtering, dynamic window resizing, token budget management.

## Orchestration framework

```python
class MultiAgentOrchestrator:
    def __init__(self, agents):
        self.agents = agents
        self.execution_queue = PriorityQueue()
        self.performance_tracker = PerformanceTracker()

    def optimize(self, target_system):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(agent.optimize, target_system): agent
                for agent in self.agents
            }
            for future in concurrent.futures.as_completed(futures):
                agent = futures[future]
                result = future.result()
                self.performance_tracker.log(agent, result)
```

## Cost tracking example

```python
class CostOptimizer:
    def __init__(self):
        self.token_budget = 100000  # Monthly budget
        self.token_usage = 0
        self.model_costs = {
            'gpt-5': 0.03,
            'claude-4-sonnet': 0.015,
            'claude-4-haiku': 0.0025
        }

    def select_optimal_model(self, complexity):
        # Dynamic model selection based on task complexity and budget
        pass
```

## Reference workflows

**E-Commerce platform:** Initial profiling → agent-based optimization → cost/performance tracking → continuous improvement.

**Enterprise API:** Comprehensive analysis → multi-layered agent optimization → iterative refinement → cost-efficient scaling.

**Target:** Use `$ARGUMENTS` (or `$TARGET`, `$PERFORMANCE_GOALS`, etc.) when invoking the tool.

---

## Orchestration patterns (Kiro)

### Parallel specialists (leader pattern)
- Create team/context; spawn N specialists in parallel (e.g. security, performance, simplicity).
- Each specialist gets a focused prompt and reports back to leader.
- Leader synthesizes findings. Shutdown each specialist then cleanup.

### Pipeline (sequential dependencies)
- Create tasks with dependencies: TaskCreate(1), TaskCreate(2), …; TaskUpdate(2, addBlockedBy: [1]), etc.
- Workers claim tasks when unblocked; complete and notify; next task auto-unblocks.
- Use for Research → Plan → Implement → Test → Review.

### Swarm (self-organizing)
- Create a pool of independent tasks (no dependencies).
- Spawn multiple workers with the same prompt: poll task list, claim a pending task, do work, complete, report, repeat until no tasks.
- Workers race to claim; natural load balance.

### Parallel resolution workflow
1. **Analyze** — Gather all items to resolve (e.g. TODOs, comments).
2. **Plan** — TodoWrite list grouped by type; respect dependencies (e.g. rename first); output mermaid flow.
3. **Implement (parallel)** — One agent per item, all invoked in parallel (e.g. invokeSubAgent per item).
4. **Commit & resolve** — Commit changes, push, mark resolved.

---

## Orchestrator rules (Kiro)

**Pre-flight:** Before invoking specialists, verify PLAN.md (or equivalent) exists; if missing, create plan first. Verify project type (WEB / MOBILE / BACKEND) and route agents accordingly.

**Project type routing:** MOBILE → mobile-developer only; WEB → frontend-specialist (+ backend if needed); BACKEND → backend-specialist.

**Agent boundaries:** Each agent stays in domain (frontend: components/UI; backend: API/DB; test-engineer: tests only; security-auditor: audit only; etc.). If a file belongs to another domain, delegate to the correct agent.

**Agent selection table (representative):** security-auditor (auth, OWASP), backend-specialist (API, DB), frontend-specialist (UI, components), test-engineer (tests, coverage), devops-engineer (CI/CD, deploy), database-architect (schema, migrations), performance-optimizer (bottlenecks, profiling), project-planner (plan, breakdown), debugger (root cause), explorer-agent (discovery).

**Conflict resolution:** Same file edited by multiple agents → merge suggestions, present options. Disagreement between agents → note both, explain trade-offs, recommend (e.g. security > performance > convenience).

---

## Performance framework (Kiro performance-oracle)

**Core areas:** Algorithmic complexity (Big O, flag O(n²)+); Database (N+1, indexes, eager loading); Memory (leaks, unbounded structures); Caching (memoization, layers, invalidation); Network (round trips, batching, payload); Frontend (bundle, render-blocking, lazy load).

**Benchmarks:** No algorithms worse than O(n log n) without justification; DB queries use indexes; memory bounded; API response &lt;200ms; bundle increase &lt;5KB per feature; batch background jobs.

**Output:** Performance summary → Critical issues → Recommendations → Metrics (latency, throughput, resource use).
