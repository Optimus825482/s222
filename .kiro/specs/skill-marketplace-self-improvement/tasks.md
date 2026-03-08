# Implementation Tasks

## Task 1: Database Schema — New PostgreSQL Tables [done]

Requirements: 1, 2, 3, 5, 6, 7, 8, 9, 10

Create SQL migration with all 8 new tables: `skill_ratings`, `skill_templates`, `performance_metrics`, `skill_performance`, `prompt_strategies`, `ab_experiments`, `ab_experiment_results`, `optimization_history`. Include indexes and constraints as defined in design.md.

Files to create:

- `backend/migrations/003_marketplace_self_improvement.sql`

Files to modify:

- `core/models.py` — add 4 new EventType enums: `METRIC_RECORDED`, `EXPERIMENT_CONCLUDED`, `OPTIMIZATION_APPLIED`, `ROUTING_WEIGHT_LOW`

- [x] Create migration SQL file with all 8 tables, indexes, and constraints
- [x] Add new EventType enums to `core/models.py`
- [x] Run migration against PostgreSQL to verify syntax
- [x] Verify all foreign keys and unique constraints work correctly

## Task 2: Performance Collector Module [done]

Requirements: 5

Build `tools/performance_collector.py` — PerformanceCollector class that records agent metrics to PostgreSQL and publishes `METRIC_RECORDED` events to the event bus. Includes 24-hour rolling in-memory cache.

Files to create:

- `tools/performance_collector.py`

Files to modify:

- `pipelines/engine.py` — integrate `PerformanceCollector.record()` call in `_run_subtask()` after existing `score_agent_output()`

- [x] Implement PerformanceCollector class with `record()`, `get_agent_stats()`, `get_skill_stats()` methods
- [x] Add rolling 24h deque cache (maxlen=5000)
- [x] Publish METRIC_RECORDED event to bus channel "metrics" on each record
- [x] Integrate into `pipelines/engine.py` `_run_subtask()` — call after `score_agent_output()`
- [x] Verify event bus receives METRIC_RECORDED events correctly

## Task 3: Prompt Strategy Manager [done]

Requirements: 10

Build `tools/prompt_strategies.py` — PromptStrategyManager class with CRUD, auto-versioning, and activate/rollback. Strategies stored in PostgreSQL `prompt_strategies` table.

Files to create:

- `tools/prompt_strategies.py`

- [x] Implement PromptStrategyManager with `create()`, `list_strategies()`, `activate()`, `get_active()` methods
- [x] Auto-increment version per agent_role+task_type combination
- [x] Activate endpoint checks for conflicting active A/B experiment (returns 409)
- [x] Retain previous versions for rollback capability
- [x] Verify version tracking works correctly across multiple creates

## Task 4: A/B Test Manager [done]

Requirements: 6

Build `tools/ab_testing.py` — ABTestManager class for experiment lifecycle: create, deterministic variant assignment, result recording, Welch's t-test significance check, and auto-conclude.

Files to create:

- `tools/ab_testing.py`

- [x] Implement ABTestManager with `create_experiment()`, `assign_variant()`, `record_result()`, `check_significance()`, `conclude_experiment()` methods
- [x] Deterministic variant assignment via `hashlib.md5(experiment_id:task_id)`
- [x] Welch's t-test via `scipy.stats.ttest_ind(equal_var=False)` with p < 0.05 threshold
- [x] Auto-check significance when both variants reach 30+ samples
- [x] Publish EXPERIMENT_CONCLUDED event on bus when significant winner found
- [x] Prevent duplicate active experiments for same agent_role+task_type

## Task 5: Optimization Engine — Skill Ranking [done]

Requirements: 7

Build `tools/optimization_engine.py` — OptimizationEngine class that ranks skills by Skill_Score for task_type+agent_role, applies exploration bonus for underused skills, and updates skill_performance records.

Files to create:

- `tools/optimization_engine.py`

Files to modify:

- `pipelines/engine.py` — integrate skill ranking before skill injection in `_run_subtask()`

- [x] Implement `rank_skills()` with Skill_Score formula: (0.4×avg_rating) + (0.3×norm_use_count) + (0.3×success_rate)
- [x] Apply +0.5 exploration bonus when use_count < 5 for task_type
- [x] Implement `update_skill_performance()` for upsert after task completion
- [x] Implement `get_active_strategy()` for prompt strategy lookup
- [x] Integrate into `pipelines/engine.py` — replace/augment existing skill injection with performance-ranked skills

## Task 6: Dynamic Router [done]

Requirements: 8

Build `tools/dynamic_router.py` — DynamicRouter class with softmax-based routing weights, exploration-exploitation balance, and periodic recalculation.

Files to create:

- `tools/dynamic_router.py`

