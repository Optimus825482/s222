"use client";

import { useState } from "react";
import type { Thread, WSLiveEvent } from "@/lib/types";
import { getAgentInfo, EVENT_ICONS } from "@/lib/agents";
import {
  Activity,
  Wrench,
  Bot,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  Zap,
  Pin,
  Compass,
  Rocket,
  MessageCircle,
  ClipboardList,
  Link,
  Play,
  FastForward,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { DetailModal } from "./detail-modal";

const ACTIVITY_EVENTS = new Set([
  "routing_decision",
  "agent_start",
  "agent_thinking",
  "tool_call",
  "tool_result",
  "pipeline_start",
  "pipeline_step",
  "pipeline_complete",
  "synthesis",
  "error",
]);

const EVENT_LUCIDE: Record<string, LucideIcon> = {
  routing_decision: Compass,
  agent_start: Rocket,
  agent_thinking: MessageCircle,
  tool_call: Wrench,
  tool_result: ClipboardList,
  pipeline_start: Play,
  pipeline_step: FastForward,
  pipeline_complete: CheckCircle,
  synthesis: Link,
  error: AlertTriangle,
};

interface Props {
  thread: Thread | null;
  liveEvents: WSLiveEvent[];
}

interface ModalData {
  title: string;
  content: string;
  color?: string;
  badge?: string;
}

export function ActivityStream({ thread, liveEvents }: Props) {
  const [selected, setSelected] = useState<ModalData | null>(null);

  const threadEvents = (thread?.events ?? []).filter((e) =>
    ACTIVITY_EVENTS.has(e.event_type),
  );
  const toolCount = threadEvents.filter(
    (e) => e.event_type === "tool_call",
  ).length;
  const agentSet = new Set(
    threadEvents.map((e) => e.agent_role).filter(Boolean),
  );
  const errorCount = threadEvents.filter(
    (e) => e.event_type === "error",
  ).length;

  return (
    <div
      className="h-full flex flex-col"
      aria-label="Aktivite akışı"
      role="region"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 lg:px-4 py-3 border-b border-border">
        <Activity className="w-4 h-4 text-slate-300" aria-hidden="true" />
        <span className="text-xs lg:text-sm font-semibold text-slate-200">
          Activity Stream
        </span>
      </div>

      {/* Stats bar */}
      <div
        className="flex gap-3 px-3 lg:px-4 py-2 text-[10px] text-slate-400 border-b border-border"
        aria-label="Aktivite istatistikleri"
      >
        <span className="inline-flex items-center gap-1">
          <Wrench className="w-3 h-3" aria-hidden="true" /> {toolCount}
        </span>
        <span className="inline-flex items-center gap-1">
          <Bot className="w-3 h-3" aria-hidden="true" /> {agentSet.size}
        </span>
        <span className="inline-flex items-center gap-1">
          {errorCount > 0 ? (
            <>
              <AlertTriangle className="w-3 h-3" aria-hidden="true" />{" "}
              {errorCount}
            </>
          ) : (
            <>
              <CheckCircle className="w-3 h-3" aria-hidden="true" />0
            </>
          )}
        </span>
        <span className="inline-flex items-center gap-1">
          <BarChart3 className="w-3 h-3" aria-hidden="true" />{" "}
          {threadEvents.length}
        </span>
      </div>

      {/* Live events */}
      {liveEvents.length > 0 && (
        <div className="px-3 py-2 border-b border-blue-900/30 bg-blue-950/20">
          <div className="text-[10px] text-blue-400 font-medium mb-1 inline-flex items-center gap-1">
            <Zap className="w-3 h-3" aria-hidden="true" /> LIVE
          </div>
          {liveEvents.slice(-10).map((ev, i) => {
            const info = getAgentInfo(ev.agent);
            const AgentIcon = EVENT_LUCIDE[ev.event_type];
            return (
              <button
                key={i}
                onClick={() =>
                  setSelected({
                    title: `${ev.agent} — ${ev.event_type}`,
                    content: ev.content,
                    color: info.color,
                    badge: "LIVE",
                  })
                }
                className="w-full flex items-start gap-1.5 py-0.5 text-[11px] animate-fade-in hover:bg-white/5 transition-colors cursor-pointer text-left rounded"
              >
                {AgentIcon ? (
                  <AgentIcon
                    className="w-3 h-3 flex-shrink-0 mt-0.5"
                    style={{ color: info.color }}
                    aria-hidden="true"
                  />
                ) : (
                  <Pin
                    className="w-3 h-3 flex-shrink-0 mt-0.5 text-slate-500"
                    aria-hidden="true"
                  />
                )}
                <span className="text-slate-400 truncate">
                  {ev.content.slice(0, 100)}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Thread events */}
      <div
        className="flex-1 overflow-y-auto px-3 py-2 space-y-1"
        role="log"
        aria-live="polite"
        aria-label="Aktivite olayları"
      >
        {threadEvents.length === 0 && liveEvents.length === 0 && (
          <div className="text-center text-xs text-slate-600 py-8">
            Agent aktivitesi bekleniyor...
          </div>
        )}
        {[...threadEvents]
          .reverse()
          .slice(0, 30)
          .map((ev) => {
            const evCfg = EVENT_ICONS[ev.event_type] ?? {
              icon: "",
              label: "Event",
              color: "#6b7280",
            };
            const EvIcon = EVENT_LUCIDE[ev.event_type] ?? Pin;
            const info = getAgentInfo(ev.agent_role ?? "");
            return (
              <button
                key={ev.id}
                onClick={() =>
                  setSelected({
                    title: `${info.name} — ${evCfg.label}`,
                    content: ev.content,
                    color: evCfg.color,
                  })
                }
                className="w-full rounded-lg p-2 text-[11px] border-l-2 bg-surface hover:bg-white/5 transition-colors cursor-pointer text-left"
                style={{ borderColor: evCfg.color }}
              >
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1">
                    <EvIcon
                      className="w-3 h-3"
                      style={{ color: evCfg.color }}
                      aria-hidden="true"
                    />
                    <span
                      className="font-semibold"
                      style={{ color: evCfg.color }}
                    >
                      {evCfg.label}
                    </span>
                  </span>
                  <span
                    className="text-[10px] font-medium"
                    style={{ color: info.color }}
                  >
                    {info.name}
                  </span>
                </div>
                <div className="text-slate-400 mt-0.5 leading-snug truncate">
                  {ev.content.slice(0, 160)}
                </div>
              </button>
            );
          })}
      </div>

      {selected && (
        <DetailModal
          title={selected.title}
          content={selected.content}
          color={selected.color}
          badge={selected.badge}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
