import type { AgentRole } from "./types";

export const AGENT_CONFIG: Record<
  AgentRole,
  { icon: string; color: string; name: string }
> = {
  orchestrator: { icon: "🧠", color: "#ec4899", name: "Qwen3 Next 80B" },
  thinker: { icon: "🔬", color: "#00e5ff", name: "MiniMax M2.1" },
  speed: { icon: "⚡", color: "#a78bfa", name: "Step 3.5 Flash" },
  researcher: { icon: "🔍", color: "#f59e0b", name: "GLM 4.7" },
  reasoner: { icon: "🌊", color: "#10b981", name: "Nemotron 3 Nano" },
};

export const PIPELINE_OPTIONS = [
  {
    id: "auto",
    label: "Otomatik",
    short: "Oto",
    desc: "Sisteme bırak, en uygun pipeline seçilsin",
  },
  {
    id: "deep_research",
    label: "Derin Araştırma",
    short: "Araştır",
    desc: "Kapsamlı web araştırması + çoklu analiz",
  },
  {
    id: "parallel",
    label: "Paralel",
    short: "Paralel",
    desc: "Tüm agent'lar aynı anda çalışır, hızlı sonuç",
  },
  {
    id: "sequential",
    label: "Sıralı",
    short: "Sıralı",
    desc: "Agent'lar sırayla çalışır, her biri öncekinin çıktısını kullanır",
  },
  {
    id: "consensus",
    label: "Uzlaşı",
    short: "Uzlaşı",
    desc: "Agent'lar tartışıp ortak karara varır",
  },
  {
    id: "iterative",
    label: "Tekrarlı",
    short: "Tekrar",
    desc: "Sonuç iyileşene kadar döngü yapar",
  },
  {
    id: "idea_to_project",
    label: "Proje Oluştur",
    short: "Proje",
    desc: "Fikirden tam proje planına dönüştürür",
  },
  {
    id: "brainstorm",
    label: "Beyin Fırtınası",
    short: "Tartış",
    desc: "Agent'lar konu üzerinde tartışır, farklı bakış açıları sunar",
  },
] as const;

export const EVENT_ICONS: Record<
  string,
  { icon: string; label: string; color: string }
> = {
  routing_decision: { icon: "🧭", label: "Routing", color: "#ec4899" },
  agent_start: { icon: "🚀", label: "Start", color: "#3b82f6" },
  agent_thinking: { icon: "💭", label: "Thinking", color: "#a78bfa" },
  tool_call: { icon: "🔧", label: "Tool", color: "#f59e0b" },
  tool_result: { icon: "📋", label: "Result", color: "#10b981" },
  pipeline_start: { icon: "▶️", label: "Pipeline", color: "#3b82f6" },
  pipeline_step: { icon: "⏩", label: "Step", color: "#06b6d4" },
  pipeline_complete: { icon: "✅", label: "Done", color: "#10b981" },
  synthesis: { icon: "🔗", label: "Synthesis", color: "#8b5cf6" },
  error: { icon: "⚠️", label: "Error", color: "#ef4444" },
};

export function getAgentInfo(role: string) {
  return (
    AGENT_CONFIG[role as AgentRole] ?? {
      icon: "⚙️",
      color: "#6b7280",
      name: role,
    }
  );
}
