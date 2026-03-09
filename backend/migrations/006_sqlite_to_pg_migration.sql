-- Migration 006: Move all remaining SQLite tables to PostgreSQL
-- Tables: schedules, workflow_executions, benchmark_results, evaluations,
--         recommendations, optimization_history, domain_skill_registry, error_events, error_patterns

-- ── Workflow Scheduler ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schedules (
    id          TEXT PRIMARY KEY,
    template    TEXT NOT NULL,
    cron_expr   TEXT NOT NULL,
    variables   TEXT NOT NULL DEFAULT '{}',
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    next_run    TIMESTAMPTZ,
    last_run    TIMESTAMPTZ,
    last_status TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Workflow Optimizer ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workflow_executions (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    workflow_id      TEXT NOT NULL,
    workflow_name    TEXT,
    template_name    TEXT,
    status           TEXT,
    duration_ms      DOUBLE PRECISION,
    step_count       INTEGER,
    error_count      INTEGER,
    variables_json   TEXT,
    step_results_json TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_wfe_workflow ON workflow_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_wfe_created  ON workflow_executions(created_at DESC);

-- ── Benchmark Suite ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS benchmark_results (
    id            TEXT PRIMARY KEY,
    agent_role    TEXT NOT NULL,
    scenario_id   TEXT NOT NULL,
    scenario_name TEXT NOT NULL,
    category      TEXT NOT NULL,
    score         DOUBLE PRECISION NOT NULL,
    max_score     DOUBLE PRECISION NOT NULL,
    latency_ms    DOUBLE PRECISION NOT NULL,
    tokens_used   INTEGER NOT NULL DEFAULT 0,
    output_preview TEXT,
    dimensions    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_br_agent    ON benchmark_results(agent_role);
CREATE INDEX IF NOT EXISTS idx_br_scenario ON benchmark_results(scenario_id);
CREATE INDEX IF NOT EXISTS idx_br_created  ON benchmark_results(created_at DESC);

-- ── Agent Evaluations ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evaluations (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_role   TEXT NOT NULL,
    task_type    TEXT NOT NULL DEFAULT 'general',
    score        DOUBLE PRECISION NOT NULL,
    dimensions   TEXT,
    task_preview TEXT,
    tokens_used  INTEGER DEFAULT 0,
    latency_ms   DOUBLE PRECISION DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_eval_agent   ON evaluations(agent_role);
CREATE INDEX IF NOT EXISTS idx_eval_type    ON evaluations(task_type);
CREATE INDEX IF NOT EXISTS idx_eval_created ON evaluations(created_at DESC);

-- ── Auto Optimizer ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendations (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category          TEXT NOT NULL,
    priority          TEXT NOT NULL DEFAULT 'medium',
    title             TEXT NOT NULL,
    description       TEXT NOT NULL,
    affected_agents   TEXT NOT NULL DEFAULT '[]',
    suggested_actions TEXT NOT NULL DEFAULT '[]',
    estimated_impact  TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_rec_category ON recommendations(category);
CREATE INDEX IF NOT EXISTS idx_rec_priority ON recommendations(priority);
CREATE INDEX IF NOT EXISTS idx_rec_status   ON recommendations(status);
CREATE INDEX IF NOT EXISTS idx_rec_created  ON recommendations(created_at);

CREATE TABLE IF NOT EXISTS optimization_history (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recommendation_id BIGINT NOT NULL REFERENCES recommendations(id),
    action            TEXT NOT NULL,
    notes             TEXT,
    performed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_oh_rec ON optimization_history(recommendation_id);

-- ── Domain Skill Registry (Marketplace) ─────────────────────────
CREATE TABLE IF NOT EXISTS domain_skill_registry (
    domain_id    TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    name_tr      TEXT NOT NULL,
    description  TEXT,
    source       TEXT DEFAULT 'discovered',
    enabled      BOOLEAN DEFAULT TRUE,
    installed_at TIMESTAMPTZ,
    usage_count  INTEGER DEFAULT 0,
    rating       DOUBLE PRECISION DEFAULT 0.0,
    version      TEXT DEFAULT '1.0.0',
    author       TEXT DEFAULT 'community'
);

-- ── Error Events & Patterns ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS error_events (
    id            TEXT PRIMARY KEY,
    agent_role    TEXT NOT NULL,
    error_type    TEXT NOT NULL DEFAULT 'unknown',
    error_message TEXT NOT NULL,
    task_type     TEXT NOT NULL DEFAULT 'general',
    severity      TEXT NOT NULL DEFAULT 'medium',
    context_json  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ee_agent    ON error_events(agent_role);
CREATE INDEX IF NOT EXISTS idx_ee_type     ON error_events(error_type);
CREATE INDEX IF NOT EXISTS idx_ee_created  ON error_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ee_severity ON error_events(severity);

CREATE TABLE IF NOT EXISTS error_patterns (
    id               TEXT PRIMARY KEY,
    pattern_name     TEXT NOT NULL,
    description      TEXT,
    error_type       TEXT NOT NULL,
    agent_roles_json TEXT NOT NULL DEFAULT '[]',
    frequency        INTEGER NOT NULL DEFAULT 0,
    first_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status           TEXT NOT NULL DEFAULT 'active',
    resolution_json  TEXT
);
CREATE INDEX IF NOT EXISTS idx_ep_status ON error_patterns(status);
CREATE INDEX IF NOT EXISTS idx_ep_type   ON error_patterns(error_type);
