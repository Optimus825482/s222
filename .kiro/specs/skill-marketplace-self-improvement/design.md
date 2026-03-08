# Technical Design Document

## Introduction

Bu doküman, Skill Marketplace ve Self-Improvement Loop özelliklerinin teknik tasarımını tanımlar. Mevcut `tools/dynamic_skills.py` (skill CRUD), `tools/agent_eval.py` (scoring), `core/event_bus.py` (pub-sub), ve `pipelines/engine.py` (pipeline execution) üzerine inşa edilir.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                          │
│  ┌──────────────────┐  ┌──────────────────────────────────┐    │
│  │ marketplace.py   │  │ self_improvement.py               │    │
│  │ (Req 1-4)        │  │ (Req 5-11)                        │    │
│  │ Skills CRUD      │  │ Metrics, Experiments, Routing,    │    │
│  │ Ratings, Export   │  │ Strategies, Dashboard             │    │
│  └────────┬─────────┘  └──────────┬───────────────────────┘    │
│           │                       │                             │
│  ┌────────▼───────────────────────▼───────────────────────┐    │
│  │                   PostgreSQL Tables                     │    │
│  │  skill_ratings │ skill_templates │ performance_metrics  │    │
│  │  skill_performance │ prompt_strategies │ ab_experiments │    │
│  │  optimization_history                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ Performance │  │  Optimization    │  │   Feedback Loop      │
│ Collector   │  │  Engine          │  │   (Event Bus Sub)    │
│             │──│  - Skill Rank    │──│   - Metric listener  │
│ Record after│  │  - Prompt Select │  │   - Auto re-rank     │
│ each subtask│  │  - Dynamic Route │  │   - Strategy update  │
└──────┬──────┘  └────────┬─────────┘  └──────────┬───────────┘
       │                  │                        │
       ▼                  ▼                        ▼
┌──────────────────────────────────────────────────────────────┐
│                     Event Bus (core/event_bus.py)             │
│  Channels: "metrics", "experiments", "optimization"          │
│  Events: METRIC_RECORDED, EXPERIMENT_CONCLUDED,              │
│          OPTIMIZATION_APPLIED, ROUTING_WEIGHT_LOW            │
└──────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ A/B Test    │  │  Dynamic Router  │  │  Prompt Strategy     │
│ Manager     │  │  (softmax route) │  │  Manager             │
│ - Variant   │  │  - Exploration   │  │  - Version tracking  │
│   assign    │  │  - Weight calc   │  │  - Activate/rollback │
│ - t-test    │  │  - Recalculate   │  │  - A/B integration   │
└─────────────┘  └──────────────────┘  └──────────────────────┘
```

## Closed Feedback Loop Data Flow

```
Task Execution (pipelines/engine.py _run_subtask)
       │
       ▼
Performance Collector ──record()──▶ PostgreSQL (performance_metrics)
       │
       ▼
Event Bus ──publish("metrics", METRIC_RECORDED)──▶ Feedback Loop
       │                                                │
       │                              ┌─────────────────┤
       │                              ▼                 ▼
       │                    Skill Re-ranking    Routing Weight Update
       │                              │                 │
       │                              ▼                 ▼
       │                    Optimization Engine ──▶ optimization_history
       │                              │
       ▼                              ▼
A/B Test Manager ◀── variant assign ── Next Task Execution
       │
       ▼ (when significant)
