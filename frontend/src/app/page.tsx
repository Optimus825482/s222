"use client";

import { useCallback, useEffect, useState } from "react";
import { useAgentSocket } from "@/lib/use-agent-socket";
import { api } from "@/lib/api";
import type { Thread, ThreadSummary, PipelineType } from "@/lib/types";
import { Sidebar } from "@/components/sidebar";
import { CockpitHeader } from "@/components/cockpit-header";
import { PipelineSelector } from "@/components/pipeline-selector";
import { ChatArea } from "@/components/chat-area";
import { ActivityStream } from "@/components/activity-stream";
import { ChatInput } from "@/components/chat-input";
import { LiveEventLog } from "@/components/live-event-log";
import { PipelineFlow } from "@/components/pipeline-flow";
import { TaskHistory } from "@/components/task-history";
import { ExportButtons } from "@/components/export-buttons";
import { InterAgentChat } from "@/components/inter-agent-chat";
import { MobileNav } from "../components/mobile-nav";
import { MobileResultPanel } from "../components/mobile-result-panel";

export default function Home() {
  const [thread, setThread] = useState<Thread | null>(null);
  const [threadList, setThreadList] = useState<ThreadSummary[]>([]);
  const [pipeline, setPipeline] = useState<PipelineType>("auto");
  const [lastError, setLastError] = useState<string | null>(null);
  // Mobile state
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState<"chat" | "activity" | "agents">(
    "chat",
  );

  const { status, liveEvents, sendMessage, stop } = useAgentSocket({
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
    } catch {
      /* backend might not be running yet */
    }
  }, []);

  useEffect(() => {
    loadThreadList();
  }, [loadThreadList]);

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
      /* ignore */
    }
  };

  const handleDeleteThread = async (id: string) => {
    try {
      await api.deleteThread(id);
      if (thread?.id === id) setThread(null);
      loadThreadList();
    } catch {
      /* ignore */
    }
  };

  const handleDeleteAllThreads = async () => {
    try {
      await api.deleteAllThreads();
      setThread(null);
      loadThreadList();
    } catch {
      /* ignore */
    }
  };

  const isProcessing = status === "running" || status === "connecting";

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

      {/* Sidebar — hidden on mobile, drawer on tablet, fixed on desktop */}
      <div
        className={`
          fixed inset-y-0 left-0 z-50 w-72 transform transition-transform duration-200 ease-out
          lg:relative lg:translate-x-0 lg:z-auto
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
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

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0" id="main-content">
        <CockpitHeader onMenuToggle={() => setSidebarOpen(true)} />
        <PipelineSelector selected={pipeline} onSelect={setPipeline} />

        <div className="flex-1 flex overflow-hidden">
          {/* Center: Chat + Pipeline flow */}
          <div
            className={`
              flex-1 flex flex-col min-w-0 lg:border-r lg:border-border
              ${mobileTab !== "chat" ? "hidden lg:flex" : "flex"}
            `}
          >
            <ChatArea thread={thread} />

            {/* Desktop: show all panels inline */}
            <div className="hidden lg:block">
              <PipelineFlow
                task={
                  thread?.tasks?.length
                    ? thread.tasks[thread.tasks.length - 1]
                    : null
                }
              />
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
                className="px-3 py-2 bg-red-950/50 border-t border-red-900/50 text-red-300 text-sm flex items-center justify-between"
                role="alert"
              >
                <span>{lastError}</span>
                <button
                  onClick={() => setLastError(null)}
                  className="text-red-400 hover:text-red-200 text-xs p-1 min-w-[44px] min-h-[44px] flex items-center justify-center"
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

          {/* Right panel: Activity stream + Inter-agent chat — hidden on mobile */}
          <div
            className={`
              w-full lg:w-72 lg:shrink-0 flex flex-col min-h-0
              ${mobileTab === "activity" ? "flex" : "hidden lg:flex"}
            `}
          >
            <div className="flex-1 overflow-y-auto border-b border-border">
              <ActivityStream thread={thread} liveEvents={liveEvents} />
            </div>
            <div className="flex-1 overflow-y-auto">
              <InterAgentChat thread={thread} liveEvents={liveEvents} />
            </div>
          </div>

          {/* Mobile agents tab */}
          <div
            className={`
              w-full flex flex-col min-h-0
              ${mobileTab === "agents" ? "flex lg:hidden" : "hidden"}
            `}
          >
            <div className="flex-1 overflow-y-auto p-3">
              <ActivityStream thread={thread} liveEvents={liveEvents} />
            </div>
          </div>
        </div>

        {/* Mobile bottom navigation */}
        <MobileNav
          activeTab={mobileTab}
          onTabChange={setMobileTab}
          isProcessing={isProcessing}
          liveEventCount={liveEvents.length}
        />
      </main>
    </div>
  );
}
