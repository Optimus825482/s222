-- Migration 003: Skill Marketplace + Self-Improvement Loop tables
-- Date: 2026-03-09

-- Skill ratings (marketplace)
CREATE TABLE IF NOT EXISTS skill_ratings (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(64) NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    review_text TEXT DEFAULT '',
    reviewer VARCHAR(64) NOT NULL,
    reviewer_type VARCHAR(16) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_skill_ratings_skill ON skill_ratings(skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_ratings_created ON skill_ratings(created_at);

-- Skill templates
CREATE TABLE IF NOT EXISTS skill_templates (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT DEFAULT '',
    category VARCHAR(64) NOT NULL,
    knowledge_template TEXT NOT NULL,
    frontmatter_template JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
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
CREATE INDEX IF NOT EXISTS idx_perf_agent ON performance_metrics(agent_role);
CREATE INDEX IF NOT EXISTS idx_perf_task ON performance_metrics(task_type);
CREATE INDEX IF NOT EXISTS idx_perf_created ON performance_metrics(created_at);

-- Skill-task-agent performance associations
CREATE TABLE IF NOT EXISTS skill_performance (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(64) NOT NULL,
    agent_role VARCHAR(32) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    avg_score REAL DEFAULT 0,
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(skill_id, agent_role, task_type)
);

-- Prompt strategies with version tracking
CREATE TABLE IF NOT EXISTS prompt_strategies (
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
CREATE INDEX IF NOT EXISTS idx_ps_role_task ON prompt_strategies(agent_role, task_type);

-- A/B experiments
CREATE TABLE IF NOT EXISTS ab_experiments (
    id SERIAL PRIMARY KEY,
    experiment_id VARCHAR(64) UNIQUE NOT NULL,
    agent_role VARCHAR(32) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    control_strategy_id INTEGER REFERENCES prompt_strategies(id),
    variant_strategy_id INTEGER REFERENCES prompt_strategies(id),
    traffic_split REAL DEFAULT 0.5 CHECK (traffic_split BETWEEN 0 AND 1),
    status VARCHAR(16) DEFAULT 'active',
    winner VARCHAR(16) DEFAULT NULL,
    p_value REAL DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    concluded_at TIMESTAMPTZ DEFAULT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ab_active ON ab_experiments(agent_role, task_type) WHERE status = 'active';

-- A/B experiment results per sample
CREATE TABLE IF NOT EXISTS ab_experiment_results (
    id SERIAL PRIMARY KEY,
    experiment_id VARCHAR(64) NOT NULL,
    variant VARCHAR(16) NOT NULL,
    score REAL NOT NULL,
    latency_ms REAL DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_abr_exp ON ab_experiment_results(experiment_id);

-- Optimization history log
CREATE TABLE IF NOT EXISTS optimization_history (
    id SERIAL PRIMARY KEY,
    optimization_type VARCHAR(32) NOT NULL,
    agent_role VARCHAR(32) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    before_value TEXT DEFAULT '',
    after_value TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_opt_created ON optimization_history(created_at);

-- Seed default skill templates
INSERT INTO skill_templates (id, name, description, category, knowledge_template) VALUES
('tpl-research', 'Research Template', 'Template for research-oriented skills', 'research', 'You are a research specialist. Gather information from multiple sources, verify facts, and provide comprehensive analysis with citations.'),
('tpl-coding', 'Coding Template', 'Template for coding-oriented skills', 'coding', 'You are a coding specialist. Write clean, efficient, well-documented code. Follow best practices and include error handling.'),
('tpl-analysis', 'Analysis Template', 'Template for analysis-oriented skills', 'analysis', 'You are an analysis specialist. Break down complex problems, identify patterns, and provide data-driven insights.'),
('tpl-reasoning', 'Reasoning Template', 'Template for reasoning-oriented skills', 'reasoning', 'You are a reasoning specialist. Apply logical thinking, consider multiple perspectives, and provide well-structured arguments.'),
('tpl-writing', 'Writing Template', 'Template for writing-oriented skills', 'writing', 'You are a writing specialist. Create clear, engaging, well-structured content tailored to the target audience.'),
('tpl-security', 'Security Template', 'Template for security-oriented skills', 'security', 'You are a security specialist. Identify vulnerabilities, recommend mitigations, and follow OWASP best practices.'),
('tpl-architecture', 'Architecture Template', 'Template for architecture-oriented skills', 'architecture', 'You are an architecture specialist. Design scalable, maintainable systems with clear component boundaries and data flow.'),
('tpl-performance', 'Performance Template', 'Template for performance-oriented skills', 'performance', 'You are a performance specialist. Profile bottlenecks, optimize queries, reduce latency, and improve throughput.'),
('tpl-domain', 'Domain-Specific Template', 'Template for domain-specific skills', 'domain-specific', 'You are a domain specialist. Apply deep domain knowledge to solve specialized problems with expert-level precision.')
ON CONFLICT (id) DO NOTHING;