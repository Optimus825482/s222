"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAgentSocket } from "@/lib/use-agent-socket";
import { LiveEventLog } from "@/components/live-event-log";
import dynamic from "next/dynamic";
import { XpWindow, type WindowState } from "./xp-window";
import { XpTaskbar } from "./xp-taskbar";
import {
  MessageSquare,
  BarChart3,
  Settings,
  Brain,
  TrendingUp,
  Link2,
  Globe,
  Bot,
  Radio,
  Trophy,
  Bug,
  Zap,
  DollarSign,
  ScrollText,
  FolderOpen,
  Users,
  History,
  Wrench,
  Trash2,
  Loader2,
  Search,
  XCircle,
  Info,
  Map,
  Package,
} from "lucide-react";
import { SystemGuideDialog } from "./system-guide-dialog";
import { RoadmapDialog } from "./roadmap-dialog";
import { useXpSounds } from "@/lib/use-xp-sounds";
import { AGENT_CONFIG } from "@/lib/agents";
import type { AgentRole } from "@/lib/types";
import { api } from "@/lib/api";
import type { ThreadSummary } from "@/lib/types";

// ── Lazy-loaded panel components (same as page.tsx) ──
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore dynamic runtime import
const ChatDesktopPanel = dynamic(() => import("./xp-chat-panel"), {
  ssr: false,
});
const TaskFlowMonitor = dynamic(
  () =>
    import("@/components/task-flow-monitor").then((m) => ({
      default: m.TaskFlowMonitor,
    })),
  { ssr: false },
);
const SystemStatsPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.SystemStatsPanel,
    })),
  { ssr: false },
);
const AgentHealthPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.AgentHealthPanel,
    })),
  { ssr: false },
);
const AnomalyPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.AnomalyPanel,
    })),
  { ssr: false },
);
const LeaderboardPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.LeaderboardPanel,
    })),
  { ssr: false },
);
const MemoryTimelinePanel = dynamic(
  () =>
    import("@/components/memory-panels").then((m) => ({
      default: m.MemoryTimelinePanel,
    })),
  { ssr: false },
);
const MemoryCorrelationPanel = dynamic(
  () =>
    import("@/components/memory-panels").then((m) => ({
      default: m.MemoryCorrelationPanel,
    })),
  { ssr: false },
);
const AgentEvolutionPanel = dynamic(
  () =>
    import("@/components/agent-evolution-panel").then((m) => ({
      default: m.AgentEvolutionPanel,
    })),
  { ssr: false },
);
const CoordinationPanel = dynamic(
  () =>
    import("@/components/coordination-panel").then((m) => ({
      default: m.CoordinationPanel,
    })),
  { ssr: false },
);
const AgentEcosystemMap = dynamic(
  () =>
    import("@/components/agent-ecosystem-map").then((m) => ({
      default: m.AgentEcosystemMap,
    })),
  { ssr: false },
);
const AutonomousEvolutionPanel = dynamic(
  () =>
    import("@/components/autonomous-evolution-panel").then((m) => ({
      default: m.AutonomousEvolutionPanel,
    })),
  { ssr: false },
);
const AgentCommsPanel = dynamic(
  () =>
    import("@/components/agent-comms-panel").then((m) => ({
      default: m.AgentCommsPanel,
    })),
  { ssr: false },
);
const BenchmarkPanel = dynamic(
  () =>
    import("@/components/benchmark-panel").then((m) => ({
      default: m.BenchmarkPanel,
    })),
  { ssr: false },
);
const ErrorPatternsPanel = dynamic(
  () => import("@/components/error-patterns-panel"),
  { ssr: false },
);
const CostTrackerPanel = dynamic(
  () => import("@/components/cost-tracker-panel"),
  { ssr: false },
);
const AutoOptimizerPanel = dynamic(
  () => import("@/components/auto-optimizer-panel"),
  { ssr: false },
);
const XpReportsPanel = dynamic(
  () =>
    import("@/components/xp-reports-panel").then((m) => ({
      default: m.XpReportsPanel,
    })),
  { ssr: false },
);
const XpSearchPanel = dynamic(
  () =>
    import("@/components/xp-search-panel").then((m) => ({
      default: m.XpSearchPanel,
    })),
  { ssr: false },
);
const RagPanel = dynamic(
  () =>
    import("@/components/tools-panels").then((m) => ({
      default: m.RagPanel,
    })),
  { ssr: false },
);
const SkillsPanel = dynamic(
  () =>
    import("@/components/tools-panels").then((m) => ({
      default: m.SkillsPanel,
    })),
  { ssr: false },
);
const McpPanel = dynamic(
  () =>
    import("@/components/tools-panels").then((m) => ({
      default: m.McpPanel,
    })),
  { ssr: false },
);
const TeachabilityPanel = dynamic(
  () =>
    import("@/components/tools-panels").then((m) => ({
      default: m.TeachabilityPanel,
    })),
  { ssr: false },
);
const EvalPanel = dynamic(
  () =>
    import("@/components/tools-panels").then((m) => ({
      default: m.EvalPanel,
    })),
  { ssr: false },
);
const XpMarketplacePanel = dynamic(
  () =>
    import("@/components/xp-marketplace-panel").then((m) => ({
      default: m.XpMarketplacePanel,
    })),
  { ssr: false },
);

// ── App definitions ──
interface DesktopApp {
  id: string;
  title: string;
  icon: React.ReactNode;
  color: string;
  group: string;
  description: string;
  defaultW: number;
  defaultH: number;
  render: () => React.ReactNode;
}

