"use client";

/* Collapsible mobile result panel */
import { useState } from "react";
import type { Thread, WSLiveEvent } from "@/lib/types";
import { PipelineFlow } from "@/components/pipeline-flow";
import { ExportButtons } from "@/components/export-buttons";
import { TaskHistory } from "@/components/task-history";
import { LiveEventLog } from "@/components/live-event-log";
import {
  ChevronUp,
  ChevronDown,
  GitBranch,
  Download,
  ClipboardList,
  Radio,
} from "lucide-react";

interface Props {
  thread: Thread | null;
  liveEvents: WSLiveEvent[];
  status: "idle" | "connecting" | "running" | "complete" | "error";
}

type PanelTab = "pipeline" | "export" | "history" | "live";

export function MobileResultPanel({ thread, liveEvents, status }: Props) {
  const [activeTab, setActiveTab] = useState<PanelTab | null>(null);

  const lastTask = thread?.tasks?.length
    ? thread.tasks[thread.tasks.length - 1]
    : null;

  const hasPipeline = lastTask && lastTask.sub_tasks.length > 0;
  const hasResult =
    lastTask?.final_result && lastTask.final_result.trim().length >= 10;
  const hasHistory = thread?.tasks && thread.tasks.length > 0;
  const hasLive = liveEvents.length > 0;

  // Nothing to show
  if (!hasPipeline && !hasResult && !hasHistory && !hasLive) return null;

  const tabs: {
    id: PanelTab;
    label: string;
    Icon: typeof GitBranch;
    show: boolean;
  }[] = [
    { id: "pipeline", label: "Akış", Icon: GitBranch, show: !!hasPipeline },
    { id: "export", label: "İndir", Icon: Download, show: !!hasResult },
    { id: "history", label: "Geçmiş", Icon: ClipboardList, show: !!hasHistory },
    { id: "live", label: "Canlı", Icon: Radio, show: hasLive },
  ];

  const visibleTabs = tabs.filter((t) => t.show);

  if (visibleTabs.length === 0) return null;

  const toggle = (tab: PanelTab) => {
    setActiveTab((prev) => (prev === tab ? null : tab));
  };

  return (
    <div className="border-t border-border bg-surface-raised/50">
      {/* Tab bar */}
      <div
        className="flex gap-1 px-3 py-1.5 overflow-x-auto scrollbar-none"
        role="tablist"
        aria-label="Sonuç detayları"
      >
        {visibleTabs.map(({ id, label, Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`mobile-panel-${id}`}
              onClick={() => toggle(id)}
              className={`
                flex items-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-medium
                min-h-[40px] shrink-0 cursor-pointer transition-all
                ${
                  isActive
                    ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                    : "bg-surface text-slate-500 hover:text-slate-300 border border-border"
                }
              `}
            >
              <Icon className="w-3.5 h-3.5" aria-hidden="true" />
              {label}
              {isActive ? (
                <ChevronUp className="w-3 h-3" aria-hidden="true" />
              ) : (
                <ChevronDown className="w-3 h-3" aria-hidden="true" />
              )}
            </button>
          );
        })}
      </div>

      {/* Panel content */}
      {activeTab === "pipeline" && hasPipeline && (
        <div
          id="mobile-panel-pipeline"
          role="tabpanel"
          className="animate-fade-in"
        >
          <PipelineFlow task={lastTask} />
        </div>
      )}

      {activeTab === "export" && hasResult && (
        <div
          id="mobile-panel-export"
          role="tabpanel"
          className="animate-fade-in"
        >
          <ExportButtons result={lastTask!.final_result!} task={lastTask} />
        </div>
      )}

      {activeTab === "history" && hasHistory && (
        <div
          id="mobile-panel-history"
          role="tabpanel"
          className="animate-fade-in"
        >
          <TaskHistory thread={thread} />
        </div>
      )}

      {activeTab === "live" && hasLive && (
        <div id="mobile-panel-live" role="tabpanel" className="animate-fade-in">
          <LiveEventLog events={liveEvents} status={status} />
        </div>
      )}
    </div>
  );
}
