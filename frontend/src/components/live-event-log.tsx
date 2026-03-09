"use client";

import { useMemo, useState } from "react";
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
  final_report: CheckCircle,
};

export function LiveEventLog({ events, status }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [showFullReport, setShowFullReport] = useState(false);

  const keyedEvents = useMemo(
    () =>
      events.map((event) => ({
        event,
        key:
          event.logKey ??
          `${event.timestamp}:${event.agent}:${event.event_type}:${event.content.slice(0, 32)}`,
      })),
    [events],
  );

  const agentInfoByKey = useMemo(
    () =>
      new Map(
        keyedEvents.map(({ event, key }) => [key, getAgentInfo(event.agent)]),
      ),
    [keyedEvents],
  );

  // Find the final_report event (emitted by backend when pipeline completes)
  const finalReportContent = useMemo(() => {
    for (let i = keyedEvents.length - 1; i >= 0; i--) {
      const ev = keyedEvents[i].event;
      if (ev.event_type === "final_report") {
        return ev.content;
      }
    }
    return undefined;
  }, [keyedEvents]);

  const statusCfg = STATUS_ICONS[status];
  const showEmptyStatus =
    events.length === 0 && (status === "connecting" || status === "running");

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
    ? `${statusCfg.label} (${keyedEvents.length} adım)`
    : `Son çalışma (${keyedEvents.length} adım)`;
  const StatusIcon = statusCfg?.Icon ?? BarChart3;

  // For modal: get selected event (tracks live updates)
  const selectedEvent =
    selectedIdx !== null ? (keyedEvents[selectedIdx]?.event ?? null) : null;

  // Find the latest confidence_analysis event for the selected event's agent
  const confidenceForSelected = useMemo(() => {
    if (!selectedEvent) return undefined;
    for (let i = keyedEvents.length - 1; i >= 0; i--) {
      const ev = keyedEvents[i].event;
      if (ev.event_type === "confidence_analysis") {
        return ev.content;
      }
    }
    return undefined;
  }, [selectedEvent, keyedEvents]);

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
        <span className="inline-flex items-center gap-2">
          {status === "complete" && finalReportContent && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
                setShowFullReport(true);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.stopPropagation();
                  setShowFullReport(true);
                }
              }}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-900/40 text-emerald-400 hover:bg-emerald-900/60 transition-colors text-[10px] font-medium border border-emerald-800/30"
            >
              <CheckCircle className="w-3 h-3" aria-hidden="true" />
              Tam Rapor
            </span>
          )}
          <span aria-hidden="true">
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </span>
        </span>
      </button>
      {expanded && (
        <div
          id="live-event-log-content"
          className="max-h-48 overflow-y-auto px-3 lg:px-4 pb-2 space-y-0.5"
          role="log"
          aria-live="polite"
        >
          {keyedEvents.map(({ event: ev, key }, i) => {
            const info = agentInfoByKey.get(key) ?? getAgentInfo(ev.agent);
            const EvIcon = TYPE_ICONS[ev.event_type] ?? Pin;
            return (
              <button
                key={key}
                onClick={() => setSelectedIdx(i)}
                className="w-full flex items-start gap-1.5 text-[11px] text-slate-500 py-1.5 px-0.5 border-b border-border/50 hover:bg-white/5 transition-colors cursor-pointer text-left"
              >
                <EvIcon
                  className="w-3 h-3 flex-shrink-0 mt-0.5"
                  aria-hidden="true"
                />
                <div className="flex-1 min-w-0">
                  <span
                    className="text-[10px] font-medium flex-shrink-0"
                    style={{ color: info.color }}
                  >
                    {ev.agent}
                  </span>
                  <span className="block text-slate-400 break-words mt-0.5">
                    {ev.content.slice(0, 200)}
                    {ev.content.length > 200 ? "…" : ""}
                  </span>
                </div>
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
          confidenceAnalysis={confidenceForSelected}
          onClose={() => setSelectedIdx(null)}
        />
      )}

      {showFullReport && finalReportContent && (
        <DetailModal
          title="Tam Rapor — Sentez Sonucu"
          content={finalReportContent}
          color="#10b981"
          badge="SONUÇ"
          onClose={() => setShowFullReport(false)}
        />
      )}
    </div>
  );
}
