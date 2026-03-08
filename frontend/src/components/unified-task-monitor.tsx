"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import { getWSSnapshot, subscribeWS } from "@/lib/ws-store";
import { LiveEventLog } from "./live-event-log";
import { AgentProgressTrackerPanel } from "./agent-progress-tracker-panel";
import { TaskFlowMonitor } from "./task-flow-monitor";
import {
  AgentHealthPanel,
  SystemStatsPanel,
  AnomalyPanel,
  HeartbeatPanel,
} from "./monitoring-panels";
import { Radio, ListChecks, Users, Cpu, Activity } from "lucide-react";

type TabId = "live" | "tasks" | "agents" | "system";

interface TabDef {
  id: TabId;
  label: string;
  icon: typeof Radio;
}

const TABS: TabDef[] = [
  { id: "live", label: "Canlı Akış", icon: Radio },
  { id: "tasks", label: "Görev Detayı", icon: ListChecks },
  { id: "agents", label: "Agent Durumu", icon: Users },
  { id: "system", label: "Sistem", icon: Cpu },
];

export function UnifiedTaskMonitor() {
  const [activeTab, setActiveTab] = useState<TabId>("live");
  const snapshot = useSyncExternalStore(
    subscribeWS,
    getWSSnapshot,
    getWSSnapshot,
  );
  const { status, liveEvents, activeThread } = snapshot;

  const isActive = status === "running";

  // Auto-switch to "live" tab when a task starts running
  useEffect(() => {
    if (status === "running") {
      setActiveTab("live");
    }
  }, [status]);

  // Listen for external tab-switch requests
  useEffect(() => {
    const handler = (e: Event) => {
      const tab = (e as CustomEvent<TabId>).detail;
      if (tab && TABS.some((t) => t.id === tab)) {
        setActiveTab(tab);
      }
    };
    window.addEventListener("task-monitor-tab", handler);
    return () => window.removeEventListener("task-monitor-tab", handler);
  }, []);

  return (
    <div className="flex flex-col h-full min-h-0 bg-white text-gray-900">
      {/* Tab bar */}
      <div className="flex items-center border-b border-[#d6d2c2] bg-[#ECE9D8] px-1 shrink-0">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] border border-transparent rounded-t transition-colors cursor-pointer"
              style={{
                fontFamily: "Tahoma, sans-serif",
                fontWeight: isSelected ? 600 : 400,
                background: isSelected ? "#fff" : "transparent",
                border: isSelected
                  ? "1px solid #d6d2c2"
                  : "1px solid transparent",
                borderBottom: isSelected
                  ? "1px solid #fff"
                  : "1px solid #d6d2c2",
                marginBottom: -1,
                color: isSelected ? "#000" : "#555",
              }}
            >
              <Icon className="w-3 h-3" />
              {tab.label}
            </button>
          );
        })}

        {/* Status indicator */}
        <div className="ml-auto flex items-center gap-1.5 pr-2">
          {isActive && (
            <Activity className="w-3 h-3 text-emerald-500 animate-pulse" />
          )}
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded ${
              isActive
                ? "bg-[#e6f5e6] text-[#339966]"
                : status === "connecting"
                  ? "bg-[#fff8e6] text-[#cc9900]"
                  : status === "error"
                    ? "bg-[#ffe6e6] text-[#cc3333]"
                    : status === "complete"
                      ? "bg-[#e6f5e6] text-[#339966]"
                      : "bg-gray-200 text-gray-500"
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
                    : "Bekleniyor"}
          </span>
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 min-h-0 overflow-auto">
        {activeTab === "live" && (
          <LiveTab events={liveEvents} status={status} />
        )}
        {activeTab === "tasks" && (
          <TasksTab thread={activeThread} liveEvents={liveEvents} />
        )}
        {activeTab === "agents" && <AgentsTab />}
        {activeTab === "system" && <SystemTab />}
      </div>
    </div>
  );
}

/* ── Tab 1: Canlı Akış — live events + agent progress ── */
function LiveTab({
  events,
  status,
}: {
  events: ReturnType<typeof getWSSnapshot>["liveEvents"];
  status: string;
}) {
  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Agent progress tracker (top half) */}
      <div className="flex-1 min-h-0 overflow-auto border-b border-[#d6d2c2]">
        <AgentProgressTrackerPanel />
      </div>
      {/* Live event log (bottom half) */}
      <div className="flex-1 min-h-0 overflow-auto">
        {events.length > 0 ? (
          <LiveEventLog
            events={events}
            status={
              status as "idle" | "connecting" | "running" | "complete" | "error"
            }
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-500 px-6">
            <Radio className="w-6 h-6 text-gray-400/50" />
            <p className="text-xs text-center">
              Görev bekleniyor — sohbetten bir görev gönderin
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Tab 2: Görev Detayı — task decomposition from thread ── */
function TasksTab({
  thread,
  liveEvents,
}: {
  thread: ReturnType<typeof getWSSnapshot>["activeThread"];
  liveEvents: ReturnType<typeof getWSSnapshot>["liveEvents"];
}) {
  return (
    <div className="p-4 h-full min-h-0 flex flex-col">
      <TaskFlowMonitor thread={thread} liveEvents={liveEvents} />
    </div>
  );
}

/* ── Tab 3: Agent Durumu — health cards with real-time metrics ── */
function AgentsTab() {
  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <AgentHealthPanel />
    </div>
  );
}

/* ── Tab 4: Sistem — system stats, anomalies, heartbeat ── */
function SystemTab() {
  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <SystemStatsPanel />
      <AnomalyPanel />
      <HeartbeatPanel />
    </div>
  );
}
