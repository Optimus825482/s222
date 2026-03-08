"use client";

import { useEffect, useState } from "react";

/* ── Phase data ── */
export interface Phase {
  id: string;
  title: string;
  icon: string;
  status: "done" | "wip" | "planned";
  color: string;
  border: string;
  progress: number;
  items: { done: boolean; label: string }[];
}

export const PHASES: Phase[] = [
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
          "6 Agent (Orchestrator, Thinker, Speed, Researcher, Reasoner, Critic)",
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
      {
        done: true,
        label: "Frontend: Next.js arayüzü (XP teması, çoklu pencere)",
      },
      {
        done: true,
        label:
          "Agent İletişim Paneli (Tool Usage, Behavior, Otonom Sohbet, Toplantılar)",
      },
      { done: true, label: "Otonom İzleme paneli + Görev Merkezi canlı veri" },
      {
        done: true,
        label:
          "Başlat menüsü sağ tık (Masaüstüne Ekle / Kaldır) + Kaldırılanlar",
      },
      {
        done: true,
        label:
          "Faz 12.1 Parametre override (apply-learning, GET/DELETE param-overrides)",
      },
      {
        done: true,
        label: "Faz 12.2 Kolektif karar (policy, needs_human, resolve API)",
      },
      { done: true, label: "Roadmap dialog + Task History sağ panel" },
      { done: true, label: "Reasoning model timeout desteği (180s)" },
    ],
  },
  {
    id: "f1",
    title: "Faz 1 — Workflow Engine",
    icon: "⚡",
    status: "done",
    color: "text-emerald-400",
    border: "border-emerald-400/30",
    progress: 100,
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
      { done: true, label: "Frontend Workflow Builder UI" },
      { done: true, label: "Workflow execution history & replay" },
      { done: true, label: "Cron/zamanlı workflow tetikleme" },
    ],
  },
  {
    id: "f2",
    title: "Faz 2 — Domain Skills",
    icon: "🧠",
    status: "done",
    color: "text-purple-400",
    border: "border-purple-400/30",
    progress: 100,
    items: [
      {
        done: true,
        label:
          "Domain Skills Engine + Finans/Hukuk/Mühendislik/Akademik modülleri",
      },
      { done: true, label: "Orchestrator entegrasyonu + Backend API" },
      { done: true, label: "Domain skill auto-discovery" },
      { done: true, label: "Skill marketplace" },
    ],
  },
  {
    id: "f2_5",
    title: "Faz 2.5 — Browser Use",
    icon: "🌐",
    status: "planned",
    color: "text-sky-400",
    border: "border-sky-400/30",
    progress: 0,
    items: [
      {
        done: false,
        label: "Browser Use Engine (Playwright/Puppeteer tabanlı)",
      },
      { done: false, label: "Sayfa navigasyonu ve içerik çıkarma" },
      { done: false, label: "Form doldurma ve buton tıklama (web otomasyon)" },
      { done: false, label: "Ekran görüntüsü alma ve görsel analiz" },
      {
        done: false,
        label: "JavaScript çalıştırma (sayfa içi script execution)",
      },
      { done: false, label: "Cookie/session yönetimi (oturum bazlı tarama)" },
      { done: false, label: "Orchestrator entegrasyonu (browse_web tool)" },
      { done: false, label: "Backend API endpoints (/api/browser/*)" },
      { done: false, label: "Anti-bot koruması ve rate limiting" },
      {
        done: false,
        label: "Frontend Browser Panel UI (canlı önizleme + geçmiş)",
      },
    ],
  },
  {
    id: "f3",
    title: "Faz 3 — Veri Analizi",
    icon: "📊",
    status: "wip",
    color: "text-sky-400",
    border: "border-sky-400/30",
    progress: 17,
    items: [
      { done: false, label: "Data Analysis Engine (pandas, numpy)" },
      { done: false, label: "Otomatik istatistiksel özetleme" },
      {
        done: true,
        label:
          "Chart/grafik üretimi (matplotlib → PNG, 7 grafik tipi, dark theme)",
      },
      { done: false, label: "CSV/Excel import ve analiz" },
      { done: false, label: "Dashboard template sistemi" },
      {
        done: false,
        label: "Agent'ların veri analizi sonuçlarını görselleştirmesi",
      },
    ],
  },
  {
    id: "f4",
    title: "Faz 4 — Gelişmiş RAG",
    icon: "🔍",
    status: "planned",
    color: "text-indigo-400",
    border: "border-indigo-400/30",
    progress: 0,
    items: [
      { done: false, label: "Multi-document comparison" },
      { done: false, label: "Belge sürüm kontrolü (versioning)" },
      { done: false, label: "Cross-dataset sorgulama" },
      {
        done: false,
        label: "Bağlamsal özetleme (context-aware summarization)",
      },
      { done: false, label: "Belge güncelleme takibi (change tracking)" },
      { done: false, label: "Otomatik bilgi grafiği (knowledge graph)" },
    ],
  },
  {
    id: "f5",
    title: "Faz 5 — Güvenlik",
    icon: "🛡️",
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
    icon: "🚀",
    status: "done",
    color: "text-amber-400",
    border: "border-amber-400/30",
    progress: 100,
    items: [
      { done: true, label: "Agent başarı oranı tracking + Confidence scoring" },
      { done: true, label: "Circuit breaker" },
      { done: true, label: "Tool usage analytics dashboard" },
      { done: true, label: "User behavior tracking" },
      {
        done: true,
        label: "Performance Benchmarking Suite (8 senaryo, 5 kategori, SQLite)",
      },
      {
        done: true,
        label: "Benchmark UI paneli (Sıralama/Test/Sonuçlar/Karşılaştır)",
      },
      { done: true, label: "Benchmark backend API (7 endpoint)" },
      {
        done: true,
        label: "Hata pattern analizi (8 hata tipi, clustering, öneri motoru)",
      },
      {
        done: true,
        label: "Otomatik optimizasyon önerileri (6 analiz, 4 kategori, 7 API)",
      },
      {
        done: true,
        label: "Cost tracking (token/maliyet takibi, bütçe, tahmin, 9 API)",
      },
    ],
  },
  {
    id: "f7",
    title: "Faz 7 — API Entegrasyon",
    icon: "🔗",
    status: "wip",
    color: "text-cyan-400",
    border: "border-cyan-400/30",
    progress: 30,
    items: [
      { done: true, label: "MCP Client + Web fetch + Whoogle" },
      { done: false, label: "Webhook receiver/sender" },
      { done: false, label: "Generic REST API connector" },
      { done: false, label: "Email gönderimi (SMTP)" },
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
      { done: false, label: "OCR entegrasyonu (Tesseract/cloud)" },
      { done: false, label: "Ses transkripsiyonu (Whisper)" },
      { done: false, label: "Video frame analizi" },
      { done: false, label: "Multimodal input pipeline" },
    ],
  },
  {
    id: "f9",
    title: "Faz 9 — Kişiselleştirme",
    icon: "👤",
    status: "done",
    color: "text-emerald-400",
    border: "border-emerald-400/30",
    progress: 100,
    items: [
      {
        done: true,
        label: "Teachability + Dynamic Skills + Skill Hygiene + Reflexion",
      },
      { done: true, label: "User behavior tracking" },
      { done: true, label: "Proaktif skill önerisi" },
      {
        done: true,
        label:
          "Adaptive tool selection (4-tab: kullanım, öneriler, matris, tercihler)",
      },
      {
        done: true,
        label:
          "Workflow auto-optimization (4-tab: genel bakış, öneriler, detay, pattern kütüphanesi)",
      },
    ],
  },
  {
    id: "f10",
    title: "Faz 10 — Gerçek Zamanlı İşbirliği",
    icon: "🤝",
    status: "done",
    color: "text-emerald-400",
    border: "border-emerald-400/30",
    progress: 100,
    items: [
      { done: true, label: "Otonom ajan-ajan iletişimi (OpenClaw tarzı)" },
      { done: true, label: "Post-task retrospective toplantılar" },
      {
        done: true,
        label: "[Kiro IDE] Paylaşımlı çalışma alanı — ortak bağlam panosu",
      },
      { done: true, label: "[Kiro IDE] Dinamik rol atama" },
      { done: true, label: "[Kiro CLI] Canlı agent ilerleme görüntüleme" },
      {
        done: true,
        label: "[Kiro CLI] Shared workspace (çoklu kullanıcı — CLI sync)",
      },
      {
        done: true,
        label: "[Claude Code] Real-time collaboration (worktree bazlı)",
      },
      { done: true, label: "[Claude Code] Collaborative document editing" },
    ],
  },
  {
    id: "f11",
    title: "Faz 11 — Otonom Agent Ekosistemi",
    icon: "🦞",
    status: "wip",
    color: "text-orange-400",
    border: "border-orange-400/30",
    progress: 92,
    items: [
      { done: true, label: "11.1 Agentic Loop — otonom görev zincirleme" },
      { done: true, label: "11.1 Context Window Guard + Cost Governor" },
      { done: true, label: "11.2 Heartbeat — proaktif bildirim sistemi" },
      { done: true, label: "11.2 Sabah brifingleri + anomali uyarıları" },
      { done: true, label: "11.3 Self-Skill — runtime skill (Dynamic Skills)" },
      { done: true, label: "11.3 Skill Markdown depolama + hygiene" },
      { done: true, label: "11.3 Pattern detection + cross-agent paylaşım" },
      { done: true, label: "11.4 Agent-to-agent otonom sohbet" },
      { done: true, label: "11.4 Kişilik bazlı iletişim + retrospective" },
      { done: true, label: "11.4 Swarm oylama (proposals + vote)" },
      {
        done: false,
        label: "11.5 Multi-channel gateway (WhatsApp/Telegram/Discord)",
      },
      {
        done: true,
        label: "11.6 SOUL.md / user.md / memory.md / bootstrap.md",
      },
      { done: true, label: "11.6 Kimlik editörü UI + build_context" },
    ],
  },
  {
    id: "f12",
    title: "Faz 12 — Otonom Evrim ve Kolektif Bilinç",
    icon: "🧬",
    status: "wip",
    color: "text-fuchsia-400",
    border: "border-fuchsia-400/30",
    progress: 33,
    items: [
      {
        done: true,
        label:
          "12.1 Parametre override (temperature, max_tokens, apply-learning)",
      },
      {
        done: false,
        label: "12.1 A/B veya multi-armed bandit ile strateji keşfi",
      },
      {
        done: true,
        label:
          "12.2 Kolektif karar (policy, quorum, tie-breaker, needs_human, resolve)",
      },
      { done: true, label: "12.7 Otonom İzleme paneli + canlı aktivite" },
      {
        done: false,
        label: "12.7 Kill switch UI ve emergent behavior log görüntüleme",
      },
      { done: false, label: "12.3 Emergent davranış izleme ve loglama" },
      { done: false, label: "12.4 Agent kültür oluşumu" },
      { done: false, label: "12.5 Cross-instance iletişim" },
      { done: false, label: "12.6 Safety sandbox + kill-switch" },
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
  {
    id: "f14",
    title: "Faz 14 — pi-mono Entegrasyonu (Unified LLM Gateway & Advanced UI)",
    icon: "🔌",
    status: "done",
    color: "text-violet-400",
    border: "border-violet-400/30",
    progress: 100,
    items: [
      {
        done: true,
        label:
          "14.1 pi-ai Gateway Service (Hono microservice — services/pi-gateway/src/index.ts)",
      },
      {
        done: true,
        label:
          "14.1 OpenAI-uyumlu proxy endpoint (/v1/chat/completions — streaming + non-streaming)",
      },
      {
        done: true,
        label:
          "14.1 Provider registry (OpenAI, Anthropic, Google, Groq, Mistral, xAI, OpenRouter)",
      },
      {
        done: true,
        label: "14.1 Model auto-discovery + katalog API (GET /v1/models)",
      },
      {
        done: true,
        label: "14.1 API key yönetimi (provider başına env var)",
      },
      {
        done: true,
        label:
          "14.1 Provider fallback (otomatik yedek provider geçişi — gateway + Python dual-layer)",
      },
      {
        done: true,
        label: "14.1 Docker container + Compose entegrasyonu",
      },
      {
        done: true,
        label:
          "14.1 config.py — PI_GATEWAY_URL, PI_GATEWAY_ENABLED, GATEWAY_MODELS",
      },
      {
        done: true,
        label:
          "14.1 agents/base.py call_llm — _get_client_for_model() gateway routing",
      },
      {
        done: true,
        label:
          "14.1 Backend gateway management API (backend/routes/gateway.py — 6 endpoint)",
      },
      {
        done: true,
        label:
          "14.1 Frontend Model Manager UI (3 tab: Sağlayıcılar, Model Eşleme, Gateway Durumu)",
      },
      {
        done: true,
        label:
          "14.1 Format converter (OpenAI ↔ pi-ai bidirectional, tool_calls, thinking, SSE chunks)",
      },
      {
        done: true,
        label:
          "14.2 Granüler Streaming (SSE endpoint + call_llm_stream + WSStreamEvent)",
      },
      {
        done: true,
        label: "14.2 Frontend thinking display + tool execution animasyonu",
      },
      {
        done: true,
        label:
          "14.3 Gateway tarafında tool argument validation (AJV — validator.ts, 6 endpoint)",
      },
      {
        done: true,
        label:
          "14.3 Python tarafında validation sonuçlarını işleme (invalid args → retry with correction prompt)",
      },
      {
        done: true,
        label:
          "14.3 _parse_text_tool_calls fallback'i gateway'e taşıma (text-parser.ts)",
      },
      {
        done: true,
        label:
          "14.3 Tool schema registry — merkezi JSON Schema (gateway auto-register on startup)",
      },
      {
        done: true,
        label:
          "14.4 Frontend Model Manager UI — provider/model listesi, agent-model eşleme",
      },
      {
        done: true,
        label:
          "14.5 pi-web-ui Chat Components (React wrapper, artifacts, attachment)",
      },
      {
        done: true,
        label: "14.5 Document extraction + IndexedDB session persistence",
      },
      {
        done: true,
        label:
          "14.6 pi-agent-core Patterns (context transformer, steering, follow-up)",
      },
      {
        done: true,
        label:
          "14.6 Otomatik multi-turn tool execution + agentic_loop güncelleme",
      },
      {
        done: true,
        label:
          "14.7 Coding Agent (file tools, project understanding, session branching)",
      },
      {
        done: true,
        label: "14.7 Session compaction + skills sistemi",
      },
      {
        done: true,
        label:
          "14.8 Multi-Channel Gateway (Slack, Discord, Telegram — pi-mom pattern)",
      },
      {
        done: true,
        label: "14.8 Kanal-bağımsız mesaj normalizasyonu + Docker sandbox",
      },
    ],
  },
];
export const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
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
  const [fullScreen, setFullScreen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (fullScreen) setFullScreen(false);
        else onClose();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose, fullScreen]);

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
        className={`bg-slate-900 border border-slate-700 shadow-2xl flex flex-col transition-all ${
          fullScreen
            ? "fixed inset-2 z-[101] rounded-xl max-w-none max-h-none w-[calc(100vw-1rem)] h-[calc(100vh-1rem)]"
            : "w-[94vw] max-w-3xl max-h-[85vh] rounded-xl"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 shrink-0">
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
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setFullScreen(!fullScreen)}
              className="text-[11px] px-2.5 py-1.5 rounded-lg border border-slate-600 text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors"
              aria-label={fullScreen ? "Küçült" : "Tam ekran"}
            >
              {fullScreen ? "Küçült" : "Tam ekran"}
            </button>
            <button
              onClick={onClose}
              className="text-slate-500 hover:text-slate-200 transition-colors text-xl leading-none p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg hover:bg-white/5"
              aria-label="Kapat"
            >
              ✕
            </button>
          </div>
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
        <div className="px-5 py-3 border-t border-slate-800 text-center text-[10px] text-slate-600 shrink-0">
          Son güncelleme: 2026-03-08 · Her sprint sonunda güncellenir
        </div>
      </div>
    </div>
  );
}
