// ── Agent & Model Types ─────────────────────────────────────────

export type AgentRole =
  | "orchestrator"
  | "thinker"
  | "speed"
  | "researcher"
  | "reasoner";

export interface ModelConfig {
  id: string;
  name: string;
  role: AgentRole;
  description: string;
  max_tokens: number;
  temperature: number;
  top_p: number;
  has_thinking: boolean;
  color: string;
  icon: string;
}

// ── Thread & Event Types ────────────────────────────────────────

export type EventType =
  | "user_message"
  | "routing_decision"
  | "agent_start"
  | "agent_thinking"
  | "agent_response"
  | "tool_call"
  | "tool_result"
  | "pipeline_start"
  | "pipeline_step"
  | "pipeline_complete"
  | "synthesis"
  | "error"
  | "human_request"
  | "human_response"
  | "teaching"
  | "code_execution"
  | "rag_query"
  | "evaluation";

export type TaskStatus =
  | "pending"
  | "routing"
  | "running"
  | "reviewing"
  | "completed"
  | "failed";

export type PipelineType =
  | "sequential"
  | "parallel"
  | "consensus"
  | "iterative"
  | "deep_research"
  | "idea_to_project"
  | "brainstorm"
  | "auto";

export interface AgentEvent {
  id: string;
  timestamp: string;
  event_type: EventType;
  agent_role: AgentRole | null;
  content: string;
  metadata: Record<string, unknown>;
}

export interface SubTask {
  id: string;
  description: string;
  assigned_agent: AgentRole;
  priority: number;
  depends_on: string[];
  skills: string[];
  status: TaskStatus;
  result: string | null;
  token_usage: number;
  latency_ms: number;
}

export interface Task {
  id: string;
  user_input: string;
  pipeline_type: PipelineType;
  sub_tasks: SubTask[];
  status: TaskStatus;
  final_result: string | null;
  total_tokens: number;
  total_latency_ms: number;
  created_at: string;
  completed_at: string | null;
}

export interface AgentMetrics {
  total_calls: number;
  total_tokens: number;
  total_latency_ms: number;
  success_count: number;
  error_count: number;
  last_active: string | null;
}

export interface Thread {
  id: string;
  events: AgentEvent[];
  tasks: Task[];
  agent_metrics: Record<string, AgentMetrics>;
  created_at: string;
}

export interface ThreadSummary {
  id: string;
  preview: string;
  created_at: string;
  task_count: number;
  event_count: number;
}

/** Performance baseline report (agent-orchestration-improve-agent skill) */
export interface PerformanceBaseline {
  task_success_rate_pct: number;
  total_tasks: number;
  success_count: number;
  avg_score: number;
  user_satisfaction_score: number;
  avg_latency_ms: number;
  total_tokens: number;
  token_efficiency_ratio: string;
  agent_role?: string | null;
}

// ── WebSocket Message Types ─────────────────────────────────────

export interface WSLiveEvent {
  type: "live_event";
  event_type: string;
  agent: string;
  content: string;
  extra: Record<string, unknown>;
  timestamp: number;
}

export interface WSResult {
  type: "result";
  thread_id: string;
  result: string;
  thread: Thread;
}

export interface WSError {
  type: "error";
  message: string;
  traceback?: string;
  thread_id?: string;
}

export interface WSOrchestratorChatReply {
  type: "orchestrator_chat_reply";
  content: string;
  is_status?: boolean;
}

export type WSMessage =
  | WSLiveEvent
  | WSResult
  | WSError
  | WSOrchestratorChatReply
  | { type: "monitor_start"; description: string }
  | { type: "monitor_complete"; summary: string }
  | { type: "monitor_error"; message: string }
  | { type: "pong" };
