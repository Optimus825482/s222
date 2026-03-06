// ── Agent & Model Types ─────────────────────────────────────────

export type AgentRole =
  | "orchestrator"
  | "thinker"
  | "speed"
  | "researcher"
  | "reasoner"
  | "observer";

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

// ── Agent Health & Performance Types ────────────────────────────

export type AgentStatus = "active" | "idle" | "offline" | "error";

export interface AgentHealth {
  role: AgentRole;
  name: string;
  status: AgentStatus;
  success_rate: number;
  avg_latency_ms: number;
  total_tokens: number;
  total_calls: number;
  error_count: number;
  last_active: string | null;
  uptime_pct: number;
}

export interface AgentPerformance {
  role: string;
  baseline: PerformanceBaseline;
  recent_tasks: {
    id: string;
    status: TaskStatus;
    latency_ms: number;
    tokens: number;
    timestamp: string;
  }[];
  skill_usage: { skill_id: string; count: number }[];
  error_patterns: { type: string; count: number; last_seen: string }[];
}

export interface AgentLeaderboardEntry {
  role: AgentRole;
  name: string;
  score: number;
  success_rate: number;
  avg_latency_ms: number;
  efficiency: number;
  rank: number;
}

// ── Skill Discovery Types ───────────────────────────────────────

export interface SkillRecommendation {
  skill_id: string;
  name: string;
  description: string;
  relevance_score: number;
  category: string;
  recommended_agent: AgentRole | null;
}

export interface AutoDiscoveryResult {
  discovered: number;
  skills: { skill_id: string; name: string; pattern: string }[];
}

// ── Security & Monitoring Types ─────────────────────────────────

export interface AuditLogEntry {
  timestamp: string;
  event_type: "login" | "logout" | "api_call" | "auth_failure" | "anomaly";
  user_id: string;
  details: string;
  ip?: string;
  severity: "info" | "warning" | "critical";
}

export interface SystemStats {
  active_threads: number;
  total_tasks: number;
  total_events: number;
  memory_usage_mb: number;
  db_status: string;
  uptime_seconds: number;
  agents_active: number;
  agents_total: number;
}

export interface AnomalyReport {
  anomalies: {
    type:
      | "high_error_rate"
      | "slow_response"
      | "token_spike"
      | "unusual_pattern";
    agent_role: AgentRole;
    severity: "low" | "medium" | "high";
    description: string;
    detected_at: string;
    metric_value: number;
    threshold: number;
  }[];
  overall_health: "healthy" | "degraded" | "critical";
}

export interface ThreadAnalytics {
  thread_id: string;
  duration_ms: number;
  agent_participation: Record<
    AgentRole,
    { calls: number; tokens: number; latency_ms: number }
  >;
  pipeline_types_used: PipelineType[];
  tool_calls: { tool: string; count: number; avg_latency_ms: number }[];
  event_timeline: { timestamp: string; event_type: string; agent: string }[];
  total_tokens: number;
  total_cost_estimate: number;
}

// ── Coordination Types ──────────────────────────────────────────

export interface CoordinationCandidate {
  role: AgentRole;
  name: string;
  score: number;
  success_rate: number;
  avg_latency_ms: number;
  avg_score: number;
  total_tasks: number;
  color: string;
  icon: string;
}

export interface CoordinationAssignment {
  assigned_agent: CoordinationCandidate | null;
  all_candidates: CoordinationCandidate[];
  task_type: string;
  complexity: string;
  timestamp: string;
}

export interface CompetencyMatrixEntry {
  role: AgentRole;
  name: string;
  color: string;
  icon: string;
  scores: Record<string, number>;
  overall: number;
}

export interface CompetencyMatrix {
  categories: string[];
  matrix: CompetencyMatrixEntry[];
  timestamp: string;
}

export interface RotationEntry {
  task_id: string;
  sub_task_id: string;
  description: string;
  assigned_agent: string;
  status: string;
  latency_ms: number;
  tokens: number;
  timestamp: string;
}

// ── Ecosystem Types ─────────────────────────────────────────────

export interface EcosystemNode {
  id: string;
  name: string;
  role: AgentRole;
  color: string;
  icon: string;
  total_tasks: number;
  success_rate: number;
  status: "active" | "idle";
}

export interface EcosystemEdge {
  source: string;
  target: string;
  weight: number;
  label: string;
}

export interface EcosystemData {
  nodes: EcosystemNode[];
  edges: EcosystemEdge[];
  total_interactions: number;
  timestamp: string;
}

// ── Agent Messaging Types ───────────────────────────────────────

export interface AgentDirectMessage {
  id: string;
  sender: string;
  receiver: string;
  content: string;
  timestamp: string;
  user_id: string;
}

// ── Autonomous Evolution Types ──────────────────────────────────

export type ActionPriority = "critical" | "high" | "medium" | "low";
export type ActionStatus = "pending" | "in_progress" | "completed" | "skipped";

export interface ImprovementAction {
  id: string;
  title: string;
  description: string;
  priority: ActionPriority;
  status: ActionStatus;
  category: string;
  expected_impact: string;
  estimated_effort: string;
}

export interface ImprovementPlan {
  agent_role: AgentRole;
  agent_name: string;
  generated_at: string;
  overall_score: number;
  strengths: string[];
  weaknesses: string[];
  actions: ImprovementAction[];
  summary: string;
}

export interface LearningInsight {
  pattern: string;
  frequency: number;
  first_seen: string;
  last_seen: string;
  resolution: string | null;
  auto_applied: boolean;
}

export interface FailureLearning {
  agent_role: AgentRole;
  agent_name: string;
  total_failures: number;
  analyzed_at: string;
  insights: LearningInsight[];
  strategy_adjustments: {
    parameter: string;
    old_value: string;
    new_value: string;
    reason: string;
    applied: boolean;
  }[];
  learning_rate: number;
}

export interface ApplyLearningResult {
  agent_role: AgentRole;
  applied_count: number;
  skipped_count: number;
  details: { action: string; result: "applied" | "skipped"; reason: string }[];
  timestamp: string;
}
