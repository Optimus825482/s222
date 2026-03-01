"use client";

import { useEffect, useRef, useState } from "react";
import type { Thread, WSLiveEvent, AgentEvent } from "@/lib/types";
import { getAgentInfo } from "@/lib/agents";
import {
  MessageSquare,
  Brain,
  Microscope,
  Zap,
  Search,
  Waves,
  Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { DetailModal } from "./detail-modal";

const INTER_AGENT_EVENTS = new Set([
  "routing_decision",
  "agent_start",
  "agent_thinking",
  "synthesis",
  "pipeline_step",
]);

const AGENT_ROLE_ICONS: Record<string, LucideIcon> = {
  orchestrator: Brain,
  thinker: Microscope,
  speed: Zap,
  researcher: Search,
  reasoner: Waves,
};

interface Props {
  thread: Thread | null;
  liveEvents: WSLiveEvent[];
}

export function InterAgentChat({ thread, liveEvents }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [selectedEvent, setSelectedEvent] = useState<{
    title: string;
    content: string;
    color?: string;
    badge?: string;
  } | null>(null);

  const interEvents = (thread?.events ?? []).filter((e) =>
    INTER_AGENT_EVENTS.has(e.event_type),
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [interEvents.length, liveEvents.length]);

  const liveInterAgent = liveEvents.filter((ev) =>
    INTER_AGENT_EVENTS.has(ev.event_type),
  );

  return (
    <div
      className="h-full flex flex-col"
      aria-label="Agent konuşmaları"
      role="region"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 lg:px-4 py-3 border-b border-border">
        <MessageSquare className="w-4 h-4 text-slate-300" aria-hidden="true" />
        <span className="text-xs lg:text-sm font-semibold text-slate-200">
          Agent Konuşmaları
        </span>
        <span className="ml-auto text-[10px] text-slate-500">
          {interEvents.length + liveInterAgent.length} mesaj
        </span>
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto px-3 py-2 space-y-2"
        role="log"
        aria-live="polite"
        aria-label="Agent mesajları"
      >
        {interEvents.length === 0 && liveInterAgent.length === 0 && (
          <div className="text-center text-xs text-slate-600 py-8">
            Agent iletişimi bekleniyor...
          </div>
        )}

        {/* Historical */}
        {interEvents.map((ev) => {
          const role = ev.agent_role ?? "orchestrator";
          const info = getAgentInfo(role);
          return (
            <AgentMessage
              key={ev.id}
              event={ev}
              onClick={() =>
                setSelectedEvent({
                  title: `${info.name} — ${ev.event_type}`,
                  content: ev.content,
                  color: info.color,
                })
              }
            />
          );
        })}

        {/* Live */}
        {liveInterAgent.map((ev, i) => {
          const info = getAgentInfo(ev.agent);
          return (
            <LiveAgentMessage
              key={`live-${i}`}
              event={ev}
              onClick={() =>
                setSelectedEvent({
                  title: `${info.name} — ${ev.event_type}`,
                  content: ev.content,
                  color: info.color,
                  badge: "LIVE",
                })
              }
            />
          );
        })}

        <div ref={bottomRef} />
      </div>

      {selectedEvent && (
        <DetailModal
          title={selectedEvent.title}
          content={selectedEvent.content}
          color={selectedEvent.color}
          badge={selectedEvent.badge}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  );
}

const LABEL_MAP: Record<string, string> = {
  routing_decision: "Yönlendirme",
  agent_start: "Başladı",
  agent_thinking: "Düşünüyor",
  synthesis: "Sentez",
  pipeline_step: "Adım",
};

function AgentMessage({
  event,
  onClick,
}: {
  event: AgentEvent;
  onClick: () => void;
}) {
  const role = event.agent_role ?? "orchestrator";
  const info = getAgentInfo(role);
  const isOrchestrator = role === "orchestrator";
  const RoleIcon = AGENT_ROLE_ICONS[role] ?? Settings;

  return (
    <button
      onClick={onClick}
      className={`w-full flex gap-2 animate-fade-in text-left hover:bg-white/5 rounded-lg p-1 transition-colors cursor-pointer ${isOrchestrator ? "" : "pl-4"}`}
    >
      <div className="flex-shrink-0 mt-1">
        <div
          className="min-w-[28px] min-h-[28px] w-7 h-7 rounded-full flex items-center justify-center"
          style={{ backgroundColor: info.color + "20", color: info.color }}
          aria-hidden="true"
        >
          <RoleIcon className="w-3.5 h-3.5" />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span
            className="text-[11px] font-semibold"
            style={{ color: info.color }}
          >
            {info.name}
          </span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-overlay text-slate-500">
            {LABEL_MAP[event.event_type] ?? event.event_type}
          </span>
        </div>
        <div className="text-[11px] text-slate-400 leading-snug whitespace-pre-wrap break-words line-clamp-3">
          {event.content.slice(0, 300)}
        </div>
      </div>
    </button>
  );
}

function LiveAgentMessage({
  event,
  onClick,
}: {
  event: WSLiveEvent;
  onClick: () => void;
}) {
  const info = getAgentInfo(event.agent);
  const RoleIcon = AGENT_ROLE_ICONS[event.agent] ?? Settings;

  return (
    <button
      onClick={onClick}
      className="w-full flex gap-2 animate-slide-up pl-2 text-left hover:bg-white/5 rounded-lg p-1 transition-colors cursor-pointer"
    >
      <div className="flex-shrink-0 mt-1">
        <div
          className="min-w-[28px] min-h-[28px] w-7 h-7 rounded-full flex items-center justify-center ring-1 ring-blue-500/30"
          style={{ backgroundColor: info.color + "20", color: info.color }}
          aria-hidden="true"
        >
          <RoleIcon className="w-3.5 h-3.5" />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span
            className="text-[11px] font-semibold"
            style={{ color: info.color }}
          >
            {info.name}
          </span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-950/40 text-blue-400 animate-pulse">
            LIVE
          </span>
        </div>
        <div className="text-[11px] text-slate-300 leading-snug whitespace-pre-wrap break-words line-clamp-3">
          {event.content.slice(0, 300)}
        </div>
      </div>
    </button>
  );
}