const APPS: DesktopApp[] = [
  {
    id: "chat",
    title: "Sohbet",
    icon: <MessageSquare className="w-8 h-8" />,
    color: "#3b82f6",
    group: "Ana",
    description:
      "Agent'larla sohbet edin, görev gönderin. Orchestrator mesajınızı analiz edip uygun specialist agent'lara yönlendirir. Metin, kod analizi, araştırma gibi her türlü görevi destekler.",
    defaultW: 700,
    defaultH: 500,
    render: () => <ChatDesktopPanel />,
  },
  {
    id: "monitor",
    title: "Görev Merkezi",
    icon: <BarChart3 className="w-8 h-8" />,
    color: "#8b5cf6",
    group: "Ana",
    description:
      "Aktif görevlerin gerçek zamanlı akış diyagramını görüntüleyin. Hangi agent'ın ne yaptığını, görev durumlarını ve alt görev ağacını takip edin.",
    defaultW: 800,
    defaultH: 500,
    render: () => (
      <div className="p-4">
        <TaskFlowMonitor thread={null} liveEvents={[]} />
      </div>
    ),
  },
  {
    id: "insights",
    title: "Sistem Durumu",
    icon: <Settings className="w-8 h-8" />,
    color: "#6b7280",
    group: "Ana",
    description:
      "Sistem istatistikleri, agent sağlık durumu, anomali tespiti ve liderlik tablosu. CPU, bellek, aktif bağlantı sayısı gibi metrikleri gerçek zamanlı izleyin.",
    defaultW: 650,
    defaultH: 550,
    render: () => (
      <div className="p-4 space-y-4 overflow-auto h-full">
        <SystemStatsPanel />
        <AgentHealthPanel />
        <AnomalyPanel />
        <LeaderboardPanel />
      </div>
    ),
  },
  {
    id: "memory",
    title: "Bellek",
    icon: <Brain className="w-8 h-8" />,
    color: "#ec4899",
    group: "Ana",
    description:
      "Agent bellek zaman çizelgesi ve korelasyon analizi. Agent'ların öğrendiği bilgileri, hafıza kayıtlarını ve bilgi bağlantılarını görselleştirin.",
    defaultW: 600,
    defaultH: 500,
    render: () => (
      <div className="p-4 space-y-4 overflow-auto h-full">
        <MemoryTimelinePanel />
        <MemoryCorrelationPanel />
      </div>
    ),
  },
  {
    id: "livelog",
    title: "Canlı Log",
    icon: <ScrollText className="w-8 h-8" />,
    color: "#22d3ee",
    group: "Ana",
    description:
      "WebSocket üzerinden gerçek zamanlı olay akışı. Görev gönderildiğinde agent'ların her adımını, düşünce süreçlerini ve sonuçlarını canlı izleyin.",
    defaultW: 700,
    defaultH: 400,
    render: () => <XpLiveLogPanel />,
  },
  {
    id: "evolution",
    title: "Gelişim",
    icon: <TrendingUp className="w-8 h-8" />,
    color: "#10b981",
    group: "Agent",
    description:
      "Agent'ların zaman içindeki performans gelişimini takip edin. Başarı oranları, yanıt süreleri ve kalite metriklerinin trend grafiklerini görüntüleyin.",
    defaultW: 650,
    defaultH: 480,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <AgentEvolutionPanel />
      </div>
    ),
  },
  {
    id: "coordination",
    title: "Koordinasyon",
    icon: <Link2 className="w-8 h-8" />,
    color: "#f59e0b",
    group: "Agent",
    description:
      "Agent'lar arası koordinasyon ve iş birliği haritası. Hangi agent'ların birlikte çalıştığını, görev dağılımını ve iletişim akışını görselleştirin.",
    defaultW: 650,
    defaultH: 480,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <CoordinationPanel />
      </div>
    ),
  },
  {
    id: "ecosystem",
    title: "Ekosistem",
    icon: <Globe className="w-8 h-8" />,
    color: "#06b6d4",
    group: "Agent",
    description:
      "Tüm agent ekosisteminin interaktif haritası. Agent'ların rollerini, bağlantılarını ve sistem içindeki konumlarını ağ grafiği olarak keşfedin.",
    defaultW: 700,
    defaultH: 500,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <AgentEcosystemMap />
      </div>
    ),
  },
  {
    id: "autonomous",
    title: "Özerk Evrim",
    icon: <Bot className="w-8 h-8" />,
    color: "#a78bfa",
    group: "Agent",
    description:
      "Agent'ların özerk öğrenme ve evrim süreçlerini izleyin. Kendi kendine öğrenen agent'ların adaptasyon stratejilerini ve performans iyileştirmelerini takip edin.",
    defaultW: 650,
    defaultH: 480,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <AutonomousEvolutionPanel />
      </div>
    ),
  },
  {
    id: "comms",
    title: "İletişim",
    icon: <Radio className="w-8 h-8" />,
    color: "#f43f5e",
    group: "Agent",
    description:
      "Agent'lar arası mesajlaşma ve iletişim kanalları. Gerçek zamanlı mesaj trafiğini, iletişim protokollerini ve agent diyaloglarını izleyin.",
    defaultW: 600,
    defaultH: 500,
    render: () => (
      <div className="overflow-hidden h-full">
        <AgentCommsPanel />
      </div>
    ),
  },
  {
    id: "benchmark",
    title: "Benchmark",
    icon: <Trophy className="w-8 h-8" />,
    color: "#eab308",
    group: "Analitik",
    description:
      "Agent performans kıyaslama testleri. Farklı agent'ların ve pipeline'ların hız, doğruluk ve maliyet metriklerini karşılaştırın.",
    defaultW: 650,
    defaultH: 480,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <BenchmarkPanel />
      </div>
    ),
  },
  {
    id: "errors",
    title: "Hata Analizi",
    icon: <Bug className="w-8 h-8" />,
    color: "#ef4444",
    group: "Analitik",
    description:
      "Hata örüntülerini tespit edin ve analiz edin. Tekrarlayan hataları, kök nedenleri ve çözüm önerilerini görüntüleyin.",
    defaultW: 650,
    defaultH: 480,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <ErrorPatternsPanel />
      </div>
    ),
  },
  {
    id: "search",
    title: "Arama",
    icon: <Search className="w-8 h-8" />,
    color: "#06b6d4",
    group: "Analitik",
    description:
      "Tüm oturumlar, görevler ve agent yanıtları içinde arama yapın. Geçmiş konuşmaları ve sonuçları hızlıca bulun.",
    defaultW: 550,
    defaultH: 500,
    render: () => (
      <div className="overflow-hidden h-full">
        <XpSearchPanel />
      </div>
    ),
  },
  {
    id: "optimizer",
    title: "Optimizer",
    icon: <Zap className="w-8 h-8" />,
    color: "#f97316",
    group: "Analitik",
    description:
      "Otomatik optimizasyon motoru. Agent yapılandırmalarını, prompt'ları ve pipeline ayarlarını otomatik olarak iyileştirin.",
    defaultW: 650,
    defaultH: 480,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <AutoOptimizerPanel />
      </div>
    ),
  },
  {
    id: "costs",
    title: "Maliyet",
    icon: <DollarSign className="w-8 h-8" />,
    color: "#84cc16",
    group: "Analitik",
    description:
      "API kullanım maliyetlerini takip edin. Model bazlı harcamalar, token kullanımı ve bütçe uyarılarını görüntüleyin.",
    defaultW: 650,
    defaultH: 480,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <CostTrackerPanel />
      </div>
    ),
  },
  {
    id: "reports",
    title: "Raporlar",
    icon: <FolderOpen className="w-8 h-8" />,
    color: "#f59e0b",
    group: "Ana",
    description:
      "Oluşturulan raporları ve proje dosyalarını görüntüleyin. PRD, mimari, analiz ve scaffold raporlarına klasör yapısıyla erişin.",
    defaultW: 750,
    defaultH: 500,
    render: () => (
      <div className="overflow-hidden h-full">
        <XpReportsPanel />
      </div>
    ),
  },
  {
    id: "agents",
    title: "Agentlar",
    icon: <Users className="w-8 h-8" />,
    color: "#ec4899",
    group: "Sistem",
    description:
      "Tüm agent'ların listesi ve durumları. Her agent'ın rolünü, rengini ve mevcut durumunu (idle/active) görüntüleyin.",
    defaultW: 400,
    defaultH: 480,
    render: () => <XpAgentsPanel />,
  },
  {
    id: "sessions",
    title: "Oturumlar",
    icon: <History className="w-8 h-8" />,
    color: "#3b82f6",
    group: "Sistem",
    description:
      "Geçmiş sohbet oturumlarını listeleyin. Oturum geçmişini inceleyin, eski görevlere göz atın veya oturumları silin.",
    defaultW: 420,
    defaultH: 500,
    render: () => <XpSessionsPanel />,
  },
  {
    id: "tools",
    title: "Araçlar",
    icon: <Wrench className="w-8 h-8" />,
    color: "#8b5cf6",
    group: "Sistem",
    description:
      "RAG, Skills, MCP, Teachability ve Eval araçlarını yönetin. Bilgi tabanı, öğretilebilirlik ve değerlendirme modüllerine erişin.",
    defaultW: 450,
    defaultH: 550,
    render: () => <XpToolsPanel />,
  },
  {
    id: "roadmap",
    title: "Yol Haritası",
    icon: <Map className="w-8 h-8" />,
    color: "#14b8a6",
    group: "Sistem",
    description:
      "Geliştirme yol haritasını görüntüleyin. Tüm fazların ilerleme durumunu, tamamlanan ve planlanan özellikleri takip edin. Proje vizyonunu ve gelecek planlarını keşfedin.",
    defaultW: 700,
    defaultH: 550,
    render: () => <XpRoadmapPanel />,
  },
  {
    id: "marketplace",
    title: "Skill Marketplace",
    icon: <Package className="w-8 h-8" />,
    color: "#8b5cf6",
    group: "Araçlar",
    description:
      "Domain modüllerini ve becerileri keşfedin. Finans, Hukuk, Mühendislik, Akademik domain araçlarını görüntüleyin. Otomatik domain tespiti ile sorgunuza uygun araçları bulun.",
    defaultW: 750,
    defaultH: 550,
    render: () => <XpMarketplacePanel />,
  },
];

