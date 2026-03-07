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
      throw new Error(
        "Oturum süresi doldu veya geçersiz. Lütfen tekrar giriş yapın.",
      );
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
  AgentHealth,
  AgentPerformance,
  AgentLeaderboardEntry,
  AutoDiscoveryResult,
  SkillRecommendation,
  ProactiveSuggestionsResponse,
  AuditLogEntry,
  SystemStats,
  AnomalyReport,
  ThreadAnalytics,
  CoordinationAssignment,
  CompetencyMatrix,
  RotationEntry,
  EcosystemData,
  AgentDirectMessage,
  ImprovementPlan,
  FailureLearning,
  ApplyLearningResult,
  AutonomousConversation,
  AutoChatConfig,
  PostTaskMeeting,
  WorkflowTemplate,
  WorkflowRunResult,
  ScheduledWorkflow,
  ChartResult,
  ChartListItem,
} from "./types";

export const api = {
  getModels: () => fetcher<Record<string, ModelConfig>>("/api/models"),
  getPipelines: () =>
    fetcher<{ id: string; label: string }[]>("/api/pipelines"),
  health: () => fetcher<{ status: string }>("/api/health"),

  /** Validate current token; 401 clears auth and throws. Use before opening WS / loading data. */
  me: () => fetcher<{ user_id: string; full_name: string }>("/api/auth/me"),

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

  // Agent Health & Performance
  getAgentsHealth: () => fetcher<AgentHealth[]>("/api/agents/health"),
  getAgentPerformance: (role: string) =>
    fetcher<AgentPerformance>(
      `/api/agents/${encodeURIComponent(role)}/performance`,
    ),
  getAgentLeaderboard: () =>
    fetcher<AgentLeaderboardEntry[]>("/api/agents/leaderboard"),

  // Skill Discovery
  autoDiscoverSkills: () =>
    fetcher<AutoDiscoveryResult>("/api/skills/auto-discover", {
      method: "POST",
    }),
  getSkillRecommendations: (query = "") =>
    fetcher<SkillRecommendation[]>(
      `/api/skills/recommendations${query ? `?query=${encodeURIComponent(query)}` : ""}`,
    ),
  getProactiveSkillSuggestions: () =>
    fetcher<ProactiveSuggestionsResponse>("/api/skills/proactive-suggestions"),

  // Security & Monitoring
  getAuditLog: (limit = 50) =>
    fetcher<AuditLogEntry[]>(`/api/security/audit-log?limit=${limit}`),
  getSystemStats: () => fetcher<SystemStats>("/api/monitoring/system-stats"),
  getAnomalies: () => fetcher<AnomalyReport>("/api/monitoring/anomalies"),

  // Thread Analytics
  getThreadAnalytics: (threadId: string) =>
    fetcher<ThreadAnalytics>(`/api/threads/${threadId}/analytics`),

  // Memory Advanced
  correlateMemories: (
    query: string,
    maxResults = 10,
    timeWindowHours?: number,
  ) =>
    fetcher<{ clusters: unknown[]; total_found: number }>(
      `/api/memory/correlate?query=${encodeURIComponent(query)}&max_results=${maxResults}${timeWindowHours ? `&time_window_hours=${timeWindowHours}` : ""}`,
    ),
  getMemoryTimeline: (
    hours = 24,
    groupBy: "hour" | "day" | "category" = "hour",
  ) =>
    fetcher<{ period?: string; group?: string; count: number }[]>(
      `/api/memory/timeline?hours=${hours}&group_by=${groupBy}`,
    ),
  getRelatedMemories: (memoryId: number, maxResults = 5) =>
    fetcher<unknown[]>(
      `/api/memory/${memoryId}/related?max_results=${maxResults}`,
    ),

  // Coordination
  assignBestAgent: (taskType = "general", complexity = "medium") =>
    fetcher<CoordinationAssignment>(
      `/api/coordination/assign?task_type=${encodeURIComponent(taskType)}&complexity=${encodeURIComponent(complexity)}`,
      { method: "POST" },
    ),
  getCompetencyMatrix: () =>
    fetcher<CompetencyMatrix>("/api/coordination/matrix"),
  getRotationHistory: (limit = 50) =>
    fetcher<{ total: number; entries: RotationEntry[] }>(
      `/api/coordination/rotation-history?limit=${limit}`,
    ),

  // Ecosystem
  getAgentEcosystem: () => fetcher<EcosystemData>("/api/agents/ecosystem"),

  // Agent Messaging
  sendAgentMessage: (sender: string, receiver: string, content: string) =>
    fetcher<{ message: AgentDirectMessage; total_messages: number }>(
      `/api/agents/message?sender=${encodeURIComponent(sender)}&receiver=${encodeURIComponent(receiver)}&content=${encodeURIComponent(content)}`,
      { method: "POST" },
    ),
  getAgentMessages: (limit = 50, sender?: string, receiver?: string) => {
    let url = `/api/agents/messages?limit=${limit}`;
    if (sender) url += `&sender=${encodeURIComponent(sender)}`;
    if (receiver) url += `&receiver=${encodeURIComponent(receiver)}`;
    return fetcher<{ total: number; messages: AgentDirectMessage[] }>(url);
  },

  // Autonomous Evolution
  getImprovementPlan: (role: string) =>
    fetcher<ImprovementPlan>(
      `/api/agents/${encodeURIComponent(role)}/improvement-plan`,
    ),
  getFailureLearnings: (role: string) =>
    fetcher<FailureLearning>(
      `/api/agents/${encodeURIComponent(role)}/failure-learnings`,
    ),
  applyLearning: (role: string) =>
    fetcher<ApplyLearningResult>(
      `/api/agents/apply-learning?role=${encodeURIComponent(role)}`,
      { method: "POST" },
    ),

  // Autonomous Chat (ClaudBot-style)
  triggerAutonomousChat: () =>
    fetcher<{
      conversation: AutonomousConversation;
      total_conversations: number;
    }>("/api/agents/autonomous-chat/trigger", { method: "POST" }),
  getAutonomousConversations: (limit = 20, agent?: string) => {
    let url = `/api/agents/autonomous-chat/conversations?limit=${limit}`;
    if (agent) url += `&agent=${encodeURIComponent(agent)}`;
    return fetcher<{
      total: number;
      conversations: AutonomousConversation[];
      timestamp: string;
    }>(url);
  },
  getAutoChatConfig: () =>
    fetcher<{ config: AutoChatConfig }>("/api/agents/autonomous-chat/config"),
  updateAutoChatConfig: (config: Partial<AutoChatConfig>) =>
    fetcher<{ config: AutoChatConfig }>("/api/agents/autonomous-chat/config", {
      method: "POST",
      body: JSON.stringify(config),
    }),

  // Post-Task Meetings
  triggerMeeting: (taskSummary = "Manuel toplantı") =>
    fetcher<{ meeting: PostTaskMeeting; total_meetings: number }>(
      `/api/agents/autonomous-chat/meeting?task_summary=${encodeURIComponent(taskSummary)}`,
      { method: "POST" },
    ),
  getMeetings: (limit = 20) =>
    fetcher<{ total: number; meetings: PostTaskMeeting[]; timestamp: string }>(
      `/api/agents/autonomous-chat/meetings?limit=${limit}`,
    ),

  // Agent Identity (SOUL.md Pattern)
  getAgentIdentity: (role: string) =>
    fetcher<import("./types").AgentIdentity>(
      `/api/agents/${encodeURIComponent(role)}/identity`,
    ),
  updateIdentityFile: (role: string, fileType: string, content: string) =>
    fetcher<{ status: string }>(
      `/api/agents/${encodeURIComponent(role)}/identity/${encodeURIComponent(fileType)}`,
      { method: "PUT", body: JSON.stringify({ content }) },
    ),
  addAgentMemoryEntry: (role: string, entry: string) =>
    fetcher<{ status: string }>(
      `/api/agents/${encodeURIComponent(role)}/memory`,
      { method: "POST", body: JSON.stringify({ entry }) },
    ),
  initializeAllIdentities: () =>
    fetcher<{ initialized: number; agents: string[] }>(
      "/api/agents/identity/initialize",
      { method: "POST" },
    ),
  listIdentityAgents: () =>
    fetcher<{ agents: string[] }>("/api/agents/identity/list"),

  // ── Workflow API ──
  getTemplates: () => fetcher<WorkflowTemplate[]>("/api/workflows/templates"),

  getHistory: (limit = 20) =>
    fetcher<WorkflowRunResult[]>(`/api/workflows/history?limit=${limit}`),

  getWorkflowDetail: (workflowId: string) =>
    fetcher<WorkflowRunResult>(`/api/workflows/history/${workflowId}`),

  runWorkflow: (
    template: string,
    variables: Record<string, unknown> = {},
    customSteps?: unknown[],
  ) =>
    fetcher<WorkflowRunResult>("/api/workflows/run", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ template, variables, custom_steps: customSteps }),
    }),

  getSchedules: () => fetcher<ScheduledWorkflow[]>("/api/workflows/schedules"),

  addSchedule: (data: {
    schedule_id: string;
    template: string;
    variables?: Record<string, unknown>;
    cron_expression: string;
    enabled?: boolean;
  }) =>
    fetcher<ScheduledWorkflow>("/api/workflows/schedules", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(data),
    }),

  removeSchedule: (scheduleId: string) =>
    fetcher<{ status: string }>(`/api/workflows/schedules/${scheduleId}`, {
      method: "DELETE",
      headers: authHeaders(),
    }),

  toggleSchedule: (scheduleId: string, enabled: boolean) =>
    fetcher<ScheduledWorkflow>(`/api/workflows/schedules/${scheduleId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ enabled }),
    }),

  // ── Chart API ──
  generateChart: (
    chartType: string,
    data: Record<string, unknown>,
    title: string = "Chart",
    width: number = 800,
    height: number = 450,
  ) =>
    fetcher<ChartResult>("/api/charts/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        chart_type: chartType,
        data,
        title,
        width,
        height,
      }),
    }),

  listCharts: (limit: number = 30) =>
    fetcher<ChartListItem[]>(`/api/charts?limit=${limit}`),

  getChart: (chartId: string) =>
    fetcher<{ chart_id: string; image_base64: string }>(
      `/api/charts/${chartId}`,
    ),

  deleteChart: (chartId: string) =>
    fetcher<{ status: string; chart_id: string }>(`/api/charts/${chartId}`, {
      method: "DELETE",
      headers: authHeaders(),
    }),
};

// ── Memory API (uses fetcher for consistent auth + 401 handling) ─

export async function getMemoryStats() {
  try {
    return await fetcher<Record<string, unknown>>("/api/memory/stats");
  } catch {
    return null;
  }
}

export async function getMemoryLayers() {
  try {
    return await fetcher<{
      working: unknown[];
      episodic: unknown[];
      semantic: unknown[];
    }>("/api/memory/layers");
  } catch {
    return { working: [], episodic: [], semantic: [] };
  }
}

export async function deleteMemory(memoryId: number) {
  try {
    await fetcher(`/api/memory/${memoryId}`, { method: "DELETE" });
    return true;
  } catch {
    return false;
  }
}

export async function getAutoSkills() {
  try {
    return await fetcher<unknown[]>("/api/skills/auto");
  } catch {
    return [];
  }
}

export async function getDbHealth() {
  try {
    return await fetcher<{ status: string }>("/api/db/health");
  } catch {
    return { status: "error" };
  }
}

// ── Benchmark API ───────────────────────────────────────────────

export const benchmarkApi = {
  async getScenarios(category?: string) {
    const q = category ? `?category=${category}` : "";
    const url = `${BASE}/api/benchmarks/scenarios${q}`;
    console.log("[DEBUG] benchmarkApi.getScenarios →", url);
    const res = await fetch(url, { headers: authHeaders() });
    console.log("[DEBUG] benchmarkApi.getScenarios ←", res.status);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getLeaderboard() {
    const url = `${BASE}/api/benchmarks/leaderboard`;
    console.log("[DEBUG] benchmarkApi.getLeaderboard →", url);
    const res = await fetch(url, { headers: authHeaders() });
    console.log("[DEBUG] benchmarkApi.getLeaderboard ←", res.status);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getResults(agentRole?: string, limit = 50) {
    const params = new URLSearchParams();
    if (agentRole) params.set("agent_role", agentRole);
    params.set("limit", String(limit));
    const url = `${BASE}/api/benchmarks/results?${params}`;
    console.log("[DEBUG] benchmarkApi.getResults →", url);
    const res = await fetch(url, { headers: authHeaders() });
    console.log("[DEBUG] benchmarkApi.getResults ←", res.status);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async run(body: {
    agent_role?: string;
    scenario_id?: string;
    category?: string;
  }) {
    const res = await fetch(`${BASE}/api/benchmarks/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async compare(roleA: string, roleB: string) {
    const res = await fetch(
      `${BASE}/api/benchmarks/compare?role_a=${roleA}&role_b=${roleB}`,
      { headers: authHeaders() },
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },
};

// ── Error Pattern Analysis API ──────────────────────────────────

export const errorPatternApi = {
  async recordError(body: {
    agent_role: string;
    error_message: string;
    task_type?: string;
    context?: Record<string, unknown>;
  }) {
    const url = `${BASE}/api/errors/record`;
    console.log("[DEBUG errorPatternApi.recordError] POST", url);
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body),
    });
    console.log("[DEBUG errorPatternApi.recordError] status:", res.status);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getStats(agentRole?: string, hours = 24) {
    const params = new URLSearchParams();
    if (agentRole) params.set("agent_role", agentRole);
    params.set("hours", String(hours));
    const url = `${BASE}/api/errors/stats?${params}`;
    console.log("[DEBUG errorPatternApi.getStats] GET", url);
    const res = await fetch(url, { headers: authHeaders() });
    console.log("[DEBUG errorPatternApi.getStats] status:", res.status);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getTimeline(hours = 24) {
    const res = await fetch(`${BASE}/api/errors/timeline?hours=${hours}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getPatterns(status?: string, agentRole?: string) {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (agentRole) params.set("agent_role", agentRole);
    const res = await fetch(`${BASE}/api/errors/patterns?${params}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async detectPatterns(hours = 24) {
    const res = await fetch(`${BASE}/api/errors/detect?hours=${hours}`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getRecommendations() {
    const res = await fetch(`${BASE}/api/errors/recommendations`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async resolvePattern(patternId: number, resolutionNotes = "") {
    const res = await fetch(
      `${BASE}/api/errors/patterns/${patternId}/resolve`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ resolution_notes: resolutionNotes }),
      },
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async suppressPattern(patternId: number) {
    const res = await fetch(
      `${BASE}/api/errors/patterns/${patternId}/suppress`,
      {
        method: "POST",
        headers: authHeaders(),
      },
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },
};

// ── Auto-Optimizer API ──────────────────────────────────────────

export const optimizerApi = {
  async getStats() {
    const url = `${BASE}/api/optimizer/stats`;
    console.log("[DEBUG] optimizerApi.getStats →", url);
    const res = await fetch(url, { headers: authHeaders() });
    console.log("[DEBUG] optimizerApi.getStats ←", res.status);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getRecommendations(
    status = "pending",
    category?: string,
    priority?: string,
  ) {
    const params = new URLSearchParams({ status });
    if (category) params.set("category", category);
    if (priority) params.set("priority", priority);
    const url = `${BASE}/api/optimizer/recommendations?${params}`;
    console.log("[DEBUG] optimizerApi.getRecommendations →", url);
    const res = await fetch(url, { headers: authHeaders() });
    console.log("[DEBUG] optimizerApi.getRecommendations ←", res.status);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async analyze() {
    const url = `${BASE}/api/optimizer/analyze`;
    console.log("[DEBUG] optimizerApi.analyze →", url);
    const res = await fetch(url, { method: "POST", headers: authHeaders() });
    console.log("[DEBUG] optimizerApi.analyze ←", res.status);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async apply(recId: number) {
    const res = await fetch(
      `${BASE}/api/optimizer/recommendations/${recId}/apply`,
      { method: "POST", headers: authHeaders() },
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async dismiss(recId: number) {
    const res = await fetch(
      `${BASE}/api/optimizer/recommendations/${recId}/dismiss`,
      { method: "POST", headers: authHeaders() },
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getAgentProfile(role: string) {
    const res = await fetch(
      `${BASE}/api/optimizer/agent/${encodeURIComponent(role)}`,
      { headers: authHeaders() },
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getHistory(limit = 50) {
    const res = await fetch(`${BASE}/api/optimizer/history?limit=${limit}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },
};

// ── Cost Tracker API ────────────────────────────────────────────

export const costTrackerApi = {
  async getSummary(hours = 24) {
    const url = `${BASE}/api/costs/summary?hours=${hours}`;
    console.log("[DEBUG costTrackerApi.getSummary] GET", url);
    const res = await fetch(url, { headers: authHeaders() });
    console.log("[DEBUG costTrackerApi.getSummary] status:", res.status);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getTimeline(hours = 24) {
    const res = await fetch(`${BASE}/api/costs/timeline?hours=${hours}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getTopConsumers(limit = 10) {
    const res = await fetch(`${BASE}/api/costs/top-consumers?limit=${limit}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getBudgetStatus(agentRole?: string) {
    const params = new URLSearchParams();
    if (agentRole) params.set("agent_role", agentRole);
    const res = await fetch(`${BASE}/api/costs/budget?${params}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },
};

// ── Cost Tracking API ───────────────────────────────────────────

export const costApi = {
  async recordUsage(body: {
    agent_role: string;
    model: string;
    input_tokens: number;
    output_tokens: number;
    task_type?: string;
    metadata?: Record<string, unknown>;
  }) {
    const res = await fetch(`${BASE}/api/costs/record`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getSummary(hours = 24) {
    const res = await fetch(`${BASE}/api/costs/summary?hours=${hours}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getTimeline(hours = 24, granularity = "hour") {
    const params = new URLSearchParams({ hours: String(hours), granularity });
    const res = await fetch(`${BASE}/api/costs/timeline?${params}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getAgentCosts(agentRole: string, hours = 24) {
    const res = await fetch(
      `${BASE}/api/costs/agent/${encodeURIComponent(agentRole)}?hours=${hours}`,
      { headers: authHeaders() },
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getTopConsumers(hours = 24, limit = 10) {
    const params = new URLSearchParams({
      hours: String(hours),
      limit: String(limit),
    });
    const res = await fetch(`${BASE}/api/costs/top-consumers?${params}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async setBudget(body: {
    agent_role?: string | null;
    daily_limit: number;
    alert_threshold?: number;
  }) {
    const res = await fetch(`${BASE}/api/costs/budget`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async checkBudget(agentRole?: string) {
    const params = agentRole
      ? `?agent_role=${encodeURIComponent(agentRole)}`
      : "";
    const res = await fetch(`${BASE}/api/costs/budget${params}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getForecast(days = 7) {
    const res = await fetch(`${BASE}/api/costs/forecast?days=${days}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getUsageStats() {
    const res = await fetch(`${BASE}/api/costs/stats`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },
};

// ── Domain & Marketplace API ────────────────────────────────────

export const domainApi = {
  async listDomains() {
    const res = await fetch(`${BASE}/api/domains`, { headers: authHeaders() });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getDomainTools(domainId: string) {
    const res = await fetch(
      `${BASE}/api/domains/${encodeURIComponent(domainId)}/tools`,
      {
        headers: authHeaders(),
      },
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async autoDetect(query: string, topK = 3) {
    const res = await fetch(`${BASE}/api/domains/auto-detect`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ query, top_k: topK }),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getMarketplaceCatalog(category?: string, search?: string) {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (search) params.set("search", search);
    const q = params.toString() ? `?${params}` : "";
    const res = await fetch(`${BASE}/api/marketplace/catalog${q}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getMarketplaceStats() {
    const res = await fetch(`${BASE}/api/marketplace/stats`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async getMarketplace() {
    const res = await fetch(`${BASE}/api/domains/marketplace`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async discoverSkills() {
    const res = await fetch(`${BASE}/api/domains/discover`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  async toggleDomain(domainId: string, enabled: boolean) {
    const res = await fetch(
      `${BASE}/api/domains/${encodeURIComponent(domainId)}/toggle`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ enabled }),
      },
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  },

  // ── Workflow Engine API ──

  async getWorkflowTemplates() {
    return fetcher<
      {
        id: string;
        name: string;
        description: string;
        step_count: number;
        required_variables: string[];
      }[]
    >("/api/workflows/templates");
  },

  async getWorkflowHistory(limit = 20) {
    return fetcher<
      {
        id: number;
        workflow_id: string;
        status: string;
        step_results: Record<string, unknown>;
        error: string | null;
        duration_ms: number;
        variables: Record<string, unknown>;
        created_at: string;
      }[]
    >(`/api/workflows/history?limit=${limit}`);
  },

  async runWorkflow(
    template: string,
    variables: Record<string, string> = {},
    customSteps?: Record<string, unknown>[],
  ) {
    return fetcher<{
      workflow_id: string;
      status: string;
      step_results: Record<string, unknown>;
      error: string | null;
      duration_ms: number;
      variables: Record<string, unknown>;
    }>("/api/workflows/run", {
      method: "POST",
      body: JSON.stringify({ template, variables, custom_steps: customSteps }),
    });
  },

  async getScheduledWorkflows() {
    return fetcher<
      {
        id: string;
        template: string;
        cron: string;
        variables: Record<string, string>;
        enabled: boolean;
        next_run: string | null;
        last_run: string | null;
      }[]
    >("/api/workflows/schedules");
  },

  async createScheduledWorkflow(
    template: string,
    cron: string,
    variables: Record<string, string> = {},
  ) {
    return fetcher<{ id: string; message: string }>(
      "/api/workflows/schedules",
      {
        method: "POST",
        body: JSON.stringify({ template, cron, variables }),
      },
    );
  },

  async deleteScheduledWorkflow(scheduleId: string) {
    return fetcher<{ message: string }>(
      `/api/workflows/schedules/${scheduleId}`,
      { method: "DELETE" },
    );
  },

  async toggleScheduledWorkflow(scheduleId: string, enabled: boolean) {
    return fetcher<{ message: string }>(
      `/api/workflows/schedules/${scheduleId}/toggle`,
      {
        method: "POST",
        body: JSON.stringify({ enabled }),
      },
    );
  },
};

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
