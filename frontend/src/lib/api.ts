const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

import { useAuth } from "@/lib/auth";

let _isClearingAuth = false;

function clearAuthOn401(): void {
  if (_isClearingAuth) return;
  _isClearingAuth = true;

  try {
    // Clear persisted auth/session markers first so future requests do not reuse stale tokens.
    localStorage.removeItem("ops-center-auth");
    sessionStorage.removeItem("auth:validated-token");
  } catch {
    /* ignore */
  }

  try {
    // Force immediate in-memory auth reset.
    useAuth.setState({ user: null });
  } catch {
    /* ignore */
  } finally {
    // Allow a subsequent login to proceed normally.
    setTimeout(() => {
      _isClearingAuth = false;
    }, 500);
  }
}

function getAuthToken(): string {
  try {
    const stored = localStorage.getItem("ops-center-auth");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed?.state?.user?.token || "";
    }
  } catch {
    /* ignore */
  }
  return "";
}

function getCurrentUserId(): string {
  try {
    const stored = localStorage.getItem("ops-center-auth");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed?.state?.user?.user_id || "";
    }
  } catch {
    /* ignore */
  }
  return "";
}

async function fetcher<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...init,
  });
  if (!res.ok) {
    if (res.status === 401) {
      clearAuthOn401();
      throw new Error("Oturum süresi doldu veya geçersiz. Lütfen tekrar giriş yapın.");
    }
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

// ── Models & Config ─────────────────────────────────────────────

import type {
  ModelConfig,
  ThreadSummary,
  Thread,
  PerformanceBaseline,
} from "./types";

export const api = {
  getModels: () => fetcher<Record<string, ModelConfig>>("/api/models"),
  getPipelines: () =>
    fetcher<{ id: string; label: string }[]>("/api/pipelines"),
  health: () => fetcher<{ status: string }>("/api/health"),

  /** Validate current token; 401 clears auth and throws. Use before opening WS / loading data. */
  me: () =>
    fetcher<{ user_id: string; full_name: string }>("/api/auth/me"),

  // Threads
  listThreads: (limit = 20) => {
    const uid = getCurrentUserId();
    return fetcher<ThreadSummary[]>(
      `/api/threads?limit=${limit}${uid ? `&user_id=${uid}` : ""}`,
    );
  },
  createThread: () => {
    const uid = getCurrentUserId();
    return fetcher<{ id: string }>(
      `/api/threads${uid ? `?user_id=${uid}` : ""}`,
      { method: "POST" },
    );
  },
  getThread: (id: string) => {
    const uid = getCurrentUserId();
    return fetcher<Thread>(`/api/threads/${id}${uid ? `?user_id=${uid}` : ""}`);
  },
  deleteThread: (id: string) => {
    const uid = getCurrentUserId();
    return fetcher<{ deleted: boolean }>(
      `/api/threads/${id}${uid ? `?user_id=${uid}` : ""}`,
      { method: "DELETE" },
    );
  },
  deleteAllThreads: () => {
    const uid = getCurrentUserId();
    return fetcher<{ deleted: number }>(
      `/api/threads${uid ? `?user_id=${uid}` : ""}`,
      { method: "DELETE" },
    );
  },

  // RAG
  ragIngest: (content: string, title: string, source = "") => {
    const user_id = getCurrentUserId();
    return fetcher("/api/rag/ingest", {
      method: "POST",
      body: JSON.stringify({ content, title, source, user_id }),
    });
  },
  ragQuery: (query: string, max_results = 5) => {
    const user_id = getCurrentUserId();
    return fetcher("/api/rag/query", {
      method: "POST",
      body: JSON.stringify({ query, max_results, user_id }),
    });
  },
  ragDocuments: () => {
    const user_id = getCurrentUserId();
    return fetcher(`/api/rag/documents${user_id ? `?user_id=${user_id}` : ""}`);
  },

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

  // Eval (agent-orchestration-improve-agent baseline)
  evalStats: () => fetcher("/api/eval/stats"),
  evalBaseline: (agentRole?: string) =>
    fetcher<PerformanceBaseline>(
      agentRole
        ? `/api/eval/baseline?agent_role=${encodeURIComponent(agentRole)}`
        : "/api/eval/baseline",
    ),

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

const authHeaders = (): HeadersInit => {
  const token = getAuthToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

export async function getMemoryStats() {
  const res = await fetch(`${BASE}/api/memory/stats`, {
    headers: authHeaders(),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function getMemoryLayers() {
  const res = await fetch(`${BASE}/api/memory/layers`, {
    headers: authHeaders(),
  });
  if (!res.ok) return { working: [], episodic: [], semantic: [] };
  return res.json();
}

export async function deleteMemory(memoryId: number) {
  const res = await fetch(`${BASE}/api/memory/${memoryId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return res.ok;
}

export async function getAutoSkills() {
  const res = await fetch(`${BASE}/api/skills/auto`, {
    headers: authHeaders(),
  });
  if (!res.ok) return [];
  return res.json();
}

export async function getDbHealth() {
  const res = await fetch(`${BASE}/api/db/health`, {
    headers: authHeaders(),
  });
  if (!res.ok) return { status: "error" };
  return res.json();
}
