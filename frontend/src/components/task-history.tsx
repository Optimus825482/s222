"use client";

import { useState } from "react";
import type { Thread, Task } from "@/lib/types";
import {
  CheckCircle,
  XCircle,
  Settings,
  Clock,
  RefreshCw,
  Eye,
  ClipboardList,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const STATUS_CFG: Record<string, { Icon: LucideIcon; color: string }> = {
  completed: { Icon: CheckCircle, color: "#10b981" },
  failed: { Icon: XCircle, color: "#ef4444" },
  running: { Icon: Settings, color: "#3b82f6" },
  pending: { Icon: Clock, color: "#6b7280" },
  routing: { Icon: RefreshCw, color: "#f59e0b" },
  reviewing: { Icon: Eye, color: "#a78bfa" },
};

const PIPELINE_COLORS: Record<string, string> = {
  auto: "#6b7280",
  sequential: "#3b82f6",
  parallel: "#a78bfa",
  consensus: "#f59e0b",
  iterative: "#06b6d4",
  deep_research: "#ec4899",
  idea_to_project: "#10b981",
};

interface Props {
  thread: Thread | null;
}

export function TaskHistory({ thread }: Props) {
  if (!thread?.tasks?.length) return null;

  return (
    <section className="border-t border-border" aria-label="Görev geçmişi">
      <div className="px-3 lg:px-4 py-2 flex items-center gap-2">
        <ClipboardList
          className="w-3.5 h-3.5 text-slate-400"
          aria-hidden="true"
        />
        <span className="text-xs font-semibold text-slate-400">
          Task History
        </span>
        <span className="text-[10px] text-slate-600">
          {thread.tasks.length} görev
        </span>
      </div>
      <div className="max-h-52 overflow-y-auto px-3 lg:px-4 pb-2 space-y-1">
        {[...thread.tasks].reverse().map((task) => (
          <TaskRow key={task.id} task={task} />
        ))}
      </div>
    </section>
  );
}

function TaskRow({ task }: { task: Task }) {
  const [expanded, setExpanded] = useState(false);
  const st = STATUS_CFG[task.status] ?? STATUS_CFG.pending;
  const StatusIcon = st.Icon;
  const pColor = PIPELINE_COLORS[task.pipeline_type] ?? "#6b7280";
  const latency = task.total_latency_ms
    ? `${(task.total_latency_ms ?? 0).toFixed(0)}ms`
    : "—";

  return (
    <div className="rounded-lg bg-surface border border-border">
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls={`task-detail-${task.id}`}
        className="w-full flex items-center gap-2 px-3 py-2 min-h-[44px] text-left cursor-pointer"
      >
        <span className="text-[10px] font-mono text-slate-600">
          #{task.id.slice(0, 6)}
        </span>
        <span className="text-xs text-slate-300 truncate flex-1 break-words">
          {task.user_input.slice(0, 60)}
        </span>
        <span
          className="text-[10px] px-1.5 py-0.5 rounded font-medium"
          style={{ color: pColor, backgroundColor: `${pColor}15` }}
        >
          {task.pipeline_type}
        </span>
        <StatusIcon
          className="w-3.5 h-3.5 flex-shrink-0"
          style={{ color: st.color }}
          aria-hidden="true"
        />
        <span className="text-[10px] font-mono text-slate-500">{latency}</span>
        <span className="text-slate-600" aria-hidden="true">
          {expanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </span>
      </button>

      {expanded && task.final_result && (
        <div
          id={`task-detail-${task.id}`}
          className="px-3 pb-3 border-t border-border/50"
        >
          <div className="text-xs text-slate-400 mt-2 whitespace-pre-wrap leading-relaxed max-h-40 overflow-y-auto break-words">
            {task.final_result}
          </div>
          {task.sub_tasks.length > 0 && (
            <div className="mt-2 space-y-0.5">
              <div className="text-[10px] text-slate-500 font-medium">
                Agents:
              </div>
              {task.sub_tasks.map((sub) => (
                <div
                  key={sub.id}
                  className="text-[10px] text-slate-500 flex gap-2"
                >
                  <span className="text-slate-400">{sub.assigned_agent}</span>
                  <span>{sub.status}</span>
                  <span className="font-mono">
                    {sub.token_usage} tok · {(sub.latency_ms ?? 0).toFixed(0)}ms
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
