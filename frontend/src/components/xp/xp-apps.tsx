"use client";

import { useState, type ReactNode } from "react";
import dynamic from "next/dynamic";
import { FeatherIcon } from "./xp-feather-icon";

// ── Lazy-loaded panel components ──
const ChatDesktopPanel = dynamic(() => import("./panels/xp-chat-panel"), {
  ssr: false,
});
const UnifiedTaskMonitor = dynamic(
  () =>
    import("@/components/unified-task-monitor").then((m) => ({
      default: m.UnifiedTaskMonitor,
    })),
  { ssr: false },
);
const AutonomousOversightPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.AutonomousOversightPanel,
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

const AutonomousEvolutionPanel = dynamic(
  () =>
    import("@/components/agent-evolution-panel").then((m) => ({
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
const AgentIdentityEditor = dynamic(
  () =>
    import("@/components/agent-identity-editor").then((m) => ({
      default: m.AgentIdentityEditor,
    })),
  { ssr: false },
);
const BenchmarkPanel = dynamic(
  () =>
    import("@/components/benchmark").then((m) => ({
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
const PerformanceDashboard = dynamic(
  () => import("@/components/performance-dashboard"),
  { ssr: false },
);
const AutoOptimizerPanel = dynamic(
  () => import("@/components/auto-optimizer-panel"),
  { ssr: false },
);
const XpReportsPanel = dynamic(
  () =>
    import("./panels/xp-reports-panel").then((m) => ({
      default: m.XpReportsPanel,
    })),
  { ssr: false },
);
const XpSearchPanel = dynamic(
  () =>
    import("./panels/xp-search-panel").then((m) => ({
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
const McpPanel = dynamic(
  () =>
    import("@/components/tools-panels").then((m) => ({
      default: m.McpPanel,
    })),
  { ssr: false },
);
const WorkflowBuilderPanel = dynamic(
  () =>
    import("@/components/workflow-builder-panel").then((m) => ({
      default: m.WorkflowBuilderPanel,
    })),
  { ssr: false },
);
const ChartPanel = dynamic(
  () =>
    import("@/components/chart-panel").then((m) => ({
      default: m.ChartPanel,
    })),
  { ssr: false },
);
const ImageStudioPanel = dynamic(
  () =>
    import("@/components/image-studio-panel").then((m) => ({
      default: m.ImageStudioPanel,
    })),
  { ssr: false },
);
const WorkflowHistoryPanel = dynamic(
  () =>
    import("@/components/workflow-history-panel").then((m) => ({
      default: m.WorkflowHistoryPanel,
    })),
  { ssr: false },
);
const ContextBoardPanel = dynamic(
  () =>
    import("@/components/context-board-panel").then((m) => ({
      default: m.ContextBoardPanel,
    })),
  { ssr: false },
);
const DynamicRolePanel = dynamic(
  () =>
    import("@/components/dynamic-role-panel").then((m) => ({
      default: m.DynamicRolePanel,
    })),
  { ssr: false },
);
const CollaborativeEditorPanel = dynamic(
  () =>
    import("@/components/collaborative-editor-panel").then((m) => ({
      default: m.CollaborativeEditorPanel,
    })),
  { ssr: false },
);
const WorktreePanel = dynamic(
  () =>
    import("@/components/worktree-panel").then((m) => ({
      default: m.WorktreePanel,
    })),
  { ssr: false },
);
const DomainMarketplacePanel = dynamic(
  () =>
    import("@/components/domain-marketplace-panel").then((m) => ({
      default: m.DomainMarketplacePanel,
    })),
  { ssr: false },
);
const AdaptiveToolSelectorPanel = dynamic(
  () =>
    import("@/components/adaptive-tool-selector-panel").then((m) => ({
      default: m.AdaptiveToolSelectorPanel,
    })),
  { ssr: false },
);
const WorkflowOptimizerPanel = dynamic(
  () =>
    import("@/components/workflow-optimizer-panel").then((m) => ({
      default: m.WorkflowOptimizerPanel,
    })),
  { ssr: false },
);

const LearningHubPanel = dynamic(
  () =>
    import("@/components/learning-hub-panel").then((m) => ({
      default: m.LearningHubPanel,
    })),
  { ssr: false },
);
const ModelManagerPanel = dynamic(
  () => import("@/components/model-manager-panel"),
  { ssr: false },
);
const SkillCreatorPanel = dynamic(
  () =>
    import("@/components/skill-creator-panel").then((m) => ({
      default: m.SkillCreatorPanel,
    })),
  { ssr: false },
);
const XpMarketplacePanel = dynamic(
  () =>
    import("./panels/xp-marketplace-panel").then((m) => ({
      default: m.XpMarketplacePanel,
    })),
  { ssr: false },
);
const SharedWorkspacePanel = dynamic(
  () =>
    import("@/components/shared-workspace-panel").then((m) => ({
      default: m.SharedWorkspacePanel,
    })),
  { ssr: false },
);
const McpUsagePanel = dynamic(
  () =>
    import("@/components/mcp-usage-panel").then((m) => ({
      default: m.McpUsagePanel,
    })),
  { ssr: false },
);
const PresentationBuilderPanel = dynamic(
  () => import("@/components/presentation-builder-panel"),
  { ssr: false },
);
const ResiliencePanel = dynamic(
  () =>
    import("@/components/resilience").then((m) => ({
      default: m.ResiliencePanel,
    })),
  { ssr: false },
);

// ── Panel imports from xp/panels ──
import { XpAgentsPanel } from "./panels/xp-agents-panel";
import { XpSessionsPanel } from "./panels/xp-sessions-panel";
import { XpToolsPanel } from "./panels/xp-tools-panel";
import { XpSkillsHubPanel } from "./panels/xp-skills-hub-panel";
import { XpRoadmapPanel } from "./panels/xp-roadmap-panel";
import { XpCollaborationPanel } from "./panels/xp-collaboration";
import { XpAnalyticsPanel } from "./panels/xp-analytics";
import { XpAgentCenter } from "./panels/xp-agent-center";
import { XpUnifiedMarketplace } from "./panels/xp-unified-marketplace";
import { XpToolsUnified } from "./panels/xp-tools-unified";

// ── App definition type ──
export interface DesktopApp {
  id: string;
  title: string;
  icon: ReactNode;
  color: string;
  group: string;
  description: string;
  defaultW: number;
  defaultH: number;
  render: () => ReactNode;
}

// ── Workflows wrapper with history tab ──
function XpWorkflowsWrapper() {
  const [tab, setTab] = useState<"builder" | "history">("builder");
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #d6d2c2",
          background: "#ECE9D8",
          padding: "0 4px",
        }}
      >
        {[
          { id: "builder" as const, label: "İş Akışları" },
          { id: "history" as const, label: "Geçmiş" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "6px 14px",
              fontSize: 11,
              fontFamily: "Tahoma, sans-serif",
              fontWeight: tab === t.id ? 600 : 400,
              background: tab === t.id ? "#fff" : "transparent",
              border:
                tab === t.id ? "1px solid #d6d2c2" : "1px solid transparent",
              borderBottom:
                tab === t.id ? "1px solid #fff" : "1px solid #d6d2c2",
              borderRadius: "3px 3px 0 0",
              marginBottom: -1,
              cursor: "pointer",
              color: tab === t.id ? "#000" : "#555",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-hidden">
        {tab === "builder" ? (
          <WorkflowBuilderPanel />
        ) : (
          <WorkflowHistoryPanel />
        )}
      </div>
    </div>
  );
}

// ── MCP wrapper with usage tab ──
function XpMcpWrapper() {
  const [tab, setTab] = useState<"servers" | "usage">("servers");
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #d6d2c2",
          background: "#ECE9D8",
          padding: "0 4px",
        }}
      >
        {[
          { id: "servers" as const, label: "MCP Sunucuları" },
          { id: "usage" as const, label: "Kullanım İstatistikleri" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "6px 14px",
              fontSize: 11,
              fontFamily: "Tahoma, sans-serif",
              fontWeight: tab === t.id ? 600 : 400,
              background: tab === t.id ? "#fff" : "transparent",
              border:
                tab === t.id ? "1px solid #d6d2c2" : "1px solid transparent",
              borderBottom:
                tab === t.id ? "1px solid #fff" : "1px solid #d6d2c2",
              borderRadius: "3px 3px 0 0",
              marginBottom: -1,
              cursor: "pointer",
              color: tab === t.id ? "#000" : "#555",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {tab === "servers" ? (
          <div className="p-4">
            <McpPanel />
          </div>
        ) : (
          <McpUsagePanel />
        )}
      </div>
    </div>
  );
}

// ── All desktop applications ──
export const APPS: DesktopApp[] = [
  {
    id: "chat",
    title: "Sohbet",
    icon: <FeatherIcon name="message-square" color="#3b82f6" />,
    color: "#3b82f6",
    group: "Ana",
    description:
      "Agent'larla sohbet edin, görev gönderin. Orchestrator mesajınızı analiz edip uygun specialist agent'lara yönlendirir.",
    defaultW: 700,
    defaultH: 500,
    render: () => <ChatDesktopPanel />,
  },
  {
    id: "monitor",
    title: "Görev İzleme",
    icon: <FeatherIcon name="activity" color="#8b5cf6" />,
    color: "#8b5cf6",
    group: "Ana",
    description:
      "Canlı akış, görev detayı, agent durumu ve sistem izleme — tek sekmeli panel.",
    defaultW: 850,
    defaultH: 600,
    render: () => <UnifiedTaskMonitor />,
  },
  {
    id: "autonomous-oversight",
    title: "Otonom İzleme",
    icon: <FeatherIcon name="eye" color="#a78bfa" />,
    color: "#a78bfa",
    group: "Agent",
    description:
      "Otonom agent davranışları ve konuşmalarını tek ekrandan izleyin — canlı aktivite, otonom sohbetler, heartbeat.",
    defaultW: 600,
    defaultH: 560,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <AutonomousOversightPanel />
      </div>
    ),
  },

  {
    id: "memory",
    title: "Bellek",
    icon: <FeatherIcon name="hard-drive" color="#ec4899" />,
    color: "#ec4899",
    group: "Ana",
    description: "Agent bellek zaman çizelgesi ve korelasyon analizi.",
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
    id: "evolution",
    title: "Gelişim",
    icon: <FeatherIcon name="trending-up" color="#10b981" />,
    color: "#10b981",
    group: "Agent",
    description: "Agent'ların zaman içindeki performans gelişimini takip edin.",
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
    icon: <FeatherIcon name="link-2" color="#f59e0b" />,
    color: "#f59e0b",
    group: "Agent",
    description: "Agent'lar arası koordinasyon ve iş birliği haritası.",
    defaultW: 650,
    defaultH: 480,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <CoordinationPanel />
      </div>
    ),
  },

  {
    id: "autonomous",
    title: "Özerk Evrim",
    icon: <FeatherIcon name="hexagon" color="#a78bfa" />,
    color: "#a78bfa",
    group: "Agent",
    description: "Agent'ların özerk öğrenme ve evrim süreçlerini izleyin.",
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
    icon: <FeatherIcon name="radio" color="#f43f5e" />,
    color: "#f43f5e",
    group: "Agent",
    description: "Agent'lar arası mesajlaşma ve iletişim kanalları.",
    defaultW: 600,
    defaultH: 500,
    render: () => (
      <div className="overflow-hidden h-full">
        <AgentCommsPanel />
      </div>
    ),
  },
  {
    id: "identity",
    title: "Agent Kimliği",
    icon: <FeatherIcon name="user" color="#8b5cf6" />,
    color: "#8b5cf6",
    group: "Agent",
    description: "Agent kimlikleri ve tercihlerini düzenleyin.",
    defaultW: 500,
    defaultH: 420,
    render: () => (
      <div className="overflow-auto h-full p-3">
        <AgentIdentityEditor />
      </div>
    ),
  },
  {
    id: "benchmark",
    title: "Benchmark",
    icon: <FeatherIcon name="award" color="#eab308" />,
    color: "#eab308",
    group: "Analitik",
    description: "Agent performans kıyaslama testleri.",
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
    icon: <FeatherIcon name="alert-triangle" color="#ef4444" />,
    color: "#ef4444",
    group: "Analitik",
    description: "Hata örüntülerini tespit edin ve analiz edin.",
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
    icon: <FeatherIcon name="search" color="#06b6d4" />,
    color: "#06b6d4",
    group: "Analitik",
    description: "Tüm oturumlar, görevler ve agent yanıtları içinde arama.",
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
    icon: <FeatherIcon name="zap" color="#f97316" />,
    color: "#f97316",
    group: "Analitik",
    description: "Otomatik optimizasyon motoru.",
    defaultW: 650,
    defaultH: 480,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <AutoOptimizerPanel />
      </div>
    ),
  },
  {
    id: "performance",
    title: "Performans",
    icon: <FeatherIcon name="activity" color="#06b6d4" />,
    color: "#06b6d4",
    group: "Analitik",
    description: "Agent performans metriklerini izleyin.",
    defaultW: 750,
    defaultH: 520,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <PerformanceDashboard />
      </div>
    ),
  },
  {
    id: "costs",
    title: "Maliyet",
    icon: <FeatherIcon name="dollar-sign" color="#84cc16" />,
    color: "#84cc16",
    group: "Analitik",
    description: "API kullanım maliyetlerini takip edin.",
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
    icon: <FeatherIcon name="folder" color="#f59e0b" />,
    color: "#f59e0b",
    group: "Ana",
    description: "Oluşturulan raporları ve proje dosyalarını görüntüleyin.",
    defaultW: 750,
    defaultH: 500,
    render: () => (
      <div className="overflow-hidden h-full">
        <XpReportsPanel />
      </div>
    ),
  },
  {
    id: "workflows",
    title: "İş Akışları",
    icon: <FeatherIcon name="repeat" color="#f59e0b" />,
    color: "#f59e0b",
    group: "Ana",
    description: "Workflow şablonlarını çalıştırın ve yönetin.",
    defaultW: 750,
    defaultH: 550,
    render: () => <XpWorkflowsWrapper />,
  },

  {
    id: "agents",
    title: "Agentlar",
    icon: <FeatherIcon name="users" color="#ec4899" />,
    color: "#ec4899",
    group: "Sistem",
    description: "Tüm agent'ların listesi ve durumları.",
    defaultW: 400,
    defaultH: 480,
    render: () => <XpAgentsPanel />,
  },
  {
    id: "sessions",
    title: "Oturumlar",
    icon: <FeatherIcon name="archive" color="#3b82f6" />,
    color: "#3b82f6",
    group: "Sistem",
    description: "Geçmiş sohbet oturumlarını listeleyin.",
    defaultW: 420,
    defaultH: 500,
    render: () => <XpSessionsPanel />,
  },
  {
    id: "rag",
    title: "Bilgi Tabanı (RAG)",
    icon: <FeatherIcon name="database" color="#f472b6" />,
    color: "#f472b6",
    group: "Araçlar",
    description: "Retrieval-Augmented Generation bilgi tabanı.",
    defaultW: 550,
    defaultH: 500,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <RagPanel />
      </div>
    ),
  },
  {
    id: "tools",
    title: "Araçlar",
    icon: <FeatherIcon name="tool" color="#8b5cf6" />,
    color: "#8b5cf6",
    group: "Sistem",
    description: "Skills, MCP, Teachability ve Eval araçlarını yönetin.",
    defaultW: 450,
    defaultH: 550,
    render: () => <XpToolsPanel />,
  },
  {
    id: "roadmap",
    title: "Yol Haritası",
    icon: <FeatherIcon name="map" color="#14b8a6" />,
    color: "#14b8a6",
    group: "Sistem",
    description: "Geliştirme yol haritasını görüntüleyin.",
    defaultW: 700,
    defaultH: 550,
    render: () => <XpRoadmapPanel />,
  },
  {
    id: "charts",
    title: "Grafikler",
    icon: <FeatherIcon name="bar-chart-2" color="#06b6d4" />,
    color: "#06b6d4",
    group: "Analitik",
    description: "Veri görselleştirme ve grafik oluşturma.",
    defaultW: 700,
    defaultH: 550,
    render: () => (
      <div className="overflow-hidden h-full">
        <ChartPanel />
      </div>
    ),
  },
  {
    id: "image-studio",
    title: "Görsel Stüdyo",
    icon: <FeatherIcon name="image" color="#a855f7" />,
    color: "#a855f7",
    group: "Analitik",
    description:
      "Prompt ile görsel oluştur (zimage, flux, imagen-4, grok-imagine). İndir ve prompt iyileştir.",
    defaultW: 560,
    defaultH: 640,
    render: () => (
      <div className="overflow-hidden h-full">
        <ImageStudioPanel />
      </div>
    ),
  },
  {
    id: "skills-hub",
    title: "Yetenekler",
    icon: <FeatherIcon name="layers" color="#a855f7" />,
    color: "#a855f7",
    group: "Araçlar",
    description: "Skill yönetim merkezi — mevcut yetenekleri görüntüleyin.",
    defaultW: 800,
    defaultH: 600,
    render: () => <XpSkillsHubPanel />,
  },
  {
    id: "mcp",
    title: "MCP Sunucuları",
    icon: <FeatherIcon name="server" color="#0ea5e9" />,
    color: "#0ea5e9",
    group: "Araçlar",
    description:
      "MCP sunucularını yönetin ve kullanım istatistiklerini görüntüleyin.",
    defaultW: 600,
    defaultH: 550,
    render: () => <XpMcpWrapper />,
  },
  {
    id: "context-board",
    title: "Bağlam Panosu",
    icon: <FeatherIcon name="clipboard" color="#14b8a6" />,
    color: "#14b8a6",
    group: "Agent",
    description: "Paylaşımlı çalışma alanı — agent'ların ortak bağlam panosu.",
    defaultW: 600,
    defaultH: 520,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <ContextBoardPanel />
      </div>
    ),
  },
  {
    id: "dynamic-roles",
    title: "Dinamik Roller",
    icon: <FeatherIcon name="user-check" color="#8b5cf6" />,
    color: "#8b5cf6",
    group: "Agent",
    description:
      "Dinamik rol atama — agent'lara çalışma zamanında roller atayın.",
    defaultW: 620,
    defaultH: 540,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <DynamicRolePanel />
      </div>
    ),
  },
  {
    id: "collab-editor",
    title: "Collaborative Editor",
    icon: <FeatherIcon name="edit-3" color="#10b981" />,
    color: "#10b981",
    group: "İşbirliği",
    description: "Çoklu agent eşzamanlı dosya düzenleme",
    defaultW: 900,
    defaultH: 600,
    render: () => (
      <div className="h-full">
        <CollaborativeEditorPanel />
      </div>
    ),
  },
  {
    id: "worktree",
    title: "Worktree Collaboration",
    icon: <FeatherIcon name="git-branch" color="#f59e0b" />,
    color: "#f59e0b",
    group: "İşbirliği",
    description: "Git worktree bazlı paralel geliştirme",
    defaultW: 900,
    defaultH: 600,
    render: () => (
      <div className="h-full">
        <WorktreePanel />
      </div>
    ),
  },
  {
    id: "shared-workspace",
    title: "Shared Workspace",
    icon: <FeatherIcon name="folder-plus" color="#14b8a6" />,
    color: "#14b8a6",
    group: "İşbirliği",
    description:
      "Paylaşımlı çalışma alanları — notlar, kodlar, kararlar ve bulgular.",
    defaultW: 800,
    defaultH: 560,
    render: () => (
      <div className="h-full">
        <SharedWorkspacePanel />
      </div>
    ),
  },
  {
    id: "collaboration",
    title: "İşbirliği Merkezi",
    icon: <FeatherIcon name="users" color="#8b5cf6" />,
    color: "#8b5cf6",
    group: "İşbirliği",
    description:
      "Birleşik işbirliği paneli — Paylaşımlı Alan, Bağlam Panosu, Düzenleyici ve Worktree sekmeleri.",
    defaultW: 900,
    defaultH: 600,
    render: () => <XpCollaborationPanel />,
  },
  {
    id: "marketplace",
    title: "Domain Marketplace",
    icon: <FeatherIcon name="shopping-bag" color="#a855f7" />,
    color: "#a855f7",
    group: "Araçlar",
    description:
      "Alan uzmanlığı skill'leri — finans, hukuk, mühendislik, akademik.",
    defaultW: 700,
    defaultH: 550,
    render: () => (
      <div className="overflow-hidden h-full">
        <DomainMarketplacePanel />
      </div>
    ),
  },
  {
    id: "adaptive-tools",
    title: "Adaptif Araçlar",
    icon: <FeatherIcon name="sliders" color="#06b6d4" />,
    color: "#06b6d4",
    group: "Araçlar",
    description: "Kullanım, öneriler, matris ve tercih bazlı araç seçimi.",
    defaultW: 750,
    defaultH: 550,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <AdaptiveToolSelectorPanel />
      </div>
    ),
  },
  {
    id: "workflow-optimizer",
    title: "Workflow Optimizer",
    icon: <FeatherIcon name="repeat" color="#f97316" />,
    color: "#f97316",
    group: "Analitik",
    description: "İş akışı önerileri, detay ve pattern kütüphanesi.",
    defaultW: 750,
    defaultH: 550,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <WorkflowOptimizerPanel />
      </div>
    ),
  },

  {
    id: "learning-hub",
    title: "Öğrenme Merkezi",
    icon: <FeatherIcon name="book-open" color="#22d3ee" />,
    color: "#22d3ee",
    group: "Analitik",
    description:
      "Adaptif öğrenme merkezi — tüm öğrenme mekanizmalarını tek panelde izleyin ve yönetin.",
    defaultW: 700,
    defaultH: 560,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <LearningHubPanel />
      </div>
    ),
  },
  {
    id: "analytics",
    title: "Analitik Merkezi",
    icon: <FeatherIcon name="bar-chart-2" color="#10b981" />,
    color: "#10b981",
    group: "Analitik",
    description:
      "Benchmark, performans, maliyet takibi, hata analizi ve otomatik optimizasyon.",
    defaultW: 800,
    defaultH: 600,
    render: () => <XpAnalyticsPanel />,
  },
  {
    id: "agent-center",
    title: "Agent Merkezi",
    icon: <FeatherIcon name="users" color="#ec4899" />,
    color: "#ec4899",
    group: "Agent",
    description:
      "Birleşik agent yönetimi — Agentlar, Otonom İzleme, Koordinasyon, İletişim, Kimlik ve Roller sekmeleri.",
    defaultW: 900,
    defaultH: 600,
    render: () => <XpAgentCenter />,
  },
  {
    id: "unified-marketplace",
    title: "Pazar Merkezi",
    icon: <FeatherIcon name="shopping-bag" color="#a855f7" />,
    color: "#a855f7",
    group: "Araçlar",
    description:
      "Birleşik pazar yeri — Domain Marketplace, Yetenekler ve Skill Marketplace sekmeleri.",
    defaultW: 800,
    defaultH: 600,
    render: () => <XpUnifiedMarketplace />,
  },
  {
    id: "tools-unified",
    title: "Araçlar Merkezi",
    icon: <FeatherIcon name="tool" color="#8b5cf6" />,
    color: "#8b5cf6",
    group: "Araçlar",
    description:
      "Birleşik araçlar paneli — Araçlar, Skill Oluşturucu ve Adaptif Araçlar sekmeleri.",
    defaultW: 800,
    defaultH: 600,
    render: () => <XpToolsUnified />,
  },
  {
    id: "model-manager",
    title: "Model Yönetimi",
    icon: <FeatherIcon name="cpu" color="#f472b6" />,
    color: "#f472b6",
    group: "Sistem",
    description:
      "Provider/model seçimi, agent-model eşleme, gateway durumu ve doğrulama.",
    defaultW: 700,
    defaultH: 560,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <ModelManagerPanel />
      </div>
    ),
  },
  {
    id: "skill-creator",
    title: "Skill Oluşturucu",
    icon: <FeatherIcon name="edit" color="#8b5cf6" />,
    color: "#8b5cf6",
    group: "Araçlar",
    description: "Skill doğrulama, test ve oluşturma aracı.",
    defaultW: 700,
    defaultH: 560,
    render: () => (
      <div className="p-4 overflow-auto h-full">
        <SkillCreatorPanel />
      </div>
    ),
  },
  {
    id: "skill-marketplace",
    title: "Marketplace",
    icon: <FeatherIcon name="shopping-cart" color="#f59e0b" />,
    color: "#f59e0b",
    group: "Araçlar",
    description: "Skill ve domain uzmanlığı mağazası — keşfet, yükle, yönet.",
    defaultW: 700,
    defaultH: 560,
    render: () => (
      <div className="overflow-hidden h-full">
        <XpMarketplacePanel />
      </div>
    ),
  },
  {
    id: "resilience",
    title: "Resilience & Monitoring",
    icon: <FeatherIcon name="shield" color="#ef4444" />,
    color: "#ef4444",
    group: "Sistem",
    description:
      "Sistem sağlığı, Prometheus metrikleri, dinamik eşikler, chaos engineering, bilgi moderasyonu ve federated learning izleme.",
    defaultW: 780,
    defaultH: 580,
    render: () => <ResiliencePanel />,
  },
  {
    id: "presentations",
    title: "Sunum Oluşturucu",
    icon: <FeatherIcon name="monitor" color="#7c3aed" />,
    color: "#7c3aed",
    group: "Araçlar",
    description:
      "AI destekli sunum oluşturucu — konu girin, araştırma yapılsın, slaytlar hazırlansın. Düzenlenebilir canvas, görsel üretimi.",
    defaultW: 1000,
    defaultH: 650,
    render: () => (
      <div className="overflow-hidden h-full">
        <PresentationBuilderPanel />
      </div>
    ),
  },
];
