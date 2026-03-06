"use client";

import { useEffect, useState } from "react";

/* ── Phase data ── */
interface Phase {
  id: string;
  title: string;
  icon: string;
  status: "done" | "wip" | "planned";
  color: string;
  border: string;
  progress: number;
  items: { done: boolean; label: string }[];
}

const PHASES: Phase[] = [
  {
    id: "v2",
    title: "Mevcut Durum (v2.0)",
    icon: "✅",
    status: "done",
    color: "text-emerald-400",
    border: "border-emerald-400/30",
    progress: 100,
    items: [
      {
        done: true,
        label:
          "6 Agent (Orchestrator, Thinker, Speed, Researcher, Reasoner, Observer)",
      },
      {
        done: true,
        label:
          "Pipeline Engine (sequential, parallel, consensus, iterative, deep_research, brainstorm)",
      },
      { done: true, label: "PostgreSQL + pgvector bellek sistemi" },
      { done: true, label: "RAG, Dynamic Skills, Teachability, MCP Client" },
      { done: true, label: "Sunum üretimi (MINI/MIDI/MAXI)" },
      { done: true, label: "Idea-to-Project pipeline" },
      { done: true, label: "Frontend: Next.js cockpit (9 tab)" },
      {
        done: true,
        label:
          "Agent İletişim Paneli (Tool Usage, Behavior, Otonom Sohbet, Toplantılar)",
      },
      { done: true, label: "Roadmap dialog + Task History sağ panel" },
      { done: true, label: "Reasoning model timeout desteği (180s)" },
    ],
  },
  {
    id: "f1",
    title: "Faz 1 — Workflow Engine",
    icon: "⚡",
    status: "wip",
    color: "text-amber-400",
    border: "border-amber-400/30",
    progress: 73,
    items: [
      { done: true, label: "Workflow Engine core" },
      {
        done: true,
        label:
          "Step tipleri: tool_call, agent_call, condition, parallel, human_approval",
      },
      { done: true, label: "Koşullu dallanma + Hata yönetimi + Rollback" },
      { done: true, label: "Workflow şablonları + Orchestrator entegrasyonu" },
      { done: true, label: "Backend API endpoints" },
      { done: false, label: "Frontend Workflow Builder UI" },
      { done: false, label: "Workflow execution history & replay" },
      { done: false, label: "Cron/zamanlı workflow tetikleme" },
    ],
  },
  {
    id: "f2",
    title: "Faz 2 — Domain Skills",
    icon: "🧠",
    status: "wip",
    color: "text-purple-400",
    border: "border-purple-400/30",
    progress: 70,
    items: [
      {
        done: true,
        label:
          "Domain Skills Engine + Finans/Hukuk/Mühendislik/Akademik modülleri",
      },
      { done: true, label: "Orchestrator entegrasyonu + Backend API" },
      { done: false, label: "Domain skill auto-discovery" },
      { done: false, label: "Skill marketplace" },
    ],
  },
  {
    id: "f3",
    title: "Faz 3 — Veri Analizi",
    icon: "📊",
    status: "planned",
    color: "text-sky-400",
    border: "border-sky-400/30",
    progress: 0,
    items: [
      { done: false, label: "Data Analysis Engine (pandas, numpy)" },
      { done: false, label: "Otomatik istatistiksel özetleme" },
      { done: false, label: "Chart/grafik üretimi" },
      { done: false, label: "CSV/Excel import ve analiz" },
      { done: false, label: "Dashboard template sistemi" },
    ],
  },
  {
    id: "f4",
    title: "Faz 4 — Gelişmiş RAG",
    icon: "�",
    status: "planned",
    color: "text-indigo-400",
    border: "border-indigo-400/30",
    progress: 0,
    items: [
      { done: false, label: "Multi-document comparison" },
      { done: false, label: "Belge sürüm kontrolü" },
      { done: false, label: "Cross-dataset sorgulama" },
      { done: false, label: "Bağlamsal özetleme" },
      { done: false, label: "Otomatik bilgi grafiği (knowledge graph)" },
    ],
  },
  {
    id: "f5",
    title: "Faz 5 — Güvenlik",
    icon: "�",
    status: "wip",
    color: "text-red-400",
    border: "border-red-400/30",
    progress: 20,
    items: [
      { done: true, label: "PII detection ve maskeleme" },
      { done: false, label: "Fact-checking engine" },
      { done: false, label: "Güvenlik açığı taraması" },
      { done: false, label: "Output validation pipeline" },
      { done: false, label: "Audit trail" },
    ],
  },
  {
    id: "f6",
    title: "Faz 6 — Performans",
    icon: "�",
    status: "wip",
    color: "text-amber-400",
    border: "border-amber-400/30",
    progress: 55,
    items: [
      { done: true, label: "Agent başarı oranı tracking + Confidence scoring" },
      { done: true, label: "Circuit breaker" },
      { done: true, label: "Tool usage analytics dashboard" },
      { done: true, label: "User behavior tracking" },
      { done: false, label: "Hata pattern analizi" },
      { done: false, label: "Otomatik optimizasyon önerileri" },
      { done: false, label: "Cost tracking (token → maliyet)" },
    ],
  },
  {
    id: "f7",
    title: "Faz 7 — API Entegrasyon",
    icon: "�",
    status: "wip",
    color: "text-cyan-400",
    border: "border-cyan-400/30",
    progress: 30,
    items: [
      { done: true, label: "MCP Client + Web fetch + SearXNG" },
      { done: false, label: "Webhook receiver/sender" },
      { done: false, label: "Generic REST API connector" },
      { done: false, label: "Slack/Discord entegrasyonu" },
      { done: false, label: "Scheduled task runner" },
    ],
  },
  {
    id: "f8",
    title: "Faz 8 — Multimedya",
    icon: "🎨",
    status: "wip",
    color: "text-pink-400",
    border: "border-pink-400/30",
    progress: 20,
    items: [
      { done: true, label: "PPTX sunum üretimi (MINI/MIDI/MAXI)" },
      { done: false, label: "OCR entegrasyonu" },
      { done: false, label: "Ses transkripsiyonu (Whisper)" },
      { done: false, label: "Video frame analizi" },
    ],
  },
  {
    id: "f9",
    title: "Faz 9 — Kişiselleştirme",
    icon: "�",
    status: "wip",
    color: "text-violet-400",
    border: "border-violet-400/30",
    progress: 55,
    items: [
      {
        done: true,
        label: "Teachability + Dynamic Skills + Skill Hygiene + Reflexion",
      },
      { done: true, label: "User behavior tracking" },
      { done: false, label: "Proaktif skill önerisi" },
      { done: false, label: "Adaptive tool selection" },
      { done: false, label: "Workflow auto-optimization" },
    ],
  },
  {
    id: "f10",
    title: "Faz 10 — Gerçek Zamanlı İşbirliği",
    icon: "🤝",
    status: "wip",
    color: "text-rose-400",
    border: "border-rose-400/30",
    progress: 20,
    items: [
      { done: true, label: "Otonom ajan-ajan iletişimi (OpenClaw tarzı)" },
      { done: true, label: "Post-task retrospective toplantılar" },
      { done: false, label: "Paylaşımlı çalışma alanı — ortak bağlam panosu" },
      { done: false, label: "Dinamik rol atama" },
      { done: false, label: "Canlı agent ilerleme görüntüleme" },
      { done: false, label: "Shared workspace (çoklu kullanıcı)" },
      { done: false, label: "Collaborative document editing" },
    ],
  },
  {
    id: "f11",
    title: "Faz 11 — Otonom Agent Ekosistemi",
    icon: "�",
    status: "wip",
    color: "text-orange-400",
    border: "border-orange-400/30",
    progress: 18,
    items: [
      { done: false, label: "11.1 Agentic Loop — otonom görev zincirleme" },
      { done: false, label: "11.1 Context Window Guard + Cost Governor" },
      { done: false, label: "11.2 Heartbeat — proaktif bildirim sistemi" },
      { done: false, label: "11.2 Sabah brifingleri + anomali uyarıları" },
      {
        done: true,
        label: "11.3 Self-Skill — runtime skill oluşturma (Dynamic Skills)",
      },
      { done: true, label: "11.3 Skill Markdown dosya depolama" },
      {
        done: false,
        label: "11.3 Gelişmiş pattern detection + cross-agent paylaşım",
      },
      { done: true, label: "11.4 Agent-to-agent otonom sohbet" },
      { done: true, label: "11.4 Agent kişilik bazlı iletişim" },
      { done: true, label: "11.4 Post-task retrospective toplantılar" },
      { done: false, label: "11.4 Konu bazlı topluluklar + swarm voting" },
      {
        done: false,
        label: "11.5 Multi-channel gateway (WhatsApp/Telegram/Discord)",
      },
      {
        done: false,
        label: "11.6 SOUL.md / user.md / memory.md / bootstrap.md",
      },
    ],
  },
  {
    id: "f12",
    title: "Faz 12 — Kolektif Bilinç",
    icon: "🧬",
    status: "planned",
    color: "text-fuchsia-400",
    border: "border-fuchsia-400/30",
    progress: 0,
    items: [
      { done: false, label: "Agent öz-evrim — kendi parametrelerini ayarlama" },
      { done: false, label: "Kolektif karar alma — oylama ve konsensüs" },
      { done: false, label: "Emergent davranış izleme ve loglama" },
      { done: false, label: "Agent kültür oluşumu" },
      { done: false, label: "Cross-instance iletişim" },
      { done: false, label: "Safety sandbox + kill-switch" },
      { done: false, label: "İnsan gözetimi dashboard'u" },
    ],
  },
  {
    id: "f13",
    title: "Faz 13 — Kiro IDE Entegrasyonu",
    icon: "🔮",
    status: "wip",
    color: "text-teal-400",
    border: "border-teal-400/30",
    progress: 30,
    items: [
      { done: true, label: "13.1 Custom Power: autonomous-agent-ecosystem" },
      { done: true, label: "13.1 Agentic Loop rehberi (steering)" },
      {
        done: true,
        label: "13.1 Heartbeat + Self-Skill + Identity rehberleri",
      },
      { done: true, label: "13.1 Social Network + Safety Sandbox rehberleri" },
      {
        done: false,
        label: "13.2 Kiro Skill entegrasyonları (ai-agents-architect vb.)",
      },
      {
        done: false,
        label: "13.3 Power kullanımları (api-design, performance vb.)",
      },
    ],
  },
];

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  done: {
    label: "Tamamlandı",
    cls: "bg-emerald-400/10 text-emerald-400 border-emerald-400/30",
  },
  wip: {
    label: "Devam Ediyor",
    cls: "bg-amber-400/10 text-amber-400 border-amber-400/30",
  },
  planned: {
    label: "Planlanmış",
    cls: "bg-slate-400/10 text-slate-400 border-slate-400/30",
  },
};

