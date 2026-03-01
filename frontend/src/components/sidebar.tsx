"use client";

import { useState, useMemo } from "react";
import { X, Trash2 } from "lucide-react";
import type {
  Thread,
  ThreadSummary,
  AgentRole,
  WSLiveEvent,
} from "@/lib/types";
import { AGENT_CONFIG } from "@/lib/agents";
import { formatNumber } from "@/lib/utils";
import {
  RagPanel,
  SkillsPanel,
  McpPanel,
  TeachabilityPanel,
  EvalPanel,
} from "./tools-panels";

interface SidebarProps {
  thread: Thread | null;
  threadList: ThreadSummary[];
  onNewThread: () => void;
  onLoadThread: (id: string) => void;
  onDeleteThread: (id: string) => void;
  onDeleteAllThreads: () => void;
  liveEvents?: WSLiveEvent[];
  isProcessing?: boolean;
  onClose?: () => void;
}

export function Sidebar({
  thread,
  threadList,
  onNewThread,
  onLoadThread,
  onDeleteThread,
  onDeleteAllThreads,
  liveEvents = [],
  isProcessing = false,
  onClose,
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<"agents" | "sessions" | "tools">(
    "agents",
  );

  const activeAgents = useMemo(() => {
    if (!isProcessing || liveEvents.length === 0) return new Set<string>();
    const agents = new Set<string>();
    const recent = liveEvents.slice(-50);
    for (const ev of recent) {
      if (ev.agent && ev.agent !== "system") agents.add(ev.agent);
    }
    return agents;
  }, [liveEvents, isProcessing]);

  return (
    <aside className="w-72 bg-surface-raised border-r border-border flex flex-col h-full shrink-0">
      {/* Logo + close button */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-xl" aria-hidden="true">
            🧠
          </span>
          <div>
            <div className="text-sm font-bold text-slate-200">
              Multi-Agent Ops
            </div>
            <div className="text-[10px] text-slate-500">Qwen Orchestrated</div>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="lg:hidden p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-surface-overlay transition-colors"
            aria-label="Menüyü kapat"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        )}
      </div>

      {/* Agent status dots */}
      <div className="flex justify-center gap-1.5 py-2 border-b border-border">
        {(
          Object.entries(AGENT_CONFIG) as [
            AgentRole,
            (typeof AGENT_CONFIG)[AgentRole],
          ][]
        ).map(([role, cfg]) => {
          const isLive = activeAgents.has(role);
          const metrics = thread?.agent_metrics?.[role];
          const isActive = isLive || (metrics && metrics.last_active);
          return (
            <div
              key={role}
              className={`flex items-center gap-0.5 px-2 py-1 rounded border text-xs min-h-[32px] ${isLive ? "animate-pulse" : ""}`}
              style={{
                borderColor: cfg.color,
                boxShadow: isActive ? `0 0 8px ${cfg.color}40` : undefined,
              }}
              title={cfg.name}
            >
              <span aria-hidden="true">{cfg.icon}</span>
              <span
                style={{ color: isActive ? "#10b981" : "#374151" }}
                aria-hidden="true"
              >
                ●
              </span>
            </div>
          );
        })}
      </div>

      {/* Tab switcher */}
      <div
        className="flex border-b border-border"
        role="tablist"
        aria-label="Sidebar sekmeleri"
      >
        {(["agents", "sessions", "tools"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            role="tab"
            aria-selected={activeTab === tab}
            className={`flex-1 py-3 text-xs font-medium transition-colors min-h-[44px] ${
              activeTab === tab
                ? "text-slate-200 border-b-2 border-blue-500"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab === "agents"
              ? "Agentlar"
              : tab === "sessions"
                ? "Oturumlar"
                : "Araçlar"}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2" role="tabpanel">
        {activeTab === "agents" && (
          <AgentCards
            thread={thread}
            activeAgents={activeAgents}
            isProcessing={isProcessing}
          />
        )}
        {activeTab === "sessions" && (
          <SessionList
            threadList={threadList}
            onNew={onNewThread}
            onLoad={onLoadThread}
            onDelete={onDeleteThread}
            onDeleteAll={onDeleteAllThreads}
          />
        )}
        {activeTab === "tools" && <ToolsPanel />}
      </div>

      {/* Metrics footer */}
      <MetricsFooter thread={thread} />
    </aside>
  );
}

function AgentCards({
  thread,
  activeAgents,
  isProcessing,
}: {
  thread: Thread | null;
  activeAgents: Set<string>;
  isProcessing: boolean;
}) {
  return (
    <div className="space-y-2">
      {(
        Object.entries(AGENT_CONFIG) as [
          AgentRole,
          (typeof AGENT_CONFIG)[AgentRole],
        ][]
      ).map(([role, cfg]) => {
        const m = thread?.agent_metrics?.[role];
        const isLive = activeAgents.has(role);
        const hasMetrics = m && m.total_calls > 0;

        let statusLabel: string;
        let statusColor: string;
        if (isLive) {
          statusLabel = "running";
          statusColor = "#10b981";
        } else if (isProcessing && hasMetrics) {
          statusLabel = "done";
          statusColor = "#f59e0b";
        } else if (hasMetrics) {
          statusLabel = "active";
          statusColor = "#10b981";
        } else {
          statusLabel = "idle";
          statusColor = "#6b7280";
        }

        return (
          <div
            key={role}
            className={`rounded-lg bg-surface p-3 border-l-2 transition-all ${isLive ? "ring-1 ring-emerald-500/30" : ""}`}
            style={{ borderColor: cfg.color }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`text-lg ${isLive ? "animate-pulse" : ""}`}
                  aria-hidden="true"
                >
                  {cfg.icon}
                </span>
                <span
                  className="text-xs font-semibold"
                  style={{ color: cfg.color }}
                >
                  {cfg.name}
                </span>
              </div>
              <span className="text-[10px]" style={{ color: statusColor }}>
                {statusLabel}
              </span>
            </div>
            <div className="flex gap-4 mt-2 text-[10px] text-slate-400">
              <div>
                <span className="text-slate-300 font-mono">
                  {m?.total_calls ?? 0}
                </span>{" "}
                calls
              </div>
              <div>
                <span className="text-slate-300 font-mono">
                  {formatNumber(m?.total_tokens ?? 0)}
                </span>{" "}
                tok
              </div>
              <div>
                <span className="text-slate-300 font-mono">
                  {m
                    ? Math.round(
                        m.total_latency_ms / Math.max(m.total_calls, 1),
                      )
                    : 0}
                  ms
                </span>{" "}
                avg
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SessionList({
  threadList,
  onNew,
  onLoad,
  onDelete,
  onDeleteAll,
}: {
  threadList: ThreadSummary[];
  onNew: () => void;
  onLoad: (id: string) => void;
  onDelete: (id: string) => void;
  onDeleteAll: () => void;
}) {
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);

  return (
    <div className="space-y-2">
      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={onNew}
          className="flex-1 py-3 rounded-lg bg-blue-600/20 text-blue-400 text-xs font-medium hover:bg-blue-600/30 transition-colors min-h-[44px]"
        >
          Yeni Oturum
        </button>
        {threadList.length > 0 && (
          <button
            onClick={() => {
              if (confirmDeleteAll) {
                onDeleteAll();
                setConfirmDeleteAll(false);
              } else {
                setConfirmDeleteAll(true);
                setTimeout(() => setConfirmDeleteAll(false), 3000);
              }
            }}
            className={`px-3 py-3 rounded-lg text-xs font-medium transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center ${
              confirmDeleteAll
                ? "bg-red-600/30 text-red-300"
                : "bg-red-950/30 text-red-400 hover:bg-red-950/50"
            }`}
            aria-label={confirmDeleteAll ? "Silmeyi onayla" : "Tümünü sil"}
            title={confirmDeleteAll ? "Emin misin? Tekrar tıkla" : "Tümünü sil"}
          >
            {confirmDeleteAll ? (
              <span className="text-[10px]">Emin?</span>
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* Thread list */}
      {threadList.map((t) => (
        <div
          key={t.id}
          className="group flex items-stretch rounded-lg bg-surface hover:bg-surface-overlay transition-colors border border-border"
        >
          <button
            onClick={() => onLoad(t.id)}
            className="flex-1 text-left p-3 min-h-[44px] min-w-0"
          >
            <div className="text-xs text-slate-300 truncate">
              {t.preview || "(boş)"}
            </div>
            <div className="text-[10px] text-slate-500 mt-1">
              {t.task_count} görev • {t.event_count} event
            </div>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(t.id);
            }}
            className="shrink-0 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity px-2.5 flex items-center justify-center text-red-400 hover:text-red-300 min-w-[36px]"
            aria-label="Oturumu sil"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
      {threadList.length === 0 && (
        <div className="text-center text-xs text-slate-500 py-4">
          Kayıtlı oturum yok
        </div>
      )}
    </div>
  );
}

function ToolsPanel() {
  return (
    <div className="space-y-4">
      <RagPanel />
      <hr className="border-border" />
      <SkillsPanel />
      <hr className="border-border" />
      <McpPanel />
      <hr className="border-border" />
      <TeachabilityPanel />
      <hr className="border-border" />
      <EvalPanel />
    </div>
  );
}

function MetricsFooter({ thread }: { thread: Thread | null }) {
  let calls = 0,
    tokens = 0,
    errors = 0;
  if (thread?.agent_metrics) {
    Object.values(thread.agent_metrics).forEach((m) => {
      calls += m.total_calls;
      tokens += m.total_tokens;
      errors += m.error_count;
    });
  }
  return (
    <div className="border-t border-border p-3 grid grid-cols-3 gap-2 text-center">
      <div>
        <div className="text-xs font-mono text-blue-400">{calls}</div>
        <div className="text-[9px] text-slate-500">Calls</div>
      </div>
      <div>
        <div className="text-xs font-mono text-slate-300">
          {formatNumber(tokens)}
        </div>
        <div className="text-[9px] text-slate-500">Tokens</div>
      </div>
      <div>
        <div
          className={`text-xs font-mono ${errors > 0 ? "text-red-400" : "text-green-400"}`}
        >
          {errors}
        </div>
        <div className="text-[9px] text-slate-500">Errors</div>
      </div>
    </div>
  );
}
