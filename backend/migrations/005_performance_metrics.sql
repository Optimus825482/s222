-- Migration 005: Performance Metrics (agent_metrics_log) + Skills schema extension

-- 1. agent_metrics_log table
CREATE TABLE IF NOT EXISTS agent_metrics_log (
    id SERIAL PRIMARY KEY,
    agent_role VARCHAR(50) NOT NULL,
    model_name VARCHAR(100),
    skill_id VARCHAR(100),
    response_time_ms FLOAT NOT NULL,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- 2. Indexes
CREATE INDEX IF NOT EXISTS idx_aml_agent_role ON agent_metrics_log(agent_role);
CREATE INDEX IF NOT EXISTS idx_aml_recorded_at ON agent_metrics_log(recorded_at);
CREATE INDEX IF NOT EXISTS idx_aml_agent_role_recorded_at ON agent_metrics_log(agent_role, recorded_at);

-- 3. Skills table schema extension
ALTER TABLE skills ADD COLUMN IF NOT EXISTS input_schema JSONB DEFAULT '{}';
ALTER TABLE skills ADD COLUMN IF NOT EXISTS output_schema JSONB DEFAULT '{}';
