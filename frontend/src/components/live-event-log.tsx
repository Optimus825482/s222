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

  if (events.length === 0) return null;

  const statusCfg = STATUS_ICONS[status];

  const statusLabel = statusCfg
    ? `${statusCfg.label} (${events.length} adım)`
    : `Son çalışma (${events.length} adım)`;

  const StatusIcon = statusCfg?.Icon ?? BarChart3;

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
              <div
                key={i}
                className="flex items-center gap-1.5 text-[11px] text-slate-500 py-0.5 border-b border-border/50"
              >
                <EvIcon className="w-3 h-3 flex-shrink-0" aria-hidden="true" />
                <span
                  className="text-[10px] font-medium flex-shrink-0"
                  style={{ color: info.color }}
                >
                  {ev.agent}
                </span>
                <span className="truncate break-words">
                  {ev.content.slice(0, 100)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
