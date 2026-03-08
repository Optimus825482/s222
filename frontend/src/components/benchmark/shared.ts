import { AGENT_CONFIG } from "@/lib/agents";
import type { AgentRole } from "@/lib/types";

export const allRoles = Object.keys(AGENT_CONFIG) as AgentRole[];

export const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";
export const sCls =
  "bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50";

export const CATEGORIES = [
  "speed",
  "quality",
  "reasoning",
  "tool_use",
  "creativity",
] as const;

export type BenchTab = "leaderboard" | "run" | "results" | "trend" | "compare";

export const BENCH_TABS: { key: BenchTab; label: string; icon: string }[] = [
  { key: "leaderboard", label: "Sıralama", icon: "🏆" },
  { key: "run", label: "Test Çalıştır", icon: "▶️" },
  { key: "results", label: "Sonuçlar", icon: "📊" },
  { key: "trend", label: "Trend", icon: "📈" },
  { key: "compare", label: "Karşılaştır", icon: "⚔️" },
];

export const TIME_FILTERS = [
  { value: "", label: "Tümü" },
  { value: "7", label: "7 Gün" },
  { value: "30", label: "30 Gün" },
  { value: "90", label: "90 Gün" },
] as const;

export const TREND_COLORS = [
  "#06b6d4",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type AnyData = any;

export function ai(r: string) {
  return (
    AGENT_CONFIG[r as AgentRole] ?? { icon: "⚙️", color: "#6b7280", name: r }
  );
}

export function scoreColor(s: number) {
  if (s >= 4) return "bg-emerald-500";
  if (s >= 3) return "bg-cyan-500";
  if (s >= 2) return "bg-amber-500";
  return "bg-red-500";
}

export function scoreText(s: number) {
  if (s >= 4) return "text-emerald-400";
  if (s >= 3) return "text-cyan-400";
  if (s >= 2) return "text-amber-400";
  return "text-red-400";
}
