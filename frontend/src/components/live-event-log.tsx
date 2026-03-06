"use client";

import { useState } from "react";
import type { WSLiveEvent } from "@/lib/types";
import { getAgentInfo } from "@/lib/agents";
import {
  BarChart3,
  RefreshCw,
  Settings,
  CheckCircle,
  XCircle,
  Rocket,
  Wrench,
  ClipboardList,
  MessageCircle,
  MessageSquare,
  Compass,
  AlertTriangle,
  Pin,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { DetailModal } from "./detail-modal";

interface Props {
  events: WSLiveEvent[];
  status: "idle" | "connecting" | "running" | "complete" | "error";
}

const STATUS_ICONS: Record<string, { Icon: LucideIcon; label: string }> = {
  connecting: { Icon: RefreshCw, label: "Bağlanıyor..." },
  running: { Icon: Settings, label: "İşleniyor" },
  complete: { Icon: CheckCircle, label: "Tamamlandı" },
  error: { Icon: XCircle, label: "Hata" },
};

const TYPE_ICONS: Record<string, LucideIcon> = {
  agent_start: Rocket,
  tool_call: Wrench,
  tool_result: ClipboardList,
  thinking: MessageCircle,
  response: MessageSquare,
  pipeline: RefreshCw,
  routing: Compass,
  error: AlertTriangle,
};

export function LiveEventLog({ events, status }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const statusCfg = STATUS_ICONS[status];
  const showEmptyStatus =
    events.length === 0 &&
    (status === "connecting" || status === "running");

  if (events.length === 0 && !showEmptyStatus) return null;

  if (showEmptyStatus) {
    const label = status === "connecting" ? "Bağlanıyor..." : "İşleniyor...";
    const Icon = statusCfg?.Icon ?? RefreshCw;
    return (
      <div
        className="border-t border-border px-3 py-2 flex items-center gap-2 text-xs text-slate-500"
        role="status"
        aria-live="polite"
      >
        <Icon
          className={`w-3.5 h-3.5 shrink-0 ${status === "connecting" ? "animate-spin" : ""}`}
          aria-hidden
        />
        {label}
      </div>
    );
  }

  const statusLabel = statusCfg
    ? `${statusCfg.label} (${events.length} adım)`
    : `Son çalışma (${events.length} adım)`;
  const StatusIcon = statusCfg?.Icon ?? BarChart3;

  // For modal: get selected event (tracks live updates)
  const selectedEvent = selectedIdx !== null ? events[selectedIdx] : null;

  return (
    <div
      className="border-t border-border"
      aria-label="Canlı olay günlüğü"
      role="region"
    >
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls="live-event-log-content"
        className="w-full flex items-center justify-between px-3 lg:px-4 py-2 min-h-[44px] text-xs text-slate-400 hover:text-slate-300 transition-colors cursor-pointer"
      >
        <span className="inline-flex items-center gap-1.5">
          <StatusIcon className="w-3 h-3" aria-hidden="true" />
          {statusLabel}
        </span>
        <span aria-hidden="true">
          {expanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </span>
      </button>
      {expanded && (
        <div
          id="live-event-log-content"
          className="max-h-48 overflow-y-auto px-3 lg:px-4 pb-2 space-y-0.5"
          role="log"
          aria-live="polite"
        >
          {events.map((ev, i) => {
            const info = getAgentInfo(ev.agent);
            const EvIcon = TYPE_ICONS[ev.event_type] ?? Pin;
            return (
              <button
                key={i}
                onClick={() => setSelectedIdx(i)}
                className="w-full flex items-center gap-1.5 text-[11px] text-slate-500 py-0.5 border-b border-border/50 hover:bg-white/5 transition-colors cursor-pointer text-left"
              >
                <EvIcon className="w-3 h-3 flex-shrink-0" aria-hidden="true" />
                <span
                  className="text-[10px] font-medium flex-shrink-0"
                  style={{ color: info.color }}
                >
                  {ev.agent}
                </span>
                <span className="truncate">{ev.content.slice(0, 100)}</span>
              </button>
            );
          })}
        </div>
      )}

      {selectedEvent && (
        <DetailModal
          title={`${selectedEvent.agent} — ${selectedEvent.event_type}`}
          content={selectedEvent.content}
          color={getAgentInfo(selectedEvent.agent).color}
          badge={status === "running" ? "LIVE" : undefined}
          onClose={() => setSelectedIdx(null)}
        />
      )}
    </div>
  );
}