interface Props {
  open: boolean;
  onClose: () => void;
}

export function RoadmapDialog({ open, onClose }: Props) {
  const [expandedPhase, setExpandedPhase] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  const totalItems = PHASES.reduce((s, p) => s + p.items.length, 0);
  const doneItems = PHASES.reduce(
    (s, p) => s + p.items.filter((i) => i.done).length,
    0,
  );
  const overallProgress = Math.round((doneItems / totalItems) * 100);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Yol Haritası"
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-[94vw] max-w-3xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🗺️</span>
            <div>
              <h2 className="text-base font-bold text-slate-100">
                Yol Haritası
              </h2>
              <p className="text-[11px] text-slate-500">
                Genel İlerleme: %{overallProgress} · {doneItems}/{totalItems}{" "}
                madde tamamlandı
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-200 transition-colors text-xl leading-none p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg hover:bg-white/5"
            aria-label="Kapat"
          >
            ✕
          </button>
        </div>

        {/* Overall progress bar */}
        <div className="px-5 pt-3 pb-1">
          <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-amber-400 to-rose-500 transition-all duration-500"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-y-auto px-5 py-3 space-y-2">
          {PHASES.map((phase) => {
            const isExpanded = expandedPhase === phase.id;
            const badge = STATUS_BADGE[phase.status];
            return (
              <div
                key={phase.id}
                className={`border ${phase.border} rounded-lg overflow-hidden transition-colors ${
                  isExpanded
                    ? "bg-slate-800/60"
                    : "bg-slate-800/30 hover:bg-slate-800/50"
                }`}
              >
                <button
                  type="button"
                  onClick={() => setExpandedPhase(isExpanded ? null : phase.id)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left"
                  aria-expanded={isExpanded}
                >
                  <span className="text-lg shrink-0">{phase.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-sm font-semibold ${phase.color}`}>
                        {phase.title}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${badge.cls}`}
                      >
                        {badge.label}
                      </span>
                    </div>
                    {/* Mini progress bar */}
                    <div className="mt-1.5 flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full bg-slate-700 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            phase.status === "done"
                              ? "bg-emerald-500"
                              : phase.status === "wip"
                                ? "bg-amber-400"
                                : "bg-slate-600"
                          }`}
                          style={{ width: `${phase.progress}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-slate-500 tabular-nums w-8 text-right">
                        %{phase.progress}
                      </span>
                    </div>
                  </div>
                  <span
                    className={`text-slate-500 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                  >
                    ▾
                  </span>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-3 pt-1 space-y-1.5 border-t border-slate-700/50">
                    {phase.items.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-2 text-[12px]"
                      >
                        <span
                          className={`mt-0.5 shrink-0 ${item.done ? "text-emerald-400" : "text-slate-600"}`}
                        >
                          {item.done ? "✓" : "○"}
                        </span>
                        <span
                          className={
                            item.done ? "text-slate-400" : "text-slate-500"
                          }
                        >
                          {item.label}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 text-center text-[10px] text-slate-600">
          Son güncelleme: 2026-03-07 · Her sprint sonunda güncellenir
        </div>
      </div>
    </div>
  );
}
