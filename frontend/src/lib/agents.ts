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

/** Orchestration pattern (Kiro: parallel specialists / pipeline / swarm) */
export type OrchestrationPattern =
  | "parallel_specialists"
  | "pipeline"
  | "swarm"
  | "hybrid"
  | "auto";

export const PIPELINE_OPTIONS = [
  {
    id: "auto",
    label: "Otomatik",
    short: "Oto",
    desc: "Sisteme bırak, en uygun pipeline seçilsin",
    pattern: "auto" as OrchestrationPattern,
  },
  {
    id: "deep_research",
    label: "Derin Araştırma",
    short: "Araştır",
    desc: "Kapsamlı web araştırması + çoklu analiz",
    pattern: "pipeline" as OrchestrationPattern,
  },
  {
    id: "parallel",
    label: "Paralel",
    short: "Paralel",
    desc: "Paralel uzmanlar: tüm agent'lar aynı anda çalışır, sonuçlar birleştirilir",
    pattern: "parallel_specialists" as OrchestrationPattern,
  },
  {
    id: "sequential",
    label: "Sıralı",
    short: "Sıralı",
    desc: "Pipeline: agent'lar sırayla çalışır, her biri öncekinin çıktısını kullanır",
    pattern: "pipeline" as OrchestrationPattern,
  },
  {
    id: "consensus",
    label: "Uzlaşı",
    short: "Uzlaşı",
    desc: "Agent'lar tartışıp ortak karara varır",
    pattern: "swarm" as OrchestrationPattern,
  },
  {
    id: "iterative",
    label: "Tekrarlı",
    short: "Tekrar",
    desc: "Sonuç iyileşene kadar döngü yapar",
    pattern: "pipeline" as OrchestrationPattern,
  },
  {
    id: "idea_to_project",
    label: "Proje Oluştur",
    short: "Proje",
    desc: "Fikirden tam proje planına dönüştürür",
    pattern: "pipeline" as OrchestrationPattern,
  },
  {
    id: "brainstorm",
    label: "Beyin Fırtınası",
    short: "Tartış",
    desc: "Swarm: agent'lar konu üzerinde tartışır, farklı bakış açıları sunar",
    pattern: "swarm" as OrchestrationPattern,
  },
] as const;

export const EVENT_ICONS: Record<
  string,
  { icon: string; label: string; color: string }
> = {
  routing_decision: { icon: "🧭", label: "Yönlendirme", color: "#ec4899" },
  routing: { icon: "🧭", label: "Yönlendirme", color: "#ec4899" },
  agent_start: { icon: "🚀", label: "Başlatıldı", color: "#3b82f6" },
  agent_thinking: { icon: "💭", label: "Düşünüyor", color: "#a78bfa" },
  thinking: { icon: "💭", label: "Düşünüyor", color: "#a78bfa" },
  tool_call: { icon: "🔧", label: "Araç", color: "#f59e0b" },
  tool_result: { icon: "📋", label: "Sonuç", color: "#10b981" },
  pipeline_start: { icon: "▶️", label: "Pipeline", color: "#3b82f6" },
  pipeline_step: { icon: "⏩", label: "Adım", color: "#06b6d4" },
  pipeline_complete: { icon: "✅", label: "Tamamlandı", color: "#10b981" },
  pipeline: { icon: "⏩", label: "Pipeline", color: "#06b6d4" },
  synthesis: { icon: "🔗", label: "Sentez", color: "#8b5cf6" },
  error: { icon: "⚠️", label: "Hata", color: "#ef4444" },
  response: { icon: "💬", label: "Yanıt", color: "#22d3ee" },
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
