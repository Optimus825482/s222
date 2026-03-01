"use client";

import type { Task, SubTask } from "@/lib/types";
import { getAgentInfo } from "@/lib/agents";
import {
  Clock,
  RefreshCw,
  Settings,
  Eye,
  CheckCircle,
  XCircle,
  ArrowRight,
  ArrowLeftRight,
} from "lucide-react";
import type { ReactNode } from "react";

interface Props {
  task: Task | null;
}

const STATUS_MAP: Record<string, { icon: ReactNode; color: string }> = {
  pending: {
    icon: <Clock className="w-3 h-3 inline-block" />,
    color: "#475569",
  },
  routing: {
    icon: <RefreshCw className="w-3 h-3 inline-block animate-spin" />,
    color: "#f59e0b",
  },
  running: {
    icon: <Settings className="w-3 h-3 inline-block animate-spin" />,
    color: "#3b82f6",
  },
  reviewing: {
    icon: <Eye className="w-3 h-3 inline-block" />,
    color: "#a78bfa",
  },
  completed: {
    icon: <CheckCircle className="w-3 h-3 inline-block" />,
    color: "#10b981",
  },
  failed: {
    icon: <XCircle className="w-3 h-3 inline-block" />,
    color: "#ef4444",
  },
};

export function PipelineFlow({ task }: Props) {
  if (!task || !task.sub_tasks.length) return null;

  const isParallel = [
    "parallel",
    "consensus",
    "deep_research",
    "idea_to_project",
  ].includes(task.pipeline_type);
  const isIterative = task.pipeline_type === "iterative";

  return (
    <div className="border-t border-border px-3 lg:px-4 py-3">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-semibold text-slate-400">
          Pipeline: <span className="text-blue-400">{task.pipeline_type}</span>
        </span>
        <span className="text-[10px] text-slate-500">
          {task.sub_tasks.length} sub-task
        </span>
      </div>

      {isParallel ? (
        <ParallelFlow subtasks={task.sub_tasks} />
      ) : isIterative ? (
        <IterativeFlow subtasks={task.sub_tasks} />
      ) : (
        <SequentialFlow subtasks={task.sub_tasks} />
      )}
    </div>
  );
}

function PipelineNode({ subtask }: { subtask: SubTask }) {
  const info = getAgentInfo(subtask.assigned_agent);
  const st = STATUS_MAP[subtask.status] ?? STATUS_MAP.pending;

  return (
    <div
      className="rounded-lg bg-surface border-l-2 p-3 min-w-[160px] text-center"
      style={{ borderColor: info.color }}
      role="listitem"
      aria-label={`${info.name} - ${subtask.status}`}
    >
      <div className="text-2xl flex items-center justify-center min-h-[44px] min-w-[44px]">
        {info.icon}
      </div>
      <div
        className="text-[11px] font-semibold mt-1"
        style={{ color: info.color }}
      >
        {info.name}
      </div>
      <div className="text-[10px] text-slate-500 mt-1 truncate max-w-[150px] mx-auto">
        {subtask.description.slice(0, 40)}
      </div>
      <div
        className="text-[11px] mt-2 flex items-center justify-center gap-1"
        style={{ color: st.color }}
      >
        {st.icon} {subtask.status}
      </div>
      {subtask.token_usage > 0 && (
        <div className="text-[9px] text-slate-600 mt-1">
          {subtask.token_usage} tok · {subtask.latency_ms.toFixed(0)}ms
        </div>
      )}
    </div>
  );
}

function SequentialFlow({ subtasks }: { subtasks: SubTask[] }) {
  return (
    <div
      className="flex items-center gap-2 overflow-x-auto snap-x snap-mandatory pb-2 -mx-3 px-3 lg:-mx-4 lg:px-4"
      role="list"
      aria-label="Sıralı pipeline akışı"
    >
      {subtasks.map((st, i) => (
        <div
          key={st.id}
          className="flex items-center gap-2 shrink-0 snap-start"
        >
          <PipelineNode subtask={st} />
          {i < subtasks.length - 1 && (
            <ArrowRight
              className="w-5 h-5 text-slate-600 shrink-0"
              aria-hidden="true"
            />
          )}
        </div>
      ))}
    </div>
  );
}

function ParallelFlow({ subtasks }: { subtasks: SubTask[] }) {
  return (
    <div
      className="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-2 -mx-3 px-3 lg:-mx-4 lg:px-4"
      role="list"
      aria-label="Paralel pipeline akışı"
    >
      {subtasks.map((st) => (
        <div key={st.id} className="shrink-0 snap-start">
          <PipelineNode subtask={st} />
        </div>
      ))}
    </div>
  );
}

function IterativeFlow({ subtasks }: { subtasks: SubTask[] }) {
  if (subtasks.length < 2) return <SequentialFlow subtasks={subtasks} />;

  return (
    <div
      className="flex items-center gap-3 justify-center flex-wrap"
      role="list"
      aria-label="İteratif pipeline akışı"
    >
      <PipelineNode subtask={subtasks[0]} />
      <ArrowLeftRight
        className="w-5 h-5 text-slate-500 shrink-0"
        aria-hidden="true"
      />
      <PipelineNode subtask={subtasks[1]} />
    </div>
  );
}