- [x] Implement Agent_Performance_Score: 0.4×success_rate + 0.25×norm_score + 0.2×latency_eff + 0.15×token_eff
- [x] Implement softmax normalization for Routing_Weights
- [x] Implement exploration_rate (default 0.1) — random agent selection for exploration fraction
- [x] Recalculate every 50 tasks or 1 hour (whichever first)
- [x] Publish ROUTING_WEIGHT_LOW event when any weight < 0.05
- [x] Implement `get_weights()` for API exposure

## Task 7: Feedback Loop [done]

Requirements: 9

Build `tools/feedback_loop.py` — FeedbackLoop class that subscribes to event bus, monitors agent performance, triggers skill re-ranking and prompt strategy updates, and logs all optimizations.

Files to create:

- `tools/feedback_loop.py`

- [x] Subscribe to "metrics" channel for METRIC_RECORDED events
- [x] Subscribe to "experiments" channel for EXPERIMENT_CONCLUDED events
- [x] Track rolling 20-task window per agent+task_type — trigger skill re-rank when success_rate < 60%
- [x] On EXPERIMENT_CONCLUDED: update agent_param_overrides with winning prompt strategy
- [x] Log all optimizations to `optimization_history` table
- [x] Publish OPTIMIZATION_APPLIED event with before/after values
- [x] Process events within 5 seconds of receipt

## Task 8: Marketplace API Routes — Skill Discovery, Rating, Templates, Sharing [done]

Requirements: 1, 2, 3, 4

Build `backend/routes/marketplace.py` — FastAPI router with 10 endpoints for skill marketplace: list, search, detail, ratings CRUD, templates, export/import/fork.

Files to create:

- `backend/routes/marketplace.py`

Files to modify:

- `backend/main.py` — register marketplace router

- [x] GET /api/skills — paginated list with category/source filters
- [x] GET /api/skills/search?q= — relevance-ranked search
- [x] GET /api/skills/{skill_id} — full detail with knowledge + stats
- [x] POST /api/skills/{skill_id}/ratings — submit rating (validate 1-5)
- [x] GET /api/skills/{skill_id}/ratings — paginated ratings list
- [x] GET /api/skill-templates — list available templates
- [x] POST /api/skills/from-template — create skill from template
- [x] POST /api/skills/{skill_id}/export — export as JSON package
- [x] POST /api/skills/import — import JSON package (dedup on existing id)
- [x] POST /api/skills/{skill_id}/fork — fork existing skill
- [x] Register router in backend/main.py

## Task 9: Self-Improvement API Routes — Metrics, Experiments, Routing, Dashboard [done]

Requirements: 5, 6, 8, 10, 11

Build `backend/routes/self_improvement.py` — FastAPI router with 12 endpoints for metrics, experiments, prompt strategies, routing weights, and dashboard data.

Files to create:

- `backend/routes/self_improvement.py`

Files to modify:

- `backend/main.py` — register self_improvement router

- [x] GET /api/metrics/agents/{agent_role} — aggregated agent stats
- [x] GET /api/metrics/skills/{skill_id} — skill usage stats
- [x] POST /api/experiments — create A/B experiment
- [x] GET /api/experiments — list experiments with metrics + significance
- [x] POST /api/prompt-strategies — create prompt strategy
- [x] GET /api/prompt-strategies — list with filters
- [x] POST /api/prompt-strategies/{id}/activate — activate (409 if A/B conflict)
- [x] GET /api/routing/weights — current routing weights
- [x] GET /api/dashboard/overview — system overview stats
- [x] GET /api/dashboard/agents/{role}/history — time-series with granularity
- [x] GET /api/dashboard/optimization-log — paginated optimization history
- [x] GET /api/dashboard/skill-leaderboard — skills ranked by Skill_Score
- [x] Register router in backend/main.py

## Task 10: Pipeline Integration — Wire Everything Together [done]

Requirements: 5, 7, 8, 9

Connect all modules into the pipeline execution flow: Performance Collector records after subtasks, Optimization Engine ranks skills before injection, Dynamic Router influences agent selection, Feedback Loop starts on app boot.

Files to modify:

- `pipelines/engine.py` — add PerformanceCollector + OptimizationEngine integration
- `agents/base.py` — add prompt strategy injection in `build_context()`
- `backend/main.py` — initialize FeedbackLoop on startup

- [x] In `PipelineEngine.__init__()`: initialize PerformanceCollector, OptimizationEngine, DynamicRouter singletons
- [x] In `_run_subtask()`: after score_agent_output, call PerformanceCollector.record()
- [x] In `_run_subtask()`: before skill injection, call OptimizationEngine.rank_skills() for performance-ranked skill selection
- [x] In `agents/base.py` `build_context()`: check for active prompt strategy and inject if available
- [x] In `backend/main.py` startup event: initialize and start FeedbackLoop
- [x] Verify closed feedback loop: task → metric → event → optimization → next task
- [x] Seed skill_templates table with 9 category templates (research, coding, analysis, reasoning, writing, security, architecture, performance, domain-specific)
