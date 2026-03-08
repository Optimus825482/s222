-- Migration 004: SharedWorkspace tables (Qdrant → PostgreSQL)

CREATE TABLE IF NOT EXISTS shared_workspaces (
    workspace_id TEXT PRIMARY KEY,
    owner_id     TEXT NOT NULL,
    name         TEXT NOT NULL,
    members      TEXT[] NOT NULL DEFAULT '{}',
    metadata     JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS shared_workspace_items (
    item_id      TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES shared_workspaces(workspace_id) ON DELETE CASCADE,
    item_type    TEXT NOT NULL,
    content      TEXT NOT NULL,
    author_id    TEXT NOT NULL,
    metadata     JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sw_items_workspace ON shared_workspace_items(workspace_id);
CREATE INDEX IF NOT EXISTS idx_sw_items_type ON shared_workspace_items(workspace_id, item_type);
CREATE INDEX IF NOT EXISTS idx_sw_members ON shared_workspaces USING GIN(members);
