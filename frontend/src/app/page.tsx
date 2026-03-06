"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useAgentSocket } from "@/lib/use-agent-socket";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Thread, ThreadSummary, PipelineType } from "@/lib/types";
import { useToast } from "@/components/toast";
import { CockpitHeader } from "@/components/cockpit-header";
import type { NavTab } from "@/components/cockpit-header";
import { SystemGuideDialog } from "@/components/system-guide-dialog";
import { RoadmapDialog } from "@/components/roadmap-dialog";
import { PipelineSelector } from "@/components/pipeline-selector";
import { ChatArea } from "@/components/chat-area";
import { ChatInput } from "@/components/chat-input";
import { LiveEventLog } from "@/components/live-event-log";
import { TaskHistory } from "@/components/task-history";
import { ExportButtons } from "@/components/export-buttons";
import { MobileNav } from "@/components/mobile-nav";
import { MobileResultPanel } from "@/components/mobile-result-panel";
import { TaskFlowMonitor } from "@/components/task-flow-monitor";

const Sidebar = dynamic(
  () => import("@/components/sidebar").then((m) => ({ default: m.Sidebar })),
  {
    ssr: false,
    loading: () => (
      <div className="w-72 h-full bg-surface/50 animate-pulse" aria-hidden />
    ),
  },
);

const AgentHealthPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.AgentHealthPanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-48 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const LeaderboardPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.LeaderboardPanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-32 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const SystemStatsPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.SystemStatsPanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-24 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const AnomalyPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.AnomalyPanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-32 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const MemoryTimelinePanel = dynamic(
  () =>
    import("@/components/memory-panels").then((m) => ({
      default: m.MemoryTimelinePanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-48 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const MemoryCorrelationPanel = dynamic(
  () =>
    import("@/components/memory-panels").then((m) => ({
      default: m.MemoryCorrelationPanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-48 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const AgentEvolutionPanel = dynamic(
  () =>
    import("@/components/agent-evolution-panel").then((m) => ({
      default: m.AgentEvolutionPanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-48 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const CoordinationPanel = dynamic(
  () =>
    import("@/components/coordination-panel").then((m) => ({
      default: m.CoordinationPanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-48 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const AgentEcosystemMap = dynamic(
  () =>
    import("@/components/agent-ecosystem-map").then((m) => ({
      default: m.AgentEcosystemMap,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-48 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const AutonomousEvolutionPanel = dynamic(
  () =>
    import("@/components/autonomous-evolution-panel").then((m) => ({
      default: m.AutonomousEvolutionPanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-48 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);
const AgentCommsPanel = dynamic(
  () =>
    import("@/components/agent-comms-panel").then((m) => ({
      default: m.AgentCommsPanel,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="h-48 bg-surface/50 animate-pulse rounded-lg"
        aria-hidden
      />
    ),
  },
);

export default function Home() {
  const router = useRouter();
  const { user } = useAuth();

  const [authValidated, setAuthValidated] = useState(false);
  const lastValidatedTokenRef = useRef<string | null>(null);
  const [thread, setThread] = useState<Thread | null>(null);
  const [threadList, setThreadList] = useState<ThreadSummary[]>([]);
  const [pipeline, setPipeline] = useState<PipelineType>("auto");
  const [lastError, setLastError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<NavTab>("chat");
  const [showSystemGuide, setShowSystemGuide] = useState(false);
  const [showRoadmap, setShowRoadmap] = useState(false);
  const toast = useToast();

  const { status, liveEvents, sendMessage, stop } = useAgentSocket({
    enabled: !!user && authValidated,
    onResult: (_tid, _result, updatedThread) => {
      setThread(updatedThread);
      setLastError(null);
      loadThreadList();
    },
    onError: (msg) => setLastError(msg),
  });

  const loadThreadList = useCallback(async () => {
    try {
      const list = await api.listThreads();
      setThreadList(list);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Thread listesi yüklenemedi";
      setLastError(msg);
    }
  }, []);

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    const token = user.token?.trim();
    if (!token) {
      setAuthValidated(false);
      router.replace("/login");
      return;
    }
    if (lastValidatedTokenRef.current === token) {
      setAuthValidated(true);
      return;
    }
    const sessionKey = "auth:validated-token";
    if (
      typeof window !== "undefined" &&
      sessionStorage.getItem(sessionKey) === token
    ) {
      lastValidatedTokenRef.current = token;
      setAuthValidated(true);
      return;
    }
    let cancelled = false;
    const validate = async () => {
      try {
        await api.me();
      } catch {
        await new Promise((r) => setTimeout(r, 350));
        await api.me();
      }
      if (cancelled) return;
      lastValidatedTokenRef.current = token;
      if (typeof window !== "undefined")
        sessionStorage.setItem(sessionKey, token);
      setAuthValidated(true);
    };
    validate().catch(() => {
      if (!cancelled) setAuthValidated(false);
    });
    return () => {
      cancelled = true;
    };
  }, [router, user]);

  useEffect(() => {
    if (authValidated && user) loadThreadList();
  }, [authValidated, loadThreadList, user]);

  if (!user) return null;
  if (!authValidated) {
    return (
      <div
        className="flex h-dvh items-center justify-center bg-background"
        aria-busy="true"
      >
        <p className="text-sm text-slate-500">Oturum doğrulanıyor…</p>
      </div>
    );
  }

  const handleSend = (message: string) => {
    sendMessage(message, thread?.id, pipeline);
    setActiveTab("chat");
  };
  const handleNewThread = () => {
    setThread(null);
    setLastError(null);
    setSidebarOpen(false);
  };
  const handleLoadThread = async (id: string) => {
    try {
      const t = await api.getThread(id);
      setThread(t);
      setLastError(null);
      setSidebarOpen(false);
    } catch {
      toast({ type: "error", message: "Thread yüklenemedi" });
    }
  };
  const handleDeleteThread = async (id: string) => {
    try {
      await api.deleteThread(id);
      if (thread?.id === id) setThread(null);
      loadThreadList();
      toast({ type: "success", message: "Thread silindi" });
    } catch {
      toast({ type: "error", message: "Thread silinemedi" });
    }
  };
  const handleDeleteAllThreads = async () => {
    try {
      await api.deleteAllThreads();
      setThread(null);
      loadThreadList();
      toast({ type: "success", message: "Tüm thread'ler silindi" });
    } catch {
      toast({ type: "error", message: "Threadler silinemedi" });
    }
  };
  const isProcessing = status === "running" || status === "connecting";

  /* ── Tab content renderer ── */
  const renderTabContent = () => {
    switch (activeTab) {
      case "chat":
        return (
          <div className="flex-1 flex flex-col min-w-0">
            <div className="flex items-center gap-2 shrink-0 px-2">
              <div className="flex-1 min-w-0">
                <PipelineSelector selected={pipeline} onSelect={setPipeline} />
              </div>
            </div>
            <ChatArea
              thread={thread}
              isProcessing={isProcessing}
              status={status}
            />
            <div className="hidden lg:block">
              {(() => {
                const lastTask = thread?.tasks?.length
                  ? thread.tasks[thread.tasks.length - 1]
                  : null;
                return lastTask?.final_result ? (
                  <ExportButtons
                    result={lastTask.final_result}
                    task={lastTask}
                  />
                ) : null;
              })()}
              <TaskHistory thread={thread} />
              <LiveEventLog events={liveEvents} status={status} />
            </div>
            <div className="lg:hidden">
              <MobileResultPanel
                thread={thread}
                liveEvents={liveEvents}
                status={status}
              />
            </div>
            {lastError && (
              <div
                className="shrink-0 px-3 py-2 bg-red-950/50 border-t border-red-900/50 text-red-300 text-sm flex items-center justify-between"
                role="alert"
              >
                <span>{lastError}</span>
                <button
                  onClick={() => setLastError(null)}
                  className="text-red-400 hover:text-red-200 text-xs p-1 min-w-[44px] min-h-[44px] flex items-center justify-center rounded"
                  aria-label="Hatayı kapat"
                >
                  ✕
                </button>
              </div>
            )}
            <ChatInput
              onSend={handleSend}
              onStop={stop}
              isProcessing={isProcessing}
            />
          </div>
        );
      case "monitor":
        return (
          <div className="flex-1 overflow-y-auto">
            <TaskFlowMonitor thread={thread} liveEvents={liveEvents} />
          </div>
        );
      case "insights":
        return (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <SystemStatsPanel />
            <AgentHealthPanel />
            <AnomalyPanel />
            <LeaderboardPanel />
          </div>
        );
      case "memory":
        return (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <MemoryTimelinePanel />
            <MemoryCorrelationPanel />
          </div>
        );
      case "evolution":
        return (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <AgentEvolutionPanel />
          </div>
        );
      case "coordination":
        return (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <CoordinationPanel />
          </div>
        );
      case "ecosystem":
        return (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <AgentEcosystemMap />
          </div>
        );
      case "autonomous":
        return (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <AutonomousEvolutionPanel />
          </div>
        );
      case "comms":
        return (
          <div className="flex-1 overflow-hidden">
            <AgentCommsPanel />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex h-dvh overflow-hidden">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 drawer-overlay lg:hidden"
          onClick={() => setSidebarOpen(false)}
          role="presentation"
        />
      )}

      {/* Left column: Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-72 flex flex-col transform transition-transform duration-200 ease-out lg:relative lg:translate-x-0 lg:z-auto ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex-1 min-h-0 overflow-hidden">
          <Sidebar
            thread={thread}
            threadList={threadList}
            onNewThread={handleNewThread}
            onLoadThread={handleLoadThread}
            onDeleteThread={handleDeleteThread}
            onDeleteAllThreads={handleDeleteAllThreads}
            liveEvents={liveEvents}
            isProcessing={isProcessing}
            onClose={() => setSidebarOpen(false)}
          />
        </div>
      </div>

      {/* Main content — full width, no right panel */}
      <main className="flex-1 flex flex-col min-w-0" id="main-content">
        <CockpitHeader
          onMenuToggle={() => setSidebarOpen(true)}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onHelpOpen={() => setShowSystemGuide(true)}
          onRoadmapOpen={() => setShowRoadmap(true)}
        />

        <div className="flex-1 flex overflow-hidden">{renderTabContent()}</div>

        {/* Mobile bottom navigation */}
        <MobileNav
          activeTab={activeTab}
          onTabChange={setActiveTab}
          isProcessing={isProcessing}
          liveEventCount={liveEvents.length}
        />

        <SystemGuideDialog
          open={showSystemGuide}
          onClose={() => setShowSystemGuide(false)}
        />

        <RoadmapDialog
          open={showRoadmap}
          onClose={() => setShowRoadmap(false)}
        />

        {/* Desktop footer */}
        <div className="hidden lg:flex items-center justify-center h-8 shrink-0 border-t border-border/40 bg-surface/50 px-4">
          <span className="text-[10px] text-slate-600">
            © 2026 Multi-Agent Ops Center · Code by{" "}
            <span className="text-slate-500">Erkan Erdem</span>
            {" & "}
            <span className="text-slate-500">Yiğit Avcı</span>
          </span>
        </div>
      </main>
    </div>
  );
}
