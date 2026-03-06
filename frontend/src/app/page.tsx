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
import { PipelineSelector } from "@/components/pipeline-selector";
import { ChatArea } from "@/components/chat-area";
import { ChatInput } from "@/components/chat-input";
import { LiveEventLog } from "@/components/live-event-log";
import { TaskHistory } from "@/components/task-history";
import { ExportButtons } from "@/components/export-buttons";
import { MobileNav } from "@/components/mobile-nav";
import { MobileResultPanel } from "@/components/mobile-result-panel";
import { OrchestratorChatDrawer } from "@/components/orchestrator-chat-drawer";
import { TaskFlowMonitor } from "@/components/task-flow-monitor";
import type { OrchestratorChatMessage } from "@/components/orchestrator-chat-drawer";

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

export default function Home() {
  const router = useRouter();
  const { user } = useAuth();

  /** Only true after token validated with backend (avoids 401 + WS close on stale token). */
  const [authValidated, setAuthValidated] = useState(false);
  const lastValidatedTokenRef = useRef<string | null>(null);
  const [thread, setThread] = useState<Thread | null>(null);
  const [threadList, setThreadList] = useState<ThreadSummary[]>([]);
  const [pipeline, setPipeline] = useState<PipelineType>("auto");
  const [lastError, setLastError] = useState<string | null>(null);
  const [orchestratorChatOpen, setOrchestratorChatOpen] = useState(false);
  const [orchestratorChatMessages, setOrchestratorChatMessages] = useState<
    OrchestratorChatMessage[]
  >([]);
  // Mobile state
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState<"chat" | "monitor">("chat");
  const [rightTab, setRightTab] = useState<
    | "monitor"
    | "insights"
    | "memory"
    | "evolution"
    | "coordination"
    | "ecosystem"
    | "autonomous"
  >("monitor");
  const toast = useToast();

  const { status, liveEvents, sendMessage, sendOrchestratorChat, stop } =
    useAgentSocket({
      enabled: !!user && authValidated,
      onResult: (_tid, _result, updatedThread) => {
        setThread(updatedThread);
        setLastError(null);
        loadThreadList();
      },
      onError: (msg) => setLastError(msg),
      onOrchestratorChatReply: (content) => {
        setOrchestratorChatMessages((prev) => [
          ...prev,
          { role: "assistant", content },
        ]);
      },
    });

  const loadThreadList = useCallback(async () => {
    try {
      const list = await api.listThreads();
      setThreadList(list);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Thread listesi yüklenemedi";
      setLastError(msg);
      // 401: clearAuthOn401 already ran; page will redirect when user becomes null
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

    // Avoid repeated /api/auth/me calls for the same token during the same browser session.
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

    // Validate token before opening WS / loading threads (avoids 401 + "WS closed before connect")
    let cancelled = false;

    const validate = async () => {
      try {
        await api.me();
      } catch {
        // Retry once for transient auth races (seen during concurrent websocket/chat interactions).
        await new Promise((resolve) => setTimeout(resolve, 350));
        await api.me();
      }

      if (cancelled) return;
      lastValidatedTokenRef.current = token;
      if (typeof window !== "undefined") {
        sessionStorage.setItem(sessionKey, token);
      }
      setAuthValidated(true);
    };

    validate().catch(() => {
      if (!cancelled) setAuthValidated(false);
      // clearAuthOn401 already ran; user will become null and redirect
    });

    return () => {
      cancelled = true;
    };
  }, [router, user]);

  useEffect(() => {
    if (authValidated && user) loadThreadList();
  }, [authValidated, loadThreadList, user]);

  if (!user) return null;

  // Wait for token validation so we don't open WS or hit /api/threads with stale token
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
    setMobileTab("chat");
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

  const handleOrchestratorChatSend = (message: string) => {
    setOrchestratorChatMessages((prev) => [
      ...prev,
      { role: "user", content: message },
    ]);
    sendOrchestratorChat(message, thread?.id ?? undefined);
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
        className={`
          fixed inset-y-0 left-0 z-50 w-72 flex flex-col transform transition-transform duration-200 ease-out
          lg:relative lg:translate-x-0 lg:z-auto
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
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

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0" id="main-content">
        <CockpitHeader onMenuToggle={() => setSidebarOpen(true)} />
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex-1 min-w-0">
            <PipelineSelector selected={pipeline} onSelect={setPipeline} />
          </div>
          <button
            type="button"
            onClick={() => setOrchestratorChatOpen(true)}
            className="ml-auto flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-border/50 hover:border-border transition-colors"
            aria-label="Orkestratörle sohbet aç"
          >
            Orkestratör sohbet
          </button>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* Center: Chat + Pipeline flow */}
          <div
            className={`
              flex-1 flex flex-col min-w-0 lg:border-r lg:border-border
              ${mobileTab !== "chat" ? "hidden lg:flex" : "flex"}
            `}
          >
            <ChatArea
              thread={thread}
              isProcessing={isProcessing}
              status={status}
            />

            {/* Desktop: export buttons + history (no pipeline agent cards) */}
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

            {/* Mobile: collapsible result panel */}
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

          {/* Right panel: Dinamik görev akışı monitörü */}
          <div
            className={`
              w-full lg:w-[26rem] lg:shrink-0 flex flex-col min-h-0
              ${mobileTab === "monitor" ? "flex" : "hidden lg:flex"}
            `}
          >
            {/* Tab switcher */}
            <div className="flex border-b border-border shrink-0">
              {[
                {
                  key: "monitor" as const,
                  label: "Görev",
                  active:
                    "text-blue-400 border-b-2 border-blue-400 bg-blue-400/5",
                },
                {
                  key: "insights" as const,
                  label: "Sistem",
                  active:
                    "text-emerald-400 border-b-2 border-emerald-400 bg-emerald-400/5",
                },
                {
                  key: "memory" as const,
                  label: "Bellek",
                  active:
                    "text-purple-400 border-b-2 border-purple-400 bg-purple-400/5",
                },
                {
                  key: "evolution" as const,
                  label: "Gelişim",
                  active:
                    "text-amber-400 border-b-2 border-amber-400 bg-amber-400/5",
                },
                {
                  key: "coordination" as const,
                  label: "Koordinasyon",
                  active:
                    "text-pink-400 border-b-2 border-pink-400 bg-pink-400/5",
                },
                {
                  key: "ecosystem" as const,
                  label: "Ekosistem",
                  active:
                    "text-cyan-400 border-b-2 border-cyan-400 bg-cyan-400/5",
                },
                {
                  key: "autonomous" as const,
                  label: "Özerk",
                  active:
                    "text-rose-400 border-b-2 border-rose-400 bg-rose-400/5",
                },
              ].map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setRightTab(tab.key)}
                  className={`flex-1 px-2 py-2 text-[11px] font-medium transition-colors ${
                    rightTab === tab.key
                      ? tab.active
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {rightTab === "monitor" ? (
              <TaskFlowMonitor thread={thread} liveEvents={liveEvents} />
            ) : rightTab === "insights" ? (
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                <SystemStatsPanel />
                <AgentHealthPanel />
                <AnomalyPanel />
                <LeaderboardPanel />
              </div>
            ) : rightTab === "memory" ? (
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                <MemoryTimelinePanel />
                <MemoryCorrelationPanel />
              </div>
            ) : rightTab === "coordination" ? (
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                <CoordinationPanel />
              </div>
            ) : rightTab === "ecosystem" ? (
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                <AgentEcosystemMap />
              </div>
            ) : rightTab === "autonomous" ? (
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                <AutonomousEvolutionPanel />
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                <AgentEvolutionPanel />
              </div>
            )}
          </div>
        </div>

        {/* Mobile bottom navigation */}
        <MobileNav
          activeTab={mobileTab}
          onTabChange={setMobileTab}
          isProcessing={isProcessing}
          liveEventCount={liveEvents.length}
        />

        <OrchestratorChatDrawer
          isOpen={orchestratorChatOpen}
          onClose={() => setOrchestratorChatOpen(false)}
          messages={orchestratorChatMessages}
          onSend={handleOrchestratorChatSend}
          threadId={thread?.id}
          isProcessing={isProcessing}
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