function XpLiveLogPanel() {
  const { status, liveEvents, reconnect } = useAgentSocket({ enabled: true });

  // Determine connection state for display
  const isConnected =
    status === "idle" || status === "running" || status === "complete";
  const isActive = status === "running";
  const hasEvents = liveEvents.length > 0;

  return (
    <div className="flex flex-col h-full min-h-0 bg-[#0a0e1a] text-slate-200">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700/50">
        <ScrollText className="w-4 h-4 text-cyan-400" />
        <span className="text-xs font-medium text-slate-300">
          Canlı Olay Akışı
        </span>
        <span
          className={`ml-auto text-[10px] px-1.5 py-0.5 rounded-full ${
            isActive
              ? "bg-green-500/20 text-green-400"
              : status === "connecting"
                ? "bg-yellow-500/20 text-yellow-400"
                : status === "error"
                  ? "bg-red-500/20 text-red-400"
                  : isConnected
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-slate-500/20 text-slate-400"
          }`}
        >
          {isActive
            ? "Aktif"
            : status === "connecting"
              ? "Bağlanıyor"
              : status === "error"
                ? "Hata"
                : status === "complete"
                  ? "Tamamlandı"
                  : isConnected
                    ? "Bağlı"
                    : "Bekleniyor"}
        </span>
      </div>
      <div className="flex-1 min-h-0 overflow-auto">
        {hasEvents ? (
          <LiveEventLog events={liveEvents} status={status} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500 px-6">
            {status === "error" ? (
              <>
                <XCircle className="w-8 h-8 text-red-400/60" />
                <p className="text-xs text-center text-red-400/80">
                  WebSocket bağlantısı kurulamadı
                </p>
                <p className="text-[10px] text-center text-slate-600">
                  Backend&apos;in çalıştığından emin olun (port 8001)
                </p>
                <button
                  onClick={reconnect}
                  className="mt-1 text-[10px] px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 transition-colors"
                >
                  Yeniden Bağlan
                </button>
              </>
            ) : isConnected ? (
              <>
                <Radio className="w-8 h-8 text-emerald-400/40" />
                <p className="text-xs text-center">
                  WebSocket bağlı — görev bekleniyor
                </p>
                <p className="text-[10px] text-center text-slate-600">
                  Sohbet panelinden bir görev gönderin, olaylar burada görünecek
                </p>
              </>
            ) : (
              <>
                <Loader2 className="w-6 h-6 animate-spin text-yellow-400/60" />
                <p className="text-xs text-center">Bağlanıyor...</p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Agents Panel (sidebar Agentlar tab equivalent) ──

function XpAgentsPanel() {
  return (
    <div className="flex flex-col h-full bg-[#0a0e1a] text-slate-200">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700/50">
        <Users className="w-4 h-4 text-pink-400" />
        <span className="text-xs font-medium text-slate-300">
          Agent Durumları
        </span>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {(
          Object.entries(AGENT_CONFIG) as [
            AgentRole,
            (typeof AGENT_CONFIG)[AgentRole],
          ][]
        ).map(([role, cfg]) => (
          <div
            key={role}
            className="rounded-lg bg-slate-800/60 p-3 border-l-2"
            style={{ borderColor: cfg.color }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">{cfg.icon}</span>
                <span
                  className="text-xs font-semibold"
                  style={{ color: cfg.color }}
                >
                  {cfg.name}
                </span>
              </div>
              <span className="text-[10px] text-slate-500">idle</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-1 capitalize">
              {role}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Sessions Panel (sidebar Oturumlar tab equivalent) ──

function XpSessionsPanel() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listThreads(50);
      setThreads(list);
    } catch (err) {
      console.error("[XpSessions] load error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: string) => {
    try {
      await api.deleteThread(id);
      setThreads((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      console.error("[XpSessions] delete error:", err);
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm("Tüm oturumlar silinsin mi?")) return;
    try {
      await api.deleteAllThreads();
      setThreads([]);
    } catch (err) {
      console.error("[XpSessions] deleteAll error:", err);
    }
  };

  const fmtDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("tr-TR", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0e1a] text-slate-200">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700/50">
        <History className="w-4 h-4 text-blue-400" />
        <span className="text-xs font-medium text-slate-300">Oturumlar</span>
        {loading && (
          <Loader2 className="w-3 h-3 animate-spin text-blue-400 ml-auto" />
        )}
        {!loading && threads.length > 0 && (
          <button
            onClick={handleDeleteAll}
            className="ml-auto text-[10px] text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-500/10 transition-colors"
          >
            Tümünü Sil
          </button>
        )}
      </div>
      <div className="flex-1 overflow-auto divide-y divide-slate-700/30">
        {threads.length === 0 && !loading && (
          <div className="p-6 text-center text-sm text-slate-500">
            Kayıtlı oturum yok
          </div>
        )}
        {threads.map((t) => (
          <div
            key={t.id}
            className="flex items-start gap-2 p-3 hover:bg-slate-800/40 transition-colors group"
          >
            <div className="flex-1 min-w-0">
              <div className="text-xs text-slate-300 truncate">
                {t.preview || t.id.slice(0, 12)}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {fmtDate(t.created_at)} · {t.task_count} görev · {t.event_count}{" "}
                olay
              </div>
            </div>
            <button
              onClick={() => handleDelete(t.id)}
              className="opacity-0 group-hover:opacity-100 p-1 text-red-400 hover:text-red-300 transition-all"
              aria-label="Oturumu sil"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Tools Panel (sidebar Araçlar tab equivalent) ──

function XpToolsPanel() {
  return (
    <div className="flex flex-col h-full bg-[#0a0e1a] text-slate-200">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700/50">
        <Wrench className="w-4 h-4 text-purple-400" />
        <span className="text-xs font-medium text-slate-300">Araçlar</span>
      </div>
      <div className="flex-1 overflow-auto space-y-4 p-1">
        <RagPanel />
        <hr className="border-slate-700/40 mx-3" />
        <SkillsPanel />
        <hr className="border-slate-700/40 mx-3" />
        <McpPanel />
        <hr className="border-slate-700/40 mx-3" />
        <TeachabilityPanel />
        <hr className="border-slate-700/40 mx-3" />
        <EvalPanel />
      </div>
    </div>
  );
}

// ── Roadmap Panel (embedded roadmap inside XP window) ──

function XpRoadmapPanel() {
  const [showDialog, setShowDialog] = useState(false);
  return (
    <>
      <div className="flex flex-col h-full bg-[#0a0e1a] text-slate-200">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700/50">
          <Map className="w-4 h-4 text-teal-400" />
          <span className="text-xs font-medium text-slate-300">
            Geliştirme Yol Haritası
          </span>
          <button
            onClick={() => setShowDialog(true)}
            className="ml-auto text-[10px] px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20 hover:bg-teal-500/20 transition-colors"
          >
            Tam Ekran
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-auto p-3">
          <RoadmapDialog
            open={showDialog}
            onClose={() => setShowDialog(false)}
          />
          <EmbeddedRoadmap />
        </div>
      </div>
    </>
  );
}

function EmbeddedRoadmap() {
  const phases = [
    {
      title: "Mevcut Durum (v2.0)",
      icon: "✅",
      status: "done" as const,
      progress: 100,
      color: "text-emerald-400",
      bar: "bg-emerald-500",
    },
    {
      title: "Faz 1 — Workflow Engine",
      icon: "⚡",
      status: "wip" as const,
      progress: 73,
      color: "text-amber-400",
      bar: "bg-amber-400",
    },
    {
      title: "Faz 2 — Domain Skills",
      icon: "🧠",
      status: "wip" as const,
      progress: 70,
      color: "text-purple-400",
      bar: "bg-purple-400",
    },
    {
      title: "Faz 2.5 — Browser Use",
      icon: "🌐",
      status: "planned" as const,
      progress: 0,
      color: "text-lime-400",
      bar: "bg-lime-500",
    },
    {
      title: "Faz 3 — Veri Analizi",
      icon: "📊",
      status: "planned" as const,
      progress: 0,
      color: "text-sky-400",
      bar: "bg-sky-500",
    },
    {
      title: "Faz 4 — Gelişmiş RAG",
      icon: "📚",
      status: "planned" as const,
      progress: 0,
      color: "text-indigo-400",
      bar: "bg-indigo-500",
    },
    {
      title: "Faz 5 — Güvenlik",
      icon: "🛡️",
      status: "wip" as const,
      progress: 20,
      color: "text-red-400",
      bar: "bg-red-400",
    },
    {
      title: "Faz 6 — Performans",
      icon: "🚀",
      status: "done" as const,
      progress: 100,
      color: "text-amber-400",
      bar: "bg-emerald-500",
    },
    {
      title: "Faz 7 — API Entegrasyon",
      icon: "🔌",
      status: "wip" as const,
      progress: 30,
      color: "text-cyan-400",
      bar: "bg-cyan-400",
    },
    {
      title: "Faz 8 — Multimedya",
      icon: "🎨",
      status: "wip" as const,
      progress: 20,
      color: "text-pink-400",
      bar: "bg-pink-400",
    },
    {
      title: "Faz 9 — Kişiselleştirme",
      icon: "👤",
      status: "wip" as const,
      progress: 55,
      color: "text-violet-400",
      bar: "bg-violet-400",
    },
    {
      title: "Faz 10 — Gerçek Zamanlı İşbirliği",
      icon: "🤝",
      status: "wip" as const,
      progress: 20,
      color: "text-rose-400",
      bar: "bg-rose-400",
    },
    {
      title: "Faz 11 — Otonom Ekosistem",
      icon: "🌐",
      status: "wip" as const,
      progress: 50,
      color: "text-orange-400",
      bar: "bg-orange-400",
    },
    {
      title: "Faz 12 — Kolektif Bilinç",
      icon: "🧬",
      status: "planned" as const,
      progress: 0,
      color: "text-fuchsia-400",
      bar: "bg-fuchsia-500",
    },
    {
      title: "Faz 13 — Kiro IDE",
      icon: "🔮",
      status: "wip" as const,
      progress: 30,
      color: "text-teal-400",
      bar: "bg-teal-400",
    },
  ];

  const statusLabel = {
    done: "Tamamlandı",
    wip: "Devam Ediyor",
    planned: "Planlanmış",
  };
  const statusCls = {
    done: "bg-emerald-400/10 text-emerald-400",
    wip: "bg-amber-400/10 text-amber-400",
    planned: "bg-slate-400/10 text-slate-400",
  };

  const totalProgress = Math.round(
    phases.reduce((s, p) => s + p.progress, 0) / phases.length,
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 mb-2">
        <div className="flex-1">
          <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-amber-400 to-rose-500 transition-all"
              style={{ width: `${totalProgress}%` }}
            />
          </div>
        </div>
        <span className="text-[11px] text-slate-400 tabular-nums shrink-0">
          %{totalProgress}
        </span>
      </div>
      {phases.map((p, i) => (
        <div
          key={i}
          className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg bg-slate-800/40 hover:bg-slate-800/60 transition-colors"
        >
          <span className="text-base shrink-0">{p.icon}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`text-[11px] font-semibold truncate ${p.color}`}>
                {p.title}
              </span>
              <span
                className={`text-[9px] px-1.5 py-0.5 rounded-full shrink-0 ${statusCls[p.status]}`}
              >
                {statusLabel[p.status]}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-2">
              <div className="flex-1 h-1 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className={`h-full rounded-full ${p.bar} transition-all`}
                  style={{ width: `${p.progress}%` }}
                />
              </div>
              <span className="text-[9px] text-slate-500 tabular-nums w-6 text-right">
                %{p.progress}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

let _nextZ = 100;
function nextZ() {
  return ++_nextZ;
}

function cascade(index: number) {
  const offset = (index % 8) * 30;
  return { x: 60 + offset, y: 40 + offset };
}

export function XpDesktop() {
  const { play } = useXpSounds();
  const [windows, setWindows] = useState<WindowState[]>([]);
  const [showGuide, setShowGuide] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null);
  const [iconCtxMenu, setIconCtxMenu] = useState<{
    x: number;
    y: number;
    appId: string;
  } | null>(null);
  const [propsDialog, setPropsDialog] = useState<string | null>(null);
  const [iconPositions, setIconPositions] = useState<
    Record<string, { x: number; y: number }>
  >({});
  const dragIcon = useRef<{
    id: string;
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  } | null>(null);
  const [isDraggingIcon, setIsDraggingIcon] = useState(false);
  const desktopRef = useRef<HTMLDivElement>(null);

  // Initialize icon positions in a grid layout
  useEffect(() => {
    const stored = localStorage.getItem("xp-icon-positions");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // Validate that all current apps have positions
        const hasAll = APPS.every((a) => parsed[a.id]);
        if (hasAll) {
          setIconPositions(parsed);
          return;
        }
      } catch {
        /* ignore */
      }
    }
    // Default grid layout — responsive for mobile
    const isMobile = window.innerWidth < 768;
    const gap = isMobile ? 80 : 96;
    const rowH = isMobile ? 84 : 100;
    const cols = Math.floor((window.innerHeight - 80) / rowH);
    const positions: Record<string, { x: number; y: number }> = {};
    APPS.forEach((app, i) => {
      const col = Math.floor(i / cols);
      const row = i % cols;
      positions[app.id] = { x: 8 + col * gap, y: 8 + row * rowH };
    });
    setIconPositions(positions);
  }, []);

  // Save positions to localStorage when they change
  useEffect(() => {
    if (Object.keys(iconPositions).length > 0) {
      localStorage.setItem("xp-icon-positions", JSON.stringify(iconPositions));
    }
  }, [iconPositions]);

  // Play startup sound once on first mount
  useEffect(() => {
    const t = setTimeout(() => play("startup"), 500);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Icon drag handlers
  const handleIconDragStart = useCallback(
    (e: React.MouseEvent, appId: string) => {
      e.preventDefault();
      const pos = iconPositions[appId];
      if (!pos) return;
      dragIcon.current = {
        id: appId,
        startX: e.clientX,
        startY: e.clientY,
        origX: pos.x,
        origY: pos.y,
      };
      setIsDraggingIcon(true);
    },
    [iconPositions],
  );

  useEffect(() => {
    if (!isDraggingIcon) return;
    const handleMove = (e: MouseEvent) => {
      if (!dragIcon.current) return;
      const dx = e.clientX - dragIcon.current.startX;
      const dy = e.clientY - dragIcon.current.startY;
      setIconPositions((prev) => ({
        ...prev,
        [dragIcon.current!.id]: {
          x: Math.max(0, dragIcon.current!.origX + dx),
          y: Math.max(0, dragIcon.current!.origY + dy),
        },
      }));
    };
    const handleUp = () => {
      dragIcon.current = null;
      setIsDraggingIcon(false);
    };
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, [isDraggingIcon]);

  const openApp = useCallback((appId: string) => {
    // Special: "help" opens SystemGuideDialog instead of a window
    if (appId === "help") {
      setShowGuide(true);
      return;
    }
    setWindows((prev) => {
      const existing = prev.find((w) => w.id === appId);
      if (existing) {
        return prev.map((w) =>
          w.id === appId ? { ...w, minimized: false, zIndex: nextZ() } : w,
        );
      }
      const app = APPS.find((a) => a.id === appId);
      if (!app) return prev;
      const pos = cascade(prev.length);
      const isMobile = window.innerWidth < 768;
      const newWin: WindowState = {
        id: app.id,
        title: app.title,
        icon: app.icon,
        x: isMobile ? 0 : pos.x,
        y: isMobile ? 0 : pos.y,
        w: isMobile ? window.innerWidth : app.defaultW,
        h: isMobile ? window.innerHeight - 36 : app.defaultH,
        minimized: false,
        maximized: isMobile,
        zIndex: nextZ(),
      };
      return [...prev, newWin];
    });
  }, []);

  const closeWindow = useCallback((id: string) => {
    setWindows((prev) => prev.filter((w) => w.id !== id));
  }, []);

  const minimizeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, minimized: true } : w)),
    );
  }, []);

  const maximizeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) =>
        w.id === id ? { ...w, maximized: !w.maximized, zIndex: nextZ() } : w,
      ),
    );
  }, []);

  const focusWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, zIndex: nextZ() } : w)),
    );
  }, []);

  const moveWindow = useCallback((id: string, x: number, y: number) => {
    setWindows((prev) => prev.map((w) => (w.id === id ? { ...w, x, y } : w)));
  }, []);

  const resizeWindow = useCallback((id: string, w: number, h: number) => {
    setWindows((prev) =>
      prev.map((win) => (win.id === id ? { ...win, w, h } : win)),
    );
  }, []);

  // ── Desktop right-click context menu ──
  const handleDesktopContext = useCallback((e: React.MouseEvent) => {
    // Only show on the wallpaper itself, not on icons/windows
    if ((e.target as HTMLElement).closest(".xp-desktop-icon, .xp-window"))
      return;
    e.preventDefault();
    setCtxMenu({ x: e.clientX, y: e.clientY });
  }, []);

  // Dismiss context menus on click outside
  useEffect(() => {
    if (!ctxMenu && !iconCtxMenu) return;
    const dismiss = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest(".xp-ctx-menu")) return;
      setCtxMenu(null);
      setIconCtxMenu(null);
    };
    window.addEventListener("pointerdown", dismiss);
    return () => window.removeEventListener("pointerdown", dismiss);
  }, [ctxMenu, iconCtxMenu]);

  const handleTaskbarClick = useCallback((id: string) => {
    setWindows((prev) => {
      const win = prev.find((w) => w.id === id);
      if (!win) return prev;
      if (win.minimized) {
        return prev.map((w) =>
          w.id === id ? { ...w, minimized: false, zIndex: nextZ() } : w,
        );
      }
      const maxZ = Math.max(...prev.map((w) => w.zIndex));
      if (win.zIndex === maxZ) {
        return prev.map((w) => (w.id === id ? { ...w, minimized: true } : w));
      }
      return prev.map((w) => (w.id === id ? { ...w, zIndex: nextZ() } : w));
    });
  }, []);

  const taskbarApps = APPS.map((a) => ({
    id: a.id,
    title: a.title,
    icon: a.icon,
    group: a.group,
  }));

  return (
    <div className="xp-desktop-root flex flex-col h-dvh overflow-hidden select-none">
      {/* Desktop Area */}
      <div
        ref={desktopRef}
        className="flex-1 relative overflow-hidden xp-wallpaper"
        onContextMenu={handleDesktopContext}
      >
        {/* Desktop Icons — absolutely positioned, draggable */}
        {APPS.map((app) => {
          const pos = iconPositions[app.id];
          if (!pos) return null;
          return (
            <button
              key={app.id}
              onMouseDown={(e) => {
                // Skip drag on touch devices
                if (window.innerWidth >= 768) handleIconDragStart(e, app.id);
              }}
              onClick={() => {
                // Single tap opens on mobile
                if (window.innerWidth < 768) openApp(app.id);
              }}
              onDoubleClick={() => openApp(app.id)}
              onContextMenu={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIconCtxMenu({ x: e.clientX, y: e.clientY, appId: app.id });
                setCtxMenu(null);
              }}
              className="xp-desktop-icon absolute flex flex-col items-center gap-1 sm:gap-1.5 w-[68px] sm:w-[80px] p-1.5 sm:p-2 rounded hover:bg-white/10 active:bg-white/20 transition-colors group z-10"
              style={{ left: pos.x, top: pos.y }}
              title={`${app.title} — çift tıkla`}
            >
              <span
                className="w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center drop-shadow-[0_2px_6px_rgba(0,0,0,0.6)] group-hover:scale-110 transition-transform"
                style={{ color: app.color }}
              >
                {app.icon}
              </span>
              <span className="text-[10px] sm:text-[11px] text-white text-center leading-tight drop-shadow-[0_1px_3px_rgba(0,0,0,0.8)] line-clamp-2 font-medium">
                {app.title}
              </span>
            </button>
          );
        })}

        {/* Windows */}
        {windows.map((win) => {
          const app = APPS.find((a) => a.id === win.id);
          if (!app) return null;
          return (
            <XpWindow
              key={win.id}
              state={win}
              onClose={closeWindow}
              onMinimize={minimizeWindow}
              onMaximize={maximizeWindow}
              onFocus={focusWindow}
              onMove={moveWindow}
              onResize={resizeWindow}
            >
              {app.render()}
            </XpWindow>
          );
        })}

        {/* Right-click Context Menu */}
        {ctxMenu && (
          <div
            className="xp-ctx-menu fixed z-[200] bg-white rounded shadow-[2px_2px_8px_rgba(0,0,0,0.3)] border border-gray-300 py-1 min-w-[180px] max-w-[90vw] text-[12px] text-gray-800"
            style={{
              left: Math.min(ctxMenu.x, window.innerWidth - 200),
              top: Math.min(ctxMenu.y, window.innerHeight - 250),
            }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => {
                setCtxMenu(null);
                openApp("chat");
              }}
              className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Yeni Görev
            </button>
            <button
              onClick={() => {
                setCtxMenu(null);
                openApp("reports");
              }}
              className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
            >
              <FolderOpen className="w-3.5 h-3.5" />
              Raporlar
            </button>
            <button
              onClick={() => {
                setCtxMenu(null);
                openApp("search");
              }}
              className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
            >
              <Search className="w-3.5 h-3.5" />
              Arama
            </button>
            <div className="border-t border-gray-200 my-1" />
            <button
              onClick={() => {
                setCtxMenu(null);
                openApp("insights");
              }}
              className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
            >
              <Settings className="w-3.5 h-3.5" />
              Sistem Durumu
            </button>
            <button
              onClick={() => {
                setCtxMenu(null);
                openApp("agents");
              }}
              className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
            >
              <Users className="w-3.5 h-3.5" />
              Agentlar
            </button>
            <div className="border-t border-gray-200 my-1" />
            <button
              onClick={() => {
                setCtxMenu(null);
                const isMobile = window.innerWidth < 768;
                const gap = isMobile ? 80 : 96;
                const rowH = isMobile ? 84 : 100;
                const cols = Math.floor((window.innerHeight - 80) / rowH);
                const positions: Record<string, { x: number; y: number }> = {};
                APPS.forEach((app, i) => {
                  const col = Math.floor(i / cols);
                  const row = i % cols;
                  positions[app.id] = { x: 8 + col * gap, y: 8 + row * rowH };
                });
                setIconPositions(positions);
                localStorage.removeItem("xp-icon-positions");
              }}
              className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
            >
              <BarChart3 className="w-3.5 h-3.5" />
              Simgeleri Düzenle
            </button>
            <button
              onClick={() => {
                setCtxMenu(null);
                setShowAbout(true);
              }}
              className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
            >
              <Brain className="w-3.5 h-3.5" />
              Hakkında
            </button>
          </div>
        )}

        {/* Icon Right-Click Context Menu */}
        {iconCtxMenu && (
          <div
            className="xp-ctx-menu fixed z-[200] bg-white rounded shadow-[2px_2px_8px_rgba(0,0,0,0.3)] border border-gray-300 py-1 min-w-[180px] max-w-[90vw] text-[12px] text-gray-800"
            style={{
              left: Math.min(iconCtxMenu.x, window.innerWidth - 200),
              top: Math.min(iconCtxMenu.y, window.innerHeight - 120),
            }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => {
                openApp(iconCtxMenu.appId);
                setIconCtxMenu(null);
              }}
              className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5 font-bold"
            >
              <FolderOpen className="w-3.5 h-3.5" />
              Aç
            </button>
            <div className="border-t border-gray-200 my-1" />
            <button
              onClick={() => {
                setPropsDialog(iconCtxMenu.appId);
                setIconCtxMenu(null);
              }}
              className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
            >
              <Info className="w-3.5 h-3.5" />
              Özellikler
            </button>
          </div>
        )}
      </div>

      {/* App Properties Dialog — Windows XP style */}
      {propsDialog &&
        (() => {
          const app = APPS.find((a) => a.id === propsDialog);
          if (!app) return null;
          return (
            <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/40">
              <div className="w-full max-w-[92vw] sm:w-[380px] rounded-lg overflow-hidden shadow-2xl border border-[#0054e3]">
                <div className="flex items-center justify-between px-3 py-1.5 bg-gradient-to-r from-[#0054e3] via-[#0066ff] to-[#3b8aff]">
                  <span className="text-white text-xs font-bold tracking-wide">
                    {app.title} — Özellikler
                  </span>
                  <button
                    onClick={() => setPropsDialog(null)}
                    className="w-5 h-5 rounded-sm bg-red-500 hover:bg-red-400 text-white text-[11px] font-bold flex items-center justify-center leading-none border border-red-700"
                  >
                    &#10005;
                  </button>
                </div>
                <div className="bg-[#ece9d8] p-5">
                  <div className="flex items-center gap-4 mb-4 pb-4 border-b border-gray-400/40">
                    <div
                      className="w-14 h-14 rounded-lg flex items-center justify-center shadow-md"
                      style={{
                        backgroundColor: app.color + "20",
                        border: `2px solid ${app.color}`,
                      }}
                    >
                      <span style={{ color: app.color }}>{app.icon}</span>
                    </div>
                    <div>
                      <h3 className="text-[14px] font-bold text-gray-900">
                        {app.title}
                      </h3>
                      <p className="text-[11px] text-gray-500 mt-0.5">
                        Kategori: {app.group}
                      </p>
                    </div>
                  </div>
                  <div className="mb-4">
                    <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider block mb-1.5">
                      Açıklama
                    </label>
                    <p className="text-[12px] text-gray-700 leading-relaxed bg-white rounded border border-gray-300 p-3">
                      {app.description}
                    </p>
                  </div>
                  <div className="bg-white rounded border border-gray-300 p-3 mb-4">
                    <div className="grid grid-cols-2 gap-y-2 text-[11px]">
                      <span className="text-gray-500">Tür:</span>
                      <span className="text-gray-800 font-medium">
                        Uygulama Penceresi
                      </span>
                      <span className="text-gray-500">Varsayılan Boyut:</span>
                      <span className="text-gray-800 font-medium">
                        {app.defaultW} × {app.defaultH} px
                      </span>
                      <span className="text-gray-500">Grup:</span>
                      <span className="text-gray-800 font-medium">
                        {app.group}
                      </span>
                      <span className="text-gray-500">Kısayol:</span>
                      <span className="text-gray-800 font-medium">
                        Çift tıkla ile aç
                      </span>
                    </div>
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        openApp(app.id);
                        setPropsDialog(null);
                      }}
                      className="px-4 py-1.5 text-[12px] bg-white hover:bg-gray-50 border border-gray-400 rounded text-gray-700 font-medium shadow-sm active:shadow-inner"
                    >
                      Aç
                    </button>
                    <button
                      onClick={() => setPropsDialog(null)}
                      className="px-5 py-1.5 text-[12px] bg-[#ece9d8] hover:bg-[#ddd8c6] border border-gray-400 rounded text-gray-700 font-medium shadow-sm active:shadow-inner"
                    >
                      Tamam
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

      {/* About Dialog — Windows XP style */}
      {showAbout && (
        <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/40">
          <div className="w-full max-w-[92vw] sm:w-[440px] rounded-lg overflow-hidden shadow-2xl border border-[#0054e3]">
            <div className="flex items-center justify-between px-3 py-1.5 bg-gradient-to-r from-[#0054e3] via-[#0066ff] to-[#3b8aff]">
              <span className="text-white text-xs font-bold tracking-wide">
                Hakk&#305;nda
              </span>
              <button
                onClick={() => setShowAbout(false)}
                className="w-5 h-5 rounded-sm bg-red-500 hover:bg-red-400 text-white text-[11px] font-bold flex items-center justify-center leading-none border border-red-700"
              >
                &#10005;
              </button>
            </div>
            <div className="bg-white p-6">
              <div className="flex items-center gap-4 mb-5">
                <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-[#0054e3] to-[#7c3aed] flex items-center justify-center shadow-lg">
                  <Bot className="w-9 h-9 text-white" />
                </div>
                <div>
                  <h2 className="text-[15px] font-bold text-gray-900 leading-tight">
                    Multi-Agent &#304;&#351;letim Sistemi
                  </h2>
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    S&#252;r&#252;m 1.0.0
                  </p>
                </div>
              </div>
              <div className="border-t border-gray-200 my-4" />
              <p className="text-[12px] text-gray-700 leading-relaxed mb-4">
                Otonom yapay zeka agentlar&#305;n&#305; orkestre eden, izleyen
                ve optimize eden yeni nesil &#231;oklu-agent y&#246;netim
                platformu. Ger&#231;ek zamanl&#305; g&#246;rev
                ak&#305;&#351;&#305;, bellek y&#246;netimi, benchmark analizi ve
                tam &#246;zerk evrim deste&#287;i.
              </p>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                <p className="text-[11px] text-gray-400 mb-3 text-center uppercase tracking-wider">
                  Ekip
                </p>
                <div className="flex items-start justify-center gap-8">
                  <div className="flex flex-col items-center gap-1.5">
                    <div className="w-11 h-11 rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-white text-sm font-bold shadow">
                      EE
                    </div>
                    <p className="text-[13px] font-semibold text-gray-800">
                      Erkan Erdem
                    </p>
                    <p className="text-[10px] text-blue-600 font-medium">
                      Full Stack Developer
                    </p>
                  </div>
                  <div className="flex flex-col items-center gap-1.5">
                    <div className="w-11 h-11 rounded-full bg-gradient-to-br from-purple-500 to-pink-400 flex items-center justify-center text-white text-sm font-bold shadow">
                      YA
                    </div>
                    <p className="text-[13px] font-semibold text-gray-800">
                      Yi&#287;it Avc&#305;
                    </p>
                    <p className="text-[10px] text-purple-600 font-medium">
                      Project Builder
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between mt-5">
                <p className="text-[10px] text-gray-400">
                  &#169; 2025 T&#252;m haklar&#305; sakl&#305;d&#305;r.
                </p>
                <button
                  onClick={() => setShowAbout(false)}
                  className="px-5 py-1.5 text-[12px] bg-[#ece9d8] hover:bg-[#ddd8c6] border border-gray-400 rounded text-gray-700 font-medium shadow-sm active:shadow-inner"
                >
                  Tamam
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* System Guide Dialog */}
      <SystemGuideDialog open={showGuide} onClose={() => setShowGuide(false)} />

      {/* Taskbar */}
      <XpTaskbar
        windows={windows}
        onWindowClick={handleTaskbarClick}
        onOpenApp={openApp}
        onHelpOpen={() => setShowGuide(true)}
        onAddShortcut={(appId) => {
          // Bring the icon to a visible position on desktop
          const app = APPS.find((a) => a.id === appId);
          if (!app) return;
          // Place it at a prominent position (center-ish of viewport)
          setIconPositions((prev) => ({
            ...prev,
            [appId]: {
              x: Math.max(16, Math.floor(window.innerWidth / 2 - 40)),
              y: Math.max(16, Math.floor(window.innerHeight / 3)),
            },
          }));
        }}
        apps={taskbarApps}
      />
    </div>
  );
}
