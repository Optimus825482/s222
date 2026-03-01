const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

async function fetcher<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

// ── Models & Config ─────────────────────────────────────────────

import type { ModelConfig, ThreadSummary, Thread } from "./types";

export const api = {
  getModels: () => fetcher<Record<string, ModelConfig>>("/api/models"),
  getPipelines: () =>
    fetcher<{ id: string; label: string }[]>("/api/pipelines"),
  health: () => fetcher<{ status: string }>("/api/health"),

  // Threads
  listThreads: (limit = 20) =>
    fetcher<ThreadSummary[]>(`/api/threads?limit=${limit}`),
  createThread: () =>
    fetcher<{ id: string }>("/api/threads", { method: "POST" }),
  getThread: (id: string) => fetcher<Thread>(`/api/threads/${id}`),
  deleteThread: (id: string) =>
    fetcher<{ deleted: boolean }>(`/api/threads/${id}`, { method: "DELETE" }),
  deleteAllThreads: () =>
    fetcher<{ deleted: number }>("/api/threads", { method: "DELETE" }),

  // RAG
  ragIngest: (content: string, title: string, source = "") =>
    fetcher("/api/rag/ingest", {
      method: "POST",
      body: JSON.stringify({ content, title, source }),
    }),
  ragQuery: (query: string, max_results = 5) =>
    fetcher("/api/rag/query", {
      method: "POST",
      body: JSON.stringify({ query, max_results }),
    }),
  ragDocuments: () => fetcher("/api/rag/documents"),

  // Skills
  listSkills: () => fetcher("/api/skills"),
  createSkill: (data: {
    skill_id: string;
    name: string;
    description: string;
    knowledge: string;
    category?: string;
    keywords?: string[];
  }) => fetcher("/api/skills", { method: "POST", body: JSON.stringify(data) }),
  getSkill: (id: string) => fetcher(`/api/skills/${id}`),
  deleteSkill: (id: string) =>
    fetcher(`/api/skills/${id}`, { method: "DELETE" }),

  // MCP
  mcpServers: () => fetcher("/api/mcp/servers"),
  addMcpServer: (server_id: string, url: string, name = "") =>
    fetcher("/api/mcp/servers", {
      method: "POST",
      body: JSON.stringify({ server_id, url, name }),
    }),
  mcpTools: (serverId: string) => fetcher(`/api/mcp/servers/${serverId}/tools`),

  // Teachability
  getTeachings: () => fetcher("/api/teachability"),
  addTeaching: (content: string) =>
    fetcher("/api/teachability", {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  // Eval
  evalStats: () => fetcher("/api/eval/stats"),

  // Projects (Idea-to-Project exports)
  listProjects: () =>
    fetcher<
      {
        name: string;
        phases: string[];
        phase_count: number;
        total_phases: number;
      }[]
    >("/api/projects"),
  exportProject: (name: string) =>
    fetcher<{ markdown: string; project_name: string }>(
      `/api/projects/${encodeURIComponent(name)}/export`,
    ),

  // Presentations
  listPresentations: () =>
    fetcher<{ name: string; filename: string; size_kb: number }[]>(
      "/api/presentations",
    ),
};

// ── Memory API ───────────────────────────────────────────────────

export async function getMemoryStats() {
  const res = await fetch(`${BASE}/api/memory/stats`);
  if (!res.ok) return null;
  return res.json();
}

export async function getMemoryLayers() {
  const res = await fetch(`${BASE}/api/memory/layers`);
  if (!res.ok) return { working: [], episodic: [], semantic: [] };
  return res.json();
}

export async function deleteMemory(memoryId: number) {
  const res = await fetch(`${BASE}/api/memory/${memoryId}`, {
    method: "DELETE",
  });
  return res.ok;
}

export async function getAutoSkills() {
  const res = await fetch(`${BASE}/api/skills/auto`);
  if (!res.ok) return [];
  return res.json();
}

export async function getDbHealth() {
  const res = await fetch(`${BASE}/api/db/health`);
  if (!res.ok) return { status: "error" };
  return res.json();
}
