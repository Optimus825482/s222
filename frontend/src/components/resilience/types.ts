/* Resilience panel shared types */

export interface HealthComponent {
  status: string;
  error?: string;
  channels?: number;
  dlq_size?: number;
  sdk_installed?: boolean;
  tracer_active?: boolean;
  enabled?: boolean;
}

export interface HealthData {
  status: string;
  components: Record<string, HealthComponent>;
}

export interface ThresholdData {
  metric: string;
  low: number;
  high: number;
  mean: number;
  std: number;
  sample_count: number;
}

export interface ChaosReport {
  enabled: boolean;
  total_injections: number;
  history: ChaosHistoryItem[];
}

export interface ChaosHistoryItem {
  scenario: string;
  target: string;
  success: boolean;
  detail: string;
  recovery_ms: number;
  timestamp: string;
}

export interface ModerationItem {
  id: number;
  solution: string;
  confidence: number;
  source_agents: string;
  submitted_at: string;
  reason: string;
}

export interface FederatedStats {
  registered_nodes: number;
  current_round: number;
  model_version: string;
  total_rounds: number;
}

export interface RoundStatus {
  round_number: number;
  status: string;
  min_participants?: number;
  timeout_seconds?: number;
  deltas_received?: number;
}

export type ResilienceTab =
  | "health"
  | "thresholds"
  | "chaos"
  | "moderation"
  | "federated";

export const TABS: { key: ResilienceTab; label: string; icon: string }[] = [
  { key: "health", label: "Sistem Sağlığı", icon: "💚" },
  { key: "thresholds", label: "Eşikler", icon: "📊" },
  { key: "chaos", label: "Chaos", icon: "🔥" },
  { key: "moderation", label: "Moderasyon", icon: "🛡️" },
  { key: "federated", label: "Federated", icon: "🌐" },
];

export const CHAOS_SCENARIOS = [
  { value: "agent_timeout", label: "Agent Timeout" },
  { value: "event_bus_overload", label: "EventBus Overload" },
  { value: "tool_latency", label: "Tool Latency" },
  { value: "agent_crash", label: "Agent Crash" },
  { value: "db_connection_drop", label: "DB Connection Drop" },
  { value: "memory_pressure", label: "Memory Pressure" },
] as const;

export const REFRESH_MS = 10_000;