EXPERIMENT_CONCLUDED ──▶ Feedback Loop ──▶ Prompt Strategy Update
```

## Database Schema

### New PostgreSQL Tables

```sql
-- Skill ratings (Req 2)
CREATE TABLE skill_ratings (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(64) NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    review_text TEXT DEFAULT '',
    reviewer VARCHAR(64) NOT NULL,        -- user_id or "agent:{role}"
    reviewer_type VARCHAR(16) DEFAULT 'user',  -- 'user' or 'agent'
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_skill_ratings_skill ON skill_ratings(skill_id);

-- Skill templates (Req 3)
CREATE TABLE skill_templates (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT DEFAULT '',
    category VARCHAR(64) NOT NULL,
    knowledge_template TEXT NOT NULL,
    frontmatter_template JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance metrics (Req 5)
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    agent_role VARCHAR(32) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    score REAL NOT NULL,
    latency_ms REAL DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    skill_ids_used TEXT[] DEFAULT '{}',
    prompt_strategy_id INTEGER DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_perf_agent ON performance_metrics(agent_role);
CREATE INDEX idx_perf_task ON performance_metrics(task_type);
CREATE INDEX idx_perf_created ON performance_metrics(created_at);

-- Skill-task-agent performance (Req 7)
CREATE TABLE skill_performance (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(64) NOT NULL,
    agent_role VARCHAR(32) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    avg_score REAL DEFAULT 0,
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(skill_id, agent_role, task_type)
);

-- Prompt strategies (Req 10)
CREATE TABLE prompt_strategies (
    id SERIAL PRIMARY KEY,
    agent_role VARCHAR(32) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    version INTEGER DEFAULT 1,
    system_prompt TEXT NOT NULL,
    few_shot_examples JSONB DEFAULT '[]',
    cot_instructions TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_ps_role_task ON prompt_strategies(agent_role, task_type);

-- A/B experiments (Req 6)
CREATE TABLE ab_experiments (
    id SERIAL PRIMARY KEY,
    experiment_id VARCHAR(64) UNIQUE NOT NULL,
    agent_role VARCHAR(32) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    control_strategy_id INTEGER REFERENCES prompt_strategies(id),
    variant_strategy_id INTEGER REFERENCES prompt_strategies(id),
    traffic_split REAL DEFAULT 0.5 CHECK (traffic_split BETWEEN 0 AND 1),
    status VARCHAR(16) DEFAULT 'active',  -- active, concluded, cancelled
    winner VARCHAR(16) DEFAULT NULL,      -- 'control', 'variant', NULL
    p_value REAL DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    concluded_at TIMESTAMPTZ DEFAULT NULL
);
CREATE UNIQUE INDEX idx_ab_active ON ab_experiments(agent_role, task_type) WHERE status = 'active';

-- A/B experiment results per sample (Req 6)
CREATE TABLE ab_experiment_results (
    id SERIAL PRIMARY KEY,
    experiment_id VARCHAR(64) NOT NULL,
    variant VARCHAR(16) NOT NULL,         -- 'control' or 'variant'
    score REAL NOT NULL,
    latency_ms REAL DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_abr_exp ON ab_experiment_results(experiment_id);

-- Optimization history (Req 9)
CREATE TABLE optimization_history (
    id SERIAL PRIMARY KEY,
    optimization_type VARCHAR(32) NOT NULL,  -- 'skill_rerank', 'routing_weight', 'prompt_strategy'
    agent_role VARCHAR(32) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    before_value TEXT DEFAULT '',
    after_value TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_opt_created ON optimization_history(created_at);
```

## New Python Modules

### 1. `tools/performance_collector.py` (Req 5)

```python
class PerformanceCollector:
    """Collects agent performance metrics after each subtask execution."""

    def __init__(self, db_pool, event_bus):
        self._pool = db_pool
        self._bus = event_bus
        self._cache: deque[dict] = deque(maxlen=5000)  # 24h rolling cache

    async def record(
        self, agent_role: str, task_type: str, score: float,
        latency_ms: float, tokens_used: int,
        skill_ids_used: list[str], prompt_strategy_id: int | None,
    ) -> None:
        """Insert into performance_metrics + publish METRIC_RECORDED event."""

    async def get_agent_stats(self, agent_role: str) -> dict:
        """Aggregated stats: avg_score, success_rate, avg_latency, per-task breakdown."""

    async def get_skill_stats(self, skill_id: str) -> dict:
        """Skill usage stats: total_uses, avg_score_when_used, per-agent breakdown."""
```

Integration point: `pipelines/engine.py` `_run_subtask()` — after `score_agent_output()` call.

### 2. `tools/ab_testing.py` (Req 6)

```python
class ABTestManager:
    """Manages A/B experiments for prompt strategies."""

    def __init__(self, db_pool, event_bus):
        self._pool = db_pool
        self._bus = event_bus

    async def create_experiment(
        self, experiment_id: str, agent_role: str, task_type: str,
        control_strategy_id: int, variant_strategy_id: int,
        traffic_split: float = 0.5,
    ) -> dict:
        """Create new experiment. Fails if active experiment exists for role+task."""

    def assign_variant(self, experiment_id: str, task_id: str) -> str:
        """Deterministic variant assignment via hash(experiment_id + task_id) % 100."""

    async def record_result(
        self, experiment_id: str, variant: str,
        score: float, latency_ms: float, tokens_used: int,
    ) -> None:
        """Record sample result + check significance if min samples reached."""

    async def check_significance(self, experiment_id: str) -> dict | None:
        """Two-sample t-test. Returns {winner, p_value} if p < 0.05 and n >= 30."""

    async def conclude_experiment(self, experiment_id: str, winner: str, p_value: float) -> None:
        """Mark concluded + publish EXPERIMENT_CONCLUDED event."""
```

Significance calculation: `scipy.stats.ttest_ind()` with `equal_var=False` (Welch's t-test).

### 3. `tools/optimization_engine.py` (Req 7)

```python
class OptimizationEngine:
    """Ranks skills and selects optimal prompt strategies based on performance data."""

    def __init__(self, db_pool):
        self._pool = db_pool

    async def rank_skills(
        self, task_type: str, agent_role: str, top_n: int = 3,
    ) -> list[str]:
        """
        Rank skills by Skill_Score for given task_type + agent_role.
        Skill_Score = (0.4 × avg_rating) + (0.3 × norm_use_count) + (0.3 × success_rate)
        Exploration bonus: +0.5 if use_count < 5 for this task_type.
        Returns top-N skill_ids.
        """

    async def update_skill_performance(
        self, skill_ids: list[str], agent_role: str, task_type: str, score: float,
    ) -> None:
        """Upsert skill_performance records after task completion."""

    async def get_active_strategy(self, agent_role: str, task_type: str) -> dict | None:
        """Get currently active prompt strategy for role+task."""
```

### 4. `tools/dynamic_router.py` (Req 8)

```python
import math

class DynamicRouter:
    """Performance-based agent routing with exploration-exploitation balance."""

    def __init__(self, db_pool, event_bus):
        self._pool = db_pool
        self._bus = event_bus
        self._weights: dict[str, dict[str, float]] = {}  # task_type → {agent → weight}
        self._task_counter = 0
        self._last_recalc = time.time()
        self.exploration_rate = 0.1

    async def route(self, task_type: str) -> str:
        """
        Select best agent for task_type.
        1. Check if recalculation needed (every 50 tasks or 1 hour)
        2. With probability exploration_rate, pick random agent
        3. Otherwise pick highest Routing_Weight agent
        """

    async def recalculate_weights(self, task_type: str | None = None) -> None:
        """
        Agent_Performance_Score = 0.4×success_rate + 0.25×norm_avg_score
                                + 0.2×latency_efficiency + 0.15×token_efficiency
        Routing_Weight = softmax(Agent_Performance_Scores)
        Publish ROUTING_WEIGHT_LOW if any weight < 0.05.
        """

    def _softmax(self, scores: dict[str, float]) -> dict[str, float]:
        """Softmax normalization."""
        max_s = max(scores.values())
        exps = {k: math.exp(v - max_s) for k, v in scores.items()}
        total = sum(exps.values())
        return {k: v / total for k, v in exps.items()}

    async def get_weights(self) -> dict[str, dict[str, float]]:
        """Return current routing weights for all task types."""
```

Integration point: `agents/orchestrator.py` routing decision — replace/augment `get_best_agent_for_task()`.

### 5. `tools/feedback_loop.py` (Req 9)

```python
class FeedbackLoop:
    """Closed-loop optimization: listens to events, triggers improvements."""

    def __init__(self, db_pool, event_bus, optimization_engine, dynamic_router):
        self._pool = db_pool
        self._bus = event_bus
        self._engine = optimization_engine
        self._router = dynamic_router
        self._recent_metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))

    async def start(self) -> None:
        """Subscribe to 'metrics' and 'experiments' channels on event bus."""

    async def _on_metric_recorded(self, msg: MessageEnvelope) -> None:
        """
        Process METRIC_RECORDED event:
        1. Track rolling window per agent+task_type
        2. If success_rate < 60% over last 20 → trigger skill re-ranking
        3. Update skill_performance records
        4. Increment Dynamic Router task counter
        """

    async def _on_experiment_concluded(self, msg: MessageEnvelope) -> None:
        """
        Process EXPERIMENT_CONCLUDED event:
        1. Get winning strategy details
        2. Update agent_param_overrides with winning prompt
        3. Log to optimization_history
        4. Publish OPTIMIZATION_APPLIED event
        """

    async def _log_optimization(
        self, opt_type: str, agent_role: str, task_type: str,
        before: str, after: str, reason: str,
    ) -> None:
        """Insert into optimization_history table."""
```

### 6. `tools/prompt_strategies.py` (Req 10)

```python
class PromptStrategyManager:
    """CRUD + version tracking for prompt strategies."""

    def __init__(self, db_pool):
        self._pool = db_pool

    async def create(
        self, agent_role: str, task_type: str, name: str,
        system_prompt: str, few_shot_examples: list = None,
        cot_instructions: str = "", metadata: dict = None,
    ) -> dict:
        """Create new strategy with auto-incremented version."""

    async def list_strategies(
        self, agent_role: str = None, task_type: str = None,
    ) -> list[dict]:
        """List strategies with optional filters."""

    async def activate(self, strategy_id: int) -> dict:
        """Set as active. Fails with 409 if active A/B experiment exists."""

    async def get_active(self, agent_role: str, task_type: str) -> dict | None:
        """Get currently active strategy for role+task."""
```

### 7. `backend/routes/marketplace.py` (Req 1-4)

Endpoints under `/api/skills/`:

- `GET /api/skills` — paginated list with category/source filters
- `GET /api/skills/search?q=` — relevance-ranked search
- `GET /api/skills/{skill_id}` — full detail
- `POST /api/skills/{skill_id}/ratings` — submit rating
- `GET /api/skills/{skill_id}/ratings` — list ratings
- `GET /api/skill-templates` — list templates
- `POST /api/skills/from-template` — create from template
- `POST /api/skills/{skill_id}/export` — export as JSON package
- `POST /api/skills/import` — import JSON package
- `POST /api/skills/{skill_id}/fork` — fork skill

### 8. `backend/routes/self_improvement.py` (Req 5-11)

Endpoints under `/api/`:

- `GET /api/metrics/agents/{agent_role}` — agent performance stats
- `GET /api/metrics/skills/{skill_id}` — skill usage stats
- `POST /api/experiments` — create A/B experiment
- `GET /api/experiments` — list experiments
- `POST /api/prompt-strategies` — create strategy
- `GET /api/prompt-strategies` — list strategies
- `POST /api/prompt-strategies/{id}/activate` — activate strategy
- `GET /api/routing/weights` — current routing weights
- `GET /api/dashboard/overview` — dashboard overview
- `GET /api/dashboard/agents/{role}/history` — time-series data
- `GET /api/dashboard/optimization-log` — optimization history
- `GET /api/dashboard/skill-leaderboard` — skill rankings

## Modified Files

### `core/models.py`

Add new EventType enums:

```python
METRIC_RECORDED = "metric_recorded"
EXPERIMENT_CONCLUDED = "experiment_concluded"
OPTIMIZATION_APPLIED = "optimization_applied"
ROUTING_WEIGHT_LOW = "routing_weight_low"
```

### `pipelines/engine.py`

In `_run_subtask()` after existing `score_agent_output()`:

1. Call `PerformanceCollector.record()` with subtask metrics
2. Before skill injection, call `OptimizationEngine.rank_skills()` to get performance-ranked skills

### `backend/main.py`

Register new routers:

```python
from backend.routes.marketplace import router as marketplace_router
from backend.routes.self_improvement import router as self_improvement_router
app.include_router(marketplace_router)
app.include_router(self_improvement_router)
```

### `agents/base.py`

Add `_prompt_strategy` lazy property that checks for active prompt strategy via `PromptStrategyManager.get_active()` and injects into `build_context()`.

## Key Algorithms

### Skill_Score Calculation

```
Skill_Score = (0.4 × avg_rating/5.0) + (0.3 × min(use_count/100, 1.0)) + (0.3 × success_rate)
If use_count < 5 for task_type: Skill_Score += 0.5 (exploration bonus, capped at 5.0)
```

### Agent_Performance_Score

```
success_rate = success_count / total_count
norm_avg_score = avg_score / 5.0
latency_efficiency = 1.0 - min(avg_latency_ms / 30000, 1.0)
token_efficiency = 1.0 - min(avg_tokens / 10000, 1.0)

APS = 0.4×success_rate + 0.25×norm_avg_score + 0.2×latency_efficiency + 0.15×token_efficiency
```

### Routing Weight (Softmax)

```
weights[agent] = exp(APS[agent]) / Σ exp(APS[all_agents])
```

### A/B Significance Test

```python
from scipy.stats import ttest_ind
t_stat, p_value = ttest_ind(control_scores, variant_scores, equal_var=False)
significant = p_value < 0.05 and len(control_scores) >= 30 and len(variant_scores) >= 30
```

### Deterministic Variant Assignment

```python
hash_val = int(hashlib.md5(f"{experiment_id}:{task_id}".encode()).hexdigest(), 16)
variant = "control" if (hash_val % 100) < (traffic_split * 100) else "variant"
```
