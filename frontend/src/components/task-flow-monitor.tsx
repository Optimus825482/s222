"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  Thread,
  Task,
  SubTask,
  TaskStatus,
  AgentRole,
  WSLiveEvent,
  AgentMetrics,
} from "@/lib/types";
import { EVENT_ICONS, getAgentInfo } from "@/lib/agents";
import {
  Activity,
  GitBranch,
  Radio,
  Circle,
  CheckCircle2,
  AlertTriangle,
  BarChart3,
  Search,
  ChevronDown,
  ChevronRight,
  Zap,
  Clock,
  TrendingUp,
  TrendingDown,
  Users,
  ArrowDown,
  Pause,
  Layers,
  Target,
} from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════════════════════════ */

interface Props {
  thread: Thread | null;
  liveEvents: WSLiveEvent[];
}

type Stage = {
  key: TaskStatus;
  label: string;
  colorClass: string;
  bgActive: string;
};

type LogItem = {
  id: string;
  timestamp: number;
  content: string;
  eventType: string;
  agent: string;
  isLive: boolean;
};

/* ═══════════════════════════════════════════════════════════════
   CONSTANTS
   ═══════════════════════════════════════════════════════════════ */

const STAGES: Stage[] = [
  {
    key: "pending",
    label: "Beklemede",
    colorClass: "text-slate-400",
    bgActive: "bg-slate-500/20 border-slate-500/60",
  },
  {
    key: "routing",
    label: "Yönlendirme",
    colorClass: "text-amber-300",
    bgActive: "bg-amber-500/20 border-amber-400/70",
  },
  {
    key: "running",
    label: "Çalışıyor",
    colorClass: "text-sky-300",
    bgActive: "bg-sky-500/20 border-sky-400/70",
  },
  {
    key: "reviewing",
    label: "İnceleme",
    colorClass: "text-teal-300",
    bgActive: "bg-teal-500/20 border-teal-400/70",
  },
  {
    key: "completed",
    label: "Tamam",
    colorClass: "text-emerald-300",
    bgActive: "bg-emerald-500/20 border-emerald-400/70",
  },
  {
    key: "failed",
    label: "Hata",
    colorClass: "text-rose-300",
    bgActive: "bg-rose-500/20 border-rose-400/70",
  },
];

const LOGGABLE_EVENTS = new Set([
  "routing_decision",
  "routing",
  "agent_start",
  "agent_thinking",
  "thinking",
  "tool_call",
  "tool_result",
  "pipeline_start",
  "pipeline_step",
  "pipeline_complete",
  "pipeline",
  "synthesis",
  "error",
  "response",
]);

const ALL_AGENT_ROLES: AgentRole[] = [
  "orchestrator",
  "thinker",
  "speed",
  "researcher",
  "reasoner",
  "observer",
];

/* ═══════════════════════════════════════════════════════════════
   UTILITY FUNCTIONS
   ═══════════════════════════════════════════════════════════════ */

function stageIndex(status: TaskStatus): number {
  const idx = STAGES.findIndex((s) => s.key === status);
  return idx >= 0 ? idx : 0;
}

function shortId(id: string): string {
  if (!id) return "-";
  return id.length > 8 ? id.slice(0, 8) : id;
}

function statusLabel(status: TaskStatus): string {
  return STAGES.find((s) => s.key === status)?.label ?? status;
}

function statusChipClass(status: TaskStatus): string {
  const map: Record<string, string> = {
    completed: "bg-emerald-500/15 text-emerald-300 border-emerald-400/30",
    failed: "bg-rose-500/15 text-rose-300 border-rose-400/30",
    running: "bg-sky-500/15 text-sky-300 border-sky-400/30",
    reviewing: "bg-teal-500/15 text-teal-300 border-teal-400/30",
    routing: "bg-amber-500/15 text-amber-300 border-amber-400/30",
  };
  return map[status] ?? "bg-slate-500/15 text-slate-300 border-slate-400/30";
}

function parseTs(ts: string | number | undefined): number {
  if (typeof ts === "number") return ts;
  if (!ts) return Date.now();
  const n = Date.parse(ts);
  return Number.isFinite(n) ? n : Date.now();
}

function toTimeString(timestamp: number): string {
  try {
    return new Date(timestamp).toLocaleTimeString("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "--:--:--";
  }
}

function eventBorderClass(eventType: string): string {
  const map: Record<string, string> = {
    routing_decision: "border-l-fuchsia-400",
    routing: "border-l-fuchsia-400",
    agent_start: "border-l-blue-400",
    agent_thinking: "border-l-teal-400",
    thinking: "border-l-teal-400",
    tool_call: "border-l-amber-400",
    tool_result: "border-l-emerald-400",
    pipeline_start: "border-l-cyan-400",
    pipeline_step: "border-l-cyan-500",
    pipeline_complete: "border-l-emerald-500",
    pipeline: "border-l-cyan-500",
    synthesis: "border-l-orange-400",
    error: "border-l-rose-500",
    response: "border-l-cyan-300",
  };
  return map[eventType] ?? "border-l-slate-500";
}

function eventLabelColor(eventType: string): string {
  const map: Record<string, string> = {
    routing_decision: "text-fuchsia-300",
    routing: "text-fuchsia-300",
    agent_start: "text-blue-300",
    agent_thinking: "text-teal-300",
    thinking: "text-teal-300",
    tool_call: "text-amber-300",
    tool_result: "text-emerald-300",
    pipeline_start: "text-cyan-300",
    pipeline_step: "text-cyan-300",
    pipeline_complete: "text-emerald-300",
    pipeline: "text-cyan-300",
    synthesis: "text-orange-300",
    error: "text-rose-300",
    response: "text-cyan-200",
  };
  return map[eventType] ?? "text-slate-300";
}

function agentTextColor(role: string): string {
  const map: Record<string, string> = {
    orchestrator: "text-pink-300",
    thinker: "text-cyan-300",
    speed: "text-violet-300",
    researcher: "text-amber-300",
    reasoner: "text-emerald-300",
  };
  return map[role] ?? "text-slate-300";
}

function toLogItems(
  thread: Thread | null,
  liveEvents: WSLiveEvent[],
): LogItem[] {
  const historical: LogItem[] = (thread?.events ?? [])
    .filter((e) => LOGGABLE_EVENTS.has(e.event_type))
    .map((e) => ({
      id: e.id,
      timestamp: parseTs(e.timestamp),
      content: e.content,
      eventType: e.event_type,
      agent: e.agent_role ?? "system",
      isLive: false,
    }));

  const live: LogItem[] = liveEvents
    .filter((e) => LOGGABLE_EVENTS.has(e.event_type))
    .map((e, i) => ({
      id: `live-${i}-${e.timestamp}`,
      timestamp: parseTs(e.timestamp),
      content: e.content,
      eventType: e.event_type,
      agent: e.agent,
      isLive: true,
    }));

  return [...historical, ...live]
    .sort((a, b) => a.timestamp - b.timestamp)
    .slice(-150);
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 1: ENHANCED STAGE DIAGRAM
   ═══════════════════════════════════════════════════════════════ */

function StageDiagram({ task }: { task: Task }) {
  const current = stageIndex(task.status);
  const isFailed = task.status === "failed";
  const completedCount = task.sub_tasks.filter(
    (s) => s.status === "completed",
  ).length;
  const totalCount = task.sub_tasks.length;
  const pct =
    totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  // Count sub-tasks per stage
  const perStage = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const st of STAGES) counts[st.key] = 0;
    for (const sub of task.sub_tasks) {
      if (counts[sub.status] !== undefined) counts[sub.status]++;
    }
    return counts;
  }, [task.sub_tasks]);

  return (
    <div
      className="space-y-2.5"
      aria-label={`Görev ${shortId(task.id)} akış durumu`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[11px] font-mono text-slate-400 shrink-0">
            #{shortId(task.id)}
          </span>
          <span
            className={`text-[10px] px-2 py-0.5 border rounded ${statusChipClass(task.status)}`}
          >
            {statusLabel(task.status)}
          </span>
        </div>
        <span className="text-[10px] text-slate-500">
          {completedCount}/{totalCount} alt görev
        </span>
      </div>

      {/* Stage nodes */}
      <div className="relative">
        {/* Progress track */}
        <div
          className="absolute left-3 right-3 top-[11px] h-[2px] bg-slate-800"
          aria-hidden="true"
        />
        {!isFailed && current > 0 && (
          <div
            className="absolute left-3 top-[11px] h-[2px] bg-emerald-500/60 transition-all duration-700 ease-out"
            style={{ width: `${(current / (STAGES.length - 1)) * 100}%` }}
            aria-hidden="true"
          />
        )}

        <ol className="relative grid grid-cols-6 gap-0.5" role="list">
          {STAGES.map((stage, index) => {
            const completed = !isFailed && index <= current;
            const failedNode = isFailed && stage.key === "failed";
            const active = index === current && !isFailed;
            const count = perStage[stage.key] ?? 0;

            return (
              <li
                key={stage.key}
                className="relative flex flex-col items-center gap-1"
              >
                <span
                  className={`
                    w-[22px] h-[22px] rounded border flex items-center justify-center text-[10px]
                    transition-all duration-500
                    ${
                      failedNode
                        ? "bg-rose-500/20 border-rose-400/80 text-rose-300"
                        : active
                          ? `${stage.bgActive} ${stage.colorClass} ring-1 ring-white/10 animate-pulse`
                          : completed
                            ? `bg-emerald-500/10 border-emerald-500/40 text-emerald-400`
                            : "bg-slate-900/40 border-slate-700 text-slate-600"
                    }
                  `}
                  aria-current={active ? "step" : undefined}
                >
                  {failedNode ? (
                    <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                  ) : completed ? (
                    <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                  ) : (
                    <Circle className="w-3 h-3" aria-hidden="true" />
                  )}
                </span>
                <span
                  className={`text-[8px] leading-tight text-center ${completed || failedNode ? "text-slate-300" : "text-slate-600"}`}
                >
                  {stage.label}
                </span>
                {count > 0 && (
                  <span className="text-[8px] text-slate-500 font-mono">
                    {count}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </div>

      {/* Mini progress bar */}
      {totalCount > 0 && (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1 bg-slate-800 rounded-sm overflow-hidden">
            <div
              className={`h-full transition-all duration-700 ease-out ${
                isFailed ? "bg-rose-500/70" : "bg-emerald-500/60"
              }`}
              style={{ width: `${pct}%` }}
              role="progressbar"
              aria-valuenow={pct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Tamamlanma: %${pct}`}
            />
          </div>
          <span className="text-[9px] text-slate-500 font-mono w-8 text-right">
            %{pct}
          </span>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 2: INTERACTIVE GANTT CHART (Pure SVG)
   ═══════════════════════════════════════════════════════════════ */

interface GanttTooltip {
  x: number;
  y: number;
  sub: SubTask;
}

function GanttChart({ task }: { task: Task }) {
  const [tooltip, setTooltip] = useState<GanttTooltip | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const chartData = useMemo(() => {
    if (!task.sub_tasks.length) return null;

    const subs = task.sub_tasks;
    const taskStart = parseTs(task.created_at);

    // Group by agent
    const agentGroups: Record<string, SubTask[]> = {};
    for (const sub of subs) {
      const role = sub.assigned_agent;
      if (!agentGroups[role]) agentGroups[role] = [];
      agentGroups[role].push(sub);
    }

    const agents = Object.keys(agentGroups);
    const rowHeight = 28;
    const headerH = 24;
    const leftPad = 80;
    const rightPad = 16;
    const totalH =
      headerH +
      agents.reduce((sum, a) => sum + agentGroups[a].length * rowHeight, 0) +
      8;

    // Calculate max time span
    const maxLatency = Math.max(...subs.map((s) => s.latency_ms), 1000);
    const totalMs = maxLatency * 1.2; // 20% padding

    // Build bar data
    type BarData = {
      sub: SubTask;
      row: number;
      agent: string;
      startMs: number;
      durationMs: number;
    };

    const bars: BarData[] = [];
    let rowIdx = 0;
    for (const agent of agents) {
      for (const sub of agentGroups[agent]) {
        // Estimate start time based on dependencies and position
        const depMaxEnd =
          sub.depends_on.length > 0
            ? Math.max(
                ...sub.depends_on.map((depId) => {
                  const dep = subs.find((s) => s.id === depId);
                  return dep ? dep.latency_ms : 0;
                }),
              )
            : 0;
        const startMs = depMaxEnd;
        const durationMs = Math.max(sub.latency_ms, 50);

        bars.push({ sub, row: rowIdx, agent, startMs, durationMs });
        rowIdx++;
      }
    }

    return {
      agents,
      agentGroups,
      bars,
      totalMs,
      rowHeight,
      headerH,
      leftPad,
      rightPad,
      totalH,
      taskStart,
    };
  }, [task]);

  if (!chartData || chartData.bars.length === 0) {
    return (
      <p className="text-[11px] text-slate-500 py-3 text-center">
        Alt görev verisi yok.
      </p>
    );
  }

  const {
    agents,
    agentGroups,
    bars,
    totalMs,
    rowHeight,
    headerH,
    leftPad,
    rightPad,
    totalH,
  } = chartData;
  const chartW = 520;
  const barAreaW = chartW - leftPad - rightPad;

  // Time axis ticks
  const tickCount = 5;
  const ticks = Array.from(
    { length: tickCount + 1 },
    (_, i) => (totalMs / tickCount) * i,
  );

  // Dependency arrows
  const depArrows: { from: (typeof bars)[0]; to: (typeof bars)[0] }[] = [];
  for (const bar of bars) {
    for (const depId of bar.sub.depends_on) {
      const fromBar = bars.find((b) => b.sub.id === depId);
      if (fromBar) depArrows.push({ from: fromBar, to: bar });
    }
  }

  const msToX = (ms: number) => leftPad + (ms / totalMs) * barAreaW;

  return (
    <div className="relative overflow-x-auto">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${chartW} ${totalH}`}
        className="w-full min-w-[400px]"
        role="img"
        aria-label="Gantt zaman çizelgesi"
      >
        {/* Time axis */}
        <line
          x1={leftPad}
          y1={headerH - 2}
          x2={chartW - rightPad}
          y2={headerH - 2}
          stroke="#334155"
          strokeWidth="1"
        />
        {ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={msToX(t)}
              y1={headerH - 6}
              x2={msToX(t)}
              y2={totalH}
              stroke="#1e293b"
              strokeWidth="0.5"
              strokeDasharray="2,3"
            />
            <text
              x={msToX(t)}
              y={headerH - 8}
              textAnchor="middle"
              className="fill-slate-500"
              fontSize="8"
              fontFamily="monospace"
            >
              {(t / 1000).toFixed(1)}s
            </text>
          </g>
        ))}

        {/* Agent labels + bars */}
        {(() => {
          let currentRow = 0;
          return agents.map((agent) => {
            const agentInfo = getAgentInfo(agent);
            const groupStart = currentRow;
            const groupBars = bars.filter((b) => b.agent === agent);

            const labelY =
              headerH +
              groupStart * rowHeight +
              (agentGroups[agent].length * rowHeight) / 2;

            currentRow += agentGroups[agent].length;

            return (
              <g key={agent}>
                {/* Agent label */}
                <text
                  x={leftPad - 6}
                  y={labelY + 4}
                  textAnchor="end"
                  fontSize="9"
                  fontFamily="sans-serif"
                  fill={agentInfo.color}
                >
                  {agentInfo.icon} {agent.slice(0, 6)}
                </text>

                {/* Bars */}
                {groupBars.map((bar) => {
                  const x = msToX(bar.startMs);
                  const w = Math.max((bar.durationMs / totalMs) * barAreaW, 4);
                  const y = headerH + bar.row * rowHeight + 4;
                  const h = rowHeight - 8;
                  const isRunning = bar.sub.status === "running";
                  const isFailed = bar.sub.status === "failed";

                  return (
                    <g
                      key={bar.sub.id}
                      onMouseEnter={(e) => {
                        const rect = svgRef.current?.getBoundingClientRect();
                        if (rect) {
                          setTooltip({
                            x: e.clientX - rect.left,
                            y: e.clientY - rect.top - 40,
                            sub: bar.sub,
                          });
                        }
                      }}
                      onMouseLeave={() => setTooltip(null)}
                      className="cursor-pointer"
                      role="button"
                      tabIndex={0}
                      aria-label={`${bar.sub.description}: ${bar.sub.latency_ms}ms, ${bar.sub.token_usage} token`}
                    >
                      <rect
                        x={x}
                        y={y}
                        width={w}
                        height={h}
                        rx="2"
                        fill={isFailed ? "#ef4444" : agentInfo.color}
                        opacity={
                          bar.sub.status === "completed"
                            ? 0.7
                            : bar.sub.status === "pending"
                              ? 0.2
                              : 0.5
                        }
                        className={isRunning ? "animate-pulse" : ""}
                      />
                      {/* Status indicator dot */}
                      <circle
                        cx={x + w - 3}
                        cy={y + h / 2}
                        r="2"
                        fill={
                          bar.sub.status === "completed"
                            ? "#10b981"
                            : bar.sub.status === "failed"
                              ? "#ef4444"
                              : bar.sub.status === "running"
                                ? "#38bdf8"
                                : "#475569"
                        }
                      />
                      {/* Label inside bar if wide enough */}
                      {w > 40 && (
                        <text
                          x={x + 4}
                          y={y + h / 2 + 3}
                          fontSize="7"
                          fill="#e2e8f0"
                          fontFamily="monospace"
                        >
                          {shortId(bar.sub.id)}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            );
          });
        })()}

        {/* Dependency arrows */}
        {depArrows.map((dep, i) => {
          const fromX = msToX(dep.from.startMs + dep.from.durationMs);
          const fromY = headerH + dep.from.row * rowHeight + rowHeight / 2;
          const toX = msToX(dep.to.startMs);
          const toY = headerH + dep.to.row * rowHeight + rowHeight / 2;

          return (
            <g key={`dep-${i}`}>
              <path
                d={`M${fromX},${fromY} C${fromX + 12},${fromY} ${toX - 12},${toY} ${toX},${toY}`}
                fill="none"
                stroke="#475569"
                strokeWidth="1"
                strokeDasharray="3,2"
                markerEnd="url(#arrowhead)"
              />
            </g>
          );
        })}

        {/* Arrow marker definition */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="6"
            markerHeight="4"
            refX="5"
            refY="2"
            orient="auto"
          >
            <polygon points="0 0, 6 2, 0 4" fill="#475569" />
          </marker>
        </defs>
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute z-50 pointer-events-none bg-slate-900 border border-slate-700 rounded px-2.5 py-2 shadow-lg"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: "translateX(-50%)",
          }}
        >
          <div className="text-[10px] space-y-0.5">
            <div className="text-slate-200 font-medium truncate max-w-[180px]">
              {tooltip.sub.description}
            </div>
            <div className="flex items-center gap-3 text-slate-400">
              <span>
                {getAgentInfo(tooltip.sub.assigned_agent).icon}{" "}
                {tooltip.sub.assigned_agent}
              </span>
              <span>{tooltip.sub.latency_ms}ms</span>
              <span>{tooltip.sub.token_usage} token</span>
            </div>
            <div
              className={`${statusChipClass(tooltip.sub.status)} inline-block px-1.5 py-0.5 rounded text-[9px] border`}
            >
              {statusLabel(tooltip.sub.status)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 3: AGENT HEALTH DASHBOARD
   ═══════════════════════════════════════════════════════════════ */

function CircularProgress({
  pct,
  color,
  size = 36,
}: {
  pct: number;
  color: string;
  size?: number;
}) {
  const r = (size - 4) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;

  return (
    <svg
      width={size}
      height={size}
      className="transform -rotate-90"
      aria-hidden="true"
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="#1e293b"
        strokeWidth="3"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="3"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-700 ease-out"
      />
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="central"
        className="transform rotate-90 origin-center"
        fill="#e2e8f0"
        fontSize="8"
        fontFamily="monospace"
      >
        {pct}%
      </text>
    </svg>
  );
}

function AgentHealthDashboard({
  metrics,
}: {
  metrics: Record<string, AgentMetrics>;
}) {
  const cards = useMemo(() => {
    return ALL_AGENT_ROLES.map((role) => {
      const m = metrics[role];
      const info = getAgentInfo(role);
      const successRate =
        m && m.total_calls > 0
          ? Math.round((m.success_count / m.total_calls) * 100)
          : 0;
      const avgLatency =
        m && m.total_calls > 0
          ? Math.round(m.total_latency_ms / m.total_calls)
          : 0;

      // Determine status
      let status: "active" | "idle" | "error" = "idle";
      if (m?.last_active) {
        const lastMs = Date.now() - parseTs(m.last_active);
        if (lastMs < 30_000) status = "active";
        else if (m.error_count > m.success_count) status = "error";
      }
      if (m && m.error_count > 0 && m.success_count === 0) status = "error";

      return { role, info, m, successRate, avgLatency, status };
    });
  }, [metrics]);

  return (
    <div
      className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-2"
      role="list"
      aria-label="Agent sağlık durumu"
    >
      {cards.map(({ role, info, m, successRate, avgLatency, status }) => (
        <article
          key={role}
          className={`
            relative rounded border bg-slate-900/50 p-2.5 space-y-2
            transition-all duration-300
            ${
              status === "active"
                ? "border-opacity-60 shadow-[0_0_8px_-2px]"
                : status === "error"
                  ? "border-rose-500/40"
                  : "border-slate-700/60"
            }
          `}
          style={{
            borderColor: status === "active" ? info.color : undefined,
            boxShadow:
              status === "active" ? `0 0 12px -4px ${info.color}40` : undefined,
          }}
          role="listitem"
          aria-label={`${info.name} - ${status === "active" ? "aktif" : status === "error" ? "hata" : "beklemede"}`}
        >
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="text-sm" aria-hidden="true">
                {info.icon}
              </span>
              <span className="text-[10px] font-medium text-slate-200 truncate">
                {role}
              </span>
            </div>
            {/* Status dot */}
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                status === "active"
                  ? "bg-emerald-400 animate-pulse"
                  : status === "error"
                    ? "bg-rose-400"
                    : "bg-slate-600"
              }`}
              aria-label={
                status === "active"
                  ? "Aktif"
                  : status === "error"
                    ? "Hata"
                    : "Beklemede"
              }
            />
          </div>

          {/* Circular progress */}
          <div className="flex justify-center">
            <CircularProgress pct={successRate} color={info.color} />
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[9px]">
            <div className="text-slate-500">Gecikme</div>
            <div className="text-slate-300 text-right font-mono">
              {avgLatency}ms
            </div>
            <div className="text-slate-500">Token</div>
            <div className="text-slate-300 text-right font-mono">
              {m
                ? m.total_tokens > 9999
                  ? `${(m.total_tokens / 1000).toFixed(1)}k`
                  : m.total_tokens
                : 0}
            </div>
            <div className="text-slate-500">Çağrı</div>
            <div className="text-slate-300 text-right font-mono">
              {m?.total_calls ?? 0}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 4: REAL-TIME PERFORMANCE METRICS
   ═══════════════════════════════════════════════════════════════ */

function Sparkline({
  values,
  color,
  width = 64,
  height = 20,
}: {
  values: number[];
  color: string;
  width?: number;
  height?: number;
}) {
  if (values.length < 2) return null;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const step = width / (values.length - 1);

  const points = values
    .map(
      (v, i) =>
        `${i * step},${height - ((v - min) / range) * (height - 2) - 1}`,
    )
    .join(" ");

  return (
    <svg width={width} height={height} className="shrink-0" aria-hidden="true">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PerformancePanel({
  thread,
  tasks,
}: {
  thread: Thread | null;
  tasks: Task[];
}) {
  const stats = useMemo(() => {
    const completedTasks = tasks.filter((t) => t.status === "completed");
    const failedTasks = tasks.filter((t) => t.status === "failed");
    const allSubs = tasks.flatMap((t) => t.sub_tasks);
    const completedSubs = allSubs.filter((s) => s.status === "completed");

    // Token efficiency: tokens per successful sub-task
    const totalTokens = completedSubs.reduce(
      (s, sub) => s + sub.token_usage,
      0,
    );
    const tokenEfficiency =
      completedSubs.length > 0
        ? Math.round(totalTokens / completedSubs.length)
        : 0;

    // Error rate
    const totalCount = tasks.length;
    const errorRate =
      totalCount > 0 ? Math.round((failedTasks.length / totalCount) * 100) : 0;

    // Avg response time
    const latencies = completedTasks
      .map((t) => t.total_latency_ms)
      .filter((l) => l > 0);
    const avgResponseMs =
      latencies.length > 0
        ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length)
        : 0;

    // Sparkline data: last 10 task latencies
    const sparkData = tasks.slice(-10).map((t) => t.total_latency_ms);

    // Active agents
    const activeAgents = thread?.agent_metrics
      ? Object.entries(thread.agent_metrics).filter(([, m]) => {
          if (!m.last_active) return false;
          return Date.now() - parseTs(m.last_active) < 30_000;
        }).length
      : 0;

    // Pipeline type
    const currentPipeline =
      tasks.length > 0 ? tasks[tasks.length - 1].pipeline_type : null;

    // Throughput: tasks per minute (rough estimate)
    let throughput = 0;
    if (completedTasks.length >= 2) {
      const first = parseTs(completedTasks[0].created_at);
      const last = parseTs(
        completedTasks[completedTasks.length - 1].completed_at ??
          completedTasks[completedTasks.length - 1].created_at,
      );
      const spanMin = (last - first) / 60_000;
      if (spanMin > 0)
        throughput = Math.round((completedTasks.length / spanMin) * 10) / 10;
    }

    // Error trend (comparing first half vs second half)
    let errorTrend: "up" | "down" | "flat" = "flat";
    if (tasks.length >= 4) {
      const mid = Math.floor(tasks.length / 2);
      const firstHalfErrors = tasks
        .slice(0, mid)
        .filter((t) => t.status === "failed").length;
      const secondHalfErrors = tasks
        .slice(mid)
        .filter((t) => t.status === "failed").length;
      if (secondHalfErrors > firstHalfErrors) errorTrend = "up";
      else if (secondHalfErrors < firstHalfErrors) errorTrend = "down";
    }

    return {
      tokenEfficiency,
      errorRate,
      avgResponseMs,
      sparkData,
      activeAgents,
      currentPipeline,
      throughput,
      errorTrend,
      completedCount: completedTasks.length,
      totalCount,
    };
  }, [thread, tasks]);

  const pipelineLabels: Record<string, string> = {
    sequential: "Sıralı",
    parallel: "Paralel",
    consensus: "Uzlaşı",
    iterative: "Tekrarlı",
    deep_research: "Araştırma",
    idea_to_project: "Proje",
    brainstorm: "Beyin Fırtınası",
    auto: "Otomatik",
  };

  return (
    <div
      className="grid grid-cols-2 lg:grid-cols-3 gap-2"
      role="list"
      aria-label="Performans metrikleri"
    >
      {/* Token Efficiency */}
      <div
        className="rounded border border-slate-700/50 bg-slate-900/40 p-2.5 space-y-1"
        role="listitem"
      >
        <div className="flex items-center gap-1.5">
          <Zap className="w-3 h-3 text-amber-400" aria-hidden="true" />
          <span className="text-[9px] text-slate-500 uppercase tracking-wide">
            Token/Görev
          </span>
        </div>
        <div className="text-base font-mono font-semibold text-slate-100">
          {stats.tokenEfficiency > 0
            ? stats.tokenEfficiency.toLocaleString("tr-TR")
            : "—"}
        </div>
      </div>

      {/* Throughput */}
      <div
        className="rounded border border-slate-700/50 bg-slate-900/40 p-2.5 space-y-1"
        role="listitem"
      >
        <div className="flex items-center gap-1.5">
          <TrendingUp className="w-3 h-3 text-emerald-400" aria-hidden="true" />
          <span className="text-[9px] text-slate-500 uppercase tracking-wide">
            Görev/dk
          </span>
        </div>
        <div className="text-base font-mono font-semibold text-slate-100">
          {stats.throughput > 0 ? stats.throughput : "—"}
        </div>
      </div>

      {/* Error Rate */}
      <div
        className="rounded border border-slate-700/50 bg-slate-900/40 p-2.5 space-y-1"
        role="listitem"
      >
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="w-3 h-3 text-rose-400" aria-hidden="true" />
          <span className="text-[9px] text-slate-500 uppercase tracking-wide">
            Hata Oranı
          </span>
          {stats.errorTrend !== "flat" &&
            (stats.errorTrend === "up" ? (
              <TrendingUp
                className="w-2.5 h-2.5 text-rose-400"
                aria-label="Artıyor"
              />
            ) : (
              <TrendingDown
                className="w-2.5 h-2.5 text-emerald-400"
                aria-label="Azalıyor"
              />
            ))}
        </div>
        <div
          className={`text-base font-mono font-semibold ${stats.errorRate > 20 ? "text-rose-300" : "text-slate-100"}`}
        >
          %{stats.errorRate}
        </div>
      </div>

      {/* Avg Response Time + Sparkline */}
      <div
        className="rounded border border-slate-700/50 bg-slate-900/40 p-2.5 space-y-1"
        role="listitem"
      >
        <div className="flex items-center gap-1.5">
          <Clock className="w-3 h-3 text-sky-400" aria-hidden="true" />
          <span className="text-[9px] text-slate-500 uppercase tracking-wide">
            Ort. Yanıt
          </span>
        </div>
        <div className="flex items-end justify-between gap-2">
          <span className="text-base font-mono font-semibold text-slate-100">
            {stats.avgResponseMs > 0
              ? `${(stats.avgResponseMs / 1000).toFixed(1)}s`
              : "—"}
          </span>
          <Sparkline values={stats.sparkData} color="#38bdf8" />
        </div>
      </div>

      {/* Active Agents */}
      <div
        className="rounded border border-slate-700/50 bg-slate-900/40 p-2.5 space-y-1"
        role="listitem"
      >
        <div className="flex items-center gap-1.5">
          <Users className="w-3 h-3 text-teal-400" aria-hidden="true" />
          <span className="text-[9px] text-slate-500 uppercase tracking-wide">
            Aktif Agent
          </span>
        </div>
        <div className="text-base font-mono font-semibold text-slate-100">
          {stats.activeAgents}/{ALL_AGENT_ROLES.length}
        </div>
      </div>

      {/* Pipeline Type */}
      <div
        className="rounded border border-slate-700/50 bg-slate-900/40 p-2.5 space-y-1"
        role="listitem"
      >
        <div className="flex items-center gap-1.5">
          <Layers className="w-3 h-3 text-fuchsia-400" aria-hidden="true" />
          <span className="text-[9px] text-slate-500 uppercase tracking-wide">
            Pipeline
          </span>
        </div>
        <div className="text-sm font-medium text-slate-100">
          {stats.currentPipeline
            ? (pipelineLabels[stats.currentPipeline] ?? stats.currentPipeline)
            : "—"}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 5: ENHANCED DYNAMIC LOG STREAM
   ═══════════════════════════════════════════════════════════════ */

const EVENT_FILTER_KEYS = [
  "routing_decision",
  "routing",
  "agent_start",
  "agent_thinking",
  "thinking",
  "tool_call",
  "tool_result",
  "pipeline_start",
  "pipeline_step",
  "pipeline_complete",
  "pipeline",
  "synthesis",
  "error",
  "response",
] as const;

function LogDetailDialog({
  log,
  onClose,
}: {
  log: LogItem;
  onClose: () => void;
}) {
  const eventCfg = EVENT_ICONS[log.eventType] ?? {
    icon: "•",
    label: log.eventType,
    color: "#64748b",
  };
  const agent = getAgentInfo(log.agent);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Log detayı"
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl w-[90vw] max-w-xl max-h-[70vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className={`text-xs font-semibold ${eventLabelColor(log.eventType)}`}
            >
              {eventCfg.icon} {eventCfg.label}
            </span>
            <span className={`text-xs ${agentTextColor(log.agent)}`}>
              {agent.name}
            </span>
            {log.isLive && (
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] text-slate-500 font-mono">
              {toTimeString(log.timestamp)}
            </span>
            <button
              onClick={onClose}
              className="text-slate-500 hover:text-slate-200 transition-colors text-lg leading-none"
              aria-label="Kapat"
            >
              ✕
            </button>
          </div>
        </div>
        {/* Body */}
        <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3">
          <pre className="text-[12px] leading-relaxed text-slate-300 whitespace-pre-wrap break-words font-mono">
            {log.content}
          </pre>
        </div>
        {/* Footer */}
        <div className="px-4 py-2 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-500">
          <span>ID: {log.id}</span>
          <span>Tür: {log.eventType}</span>
        </div>
      </div>
    </div>
  );
}

function LogStream({ logs }: { logs: LogItem[] }) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [selectedLog, setSelectedLog] = useState<LogItem | null>(null);

  const toggleFilter = useCallback((key: string) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const filtered = useMemo(() => {
    let result = logs;
    if (activeFilters.size > 0) {
      result = result.filter((l) => activeFilters.has(l.eventType));
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (l) =>
          l.content.toLowerCase().includes(q) ||
          l.agent.toLowerCase().includes(q) ||
          l.eventType.toLowerCase().includes(q),
      );
    }
    return result;
  }, [logs, activeFilters, searchQuery]);

  useEffect(() => {
    if (!autoScroll || !scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [filtered.length, autoScroll]);

  return (
    <div className="flex flex-col min-h-0 flex-1">
      {/* Controls bar */}
      <div className="px-3 lg:px-4 py-2 border-b border-slate-800/70 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
            <Radio
              className="w-3.5 h-3.5 text-emerald-400"
              aria-hidden="true"
            />
            Dinamik Log Akışı
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500 font-mono">
              {filtered.length}/{logs.length}
            </span>
            <button
              onClick={() => setAutoScroll((p) => !p)}
              className={`p-1 rounded transition-colors ${
                autoScroll
                  ? "text-emerald-400 bg-emerald-500/10"
                  : "text-slate-500 hover:text-slate-300"
              }`}
              aria-label={
                autoScroll
                  ? "Otomatik kaydırma açık"
                  : "Otomatik kaydırma kapalı"
              }
              title={
                autoScroll
                  ? "Otomatik kaydırma açık"
                  : "Otomatik kaydırma kapalı"
              }
            >
              {autoScroll ? (
                <ArrowDown className="w-3 h-3" />
              ) : (
                <Pause className="w-3 h-3" />
              )}
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500"
            aria-hidden="true"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Log ara..."
            className="w-full pl-6 pr-2 py-1 text-[10px] bg-slate-900/60 border border-slate-700/50 rounded text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-slate-600"
            aria-label="Log arama"
          />
        </div>

        {/* Filter chips */}
        <div
          className="flex flex-wrap gap-1"
          role="group"
          aria-label="Olay türü filtreleri"
        >
          {EVENT_FILTER_KEYS.map((key) => {
            const cfg = EVENT_ICONS[key];
            const isActive = activeFilters.has(key);
            return (
              <button
                key={key}
                onClick={() => toggleFilter(key)}
                className={`
                  text-[9px] px-1.5 py-0.5 rounded border transition-all
                  ${
                    isActive
                      ? "bg-slate-700/60 border-slate-500/60 text-slate-200"
                      : "bg-transparent border-slate-800 text-slate-500 hover:text-slate-400 hover:border-slate-700"
                  }
                `}
                aria-pressed={isActive}
                aria-label={`Filtre: ${cfg?.label ?? key}`}
              >
                {cfg?.icon ?? "•"} {cfg?.label ?? key}
              </button>
            );
          })}
        </div>
      </div>

      {/* Log entries */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto px-3 lg:px-4 py-2 space-y-1"
        role="log"
        aria-live="polite"
        aria-label="Canlı görev logları"
      >
        {filtered.length === 0 && (
          <p className="text-[11px] text-slate-500 py-6 text-center">
            {logs.length === 0 ? "Log bekleniyor..." : "Filtre sonucu boş."}
          </p>
        )}

        {filtered.map((log) => {
          const eventCfg = EVENT_ICONS[log.eventType] ?? {
            icon: "•",
            label: log.eventType,
            color: "#64748b",
          };
          const agent = getAgentInfo(log.agent);
          const isLong = log.content.length > 120;
          const isExpanded = expandedIds.has(log.id);
          const isError = log.eventType === "error";

          return (
            <article
              key={log.id}
              onClick={() => setSelectedLog(log)}
              className={`
                rounded border-l-2 px-2.5 py-1.5 transition-all duration-200 cursor-pointer hover:bg-slate-800/40
                ${eventBorderClass(log.eventType)}
                ${isError ? "bg-rose-950/20" : "bg-slate-900/40"}
                ${log.isLive ? "ring-1 ring-cyan-500/15" : ""}
              `}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") setSelectedLog(log);
              }}
              aria-label={`${eventCfg.label} - ${agent.name}: detay için tıkla`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={`text-[10px] font-semibold ${eventLabelColor(log.eventType)}`}
                  >
                    {eventCfg.icon} {eventCfg.label}
                  </span>
                  <span
                    className={`text-[10px] truncate ${agentTextColor(log.agent)}`}
                  >
                    {agent.name}
                  </span>
                  {log.isLive && (
                    <span
                      className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shrink-0"
                      aria-label="Canlı"
                    />
                  )}
                </div>
                <span className="text-[9px] text-slate-600 whitespace-nowrap font-mono">
                  {toTimeString(log.timestamp)}
                </span>
              </div>

              <div className="mt-1">
                <p
                  className={`text-[11px] leading-snug ${isError ? "text-rose-300" : "text-slate-400"} ${!isExpanded && isLong ? "line-clamp-2" : ""}`}
                >
                  {log.content}
                </p>
                {isLong && (
                  <button
                    onClick={() => toggleExpand(log.id)}
                    className="text-[9px] text-slate-500 hover:text-slate-300 mt-0.5 flex items-center gap-0.5 transition-colors"
                    aria-expanded={isExpanded}
                  >
                    {isExpanded ? (
                      <>
                        <ChevronDown className="w-2.5 h-2.5" /> Daralt
                      </>
                    ) : (
                      <>
                        <ChevronRight className="w-2.5 h-2.5" /> Devamı
                      </>
                    )}
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {/* Log Detail Dialog */}
      {selectedLog && (
        <LogDetailDialog
          log={selectedLog}
          onClose={() => setSelectedLog(null)}
        />
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 6: SUB-TASK DEPENDENCY GRAPH (Pure SVG)
   ═══════════════════════════════════════════════════════════════ */

function DependencyGraph({ subTasks }: { subTasks: SubTask[] }) {
  const layout = useMemo(() => {
    if (subTasks.length === 0) return null;

    // Topological layering: assign each node to a layer based on dependencies
    const idToSub = new Map(subTasks.map((s) => [s.id, s]));
    const layers: string[][] = [];
    const assigned = new Set<string>();

    // BFS-like layering
    const maxIter = subTasks.length + 1;
    let iter = 0;
    while (assigned.size < subTasks.length && iter < maxIter) {
      const layer: string[] = [];
      for (const sub of subTasks) {
        if (assigned.has(sub.id)) continue;
        const depsResolved = sub.depends_on.every((d) => assigned.has(d));
        if (depsResolved) layer.push(sub.id);
      }
      if (layer.length === 0) {
        // Remaining nodes have circular deps, just add them
        for (const sub of subTasks) {
          if (!assigned.has(sub.id)) layer.push(sub.id);
        }
      }
      for (const id of layer) assigned.add(id);
      layers.push(layer);
      iter++;
    }

    // Calculate positions
    const nodeR = 16;
    const layerGap = 80;
    const nodeGap = 48;
    const padX = 40;
    const padY = 30;

    const maxLayerSize = Math.max(...layers.map((l) => l.length));
    const svgW = layers.length * layerGap + padX * 2;
    const svgH = maxLayerSize * nodeGap + padY * 2;

    type NodePos = { id: string; sub: SubTask; x: number; y: number };
    const nodes: NodePos[] = [];
    const posMap = new Map<string, { x: number; y: number }>();

    for (let li = 0; li < layers.length; li++) {
      const layer = layers[li];
      const layerH = layer.length * nodeGap;
      const offsetY = (svgH - layerH) / 2;

      for (let ni = 0; ni < layer.length; ni++) {
        const id = layer[ni];
        const sub = idToSub.get(id)!;
        const x = padX + li * layerGap + layerGap / 2;
        const y = offsetY + ni * nodeGap + nodeGap / 2;
        nodes.push({ id, sub, x, y });
        posMap.set(id, { x, y });
      }
    }

    // Edges
    type Edge = {
      from: { x: number; y: number };
      to: { x: number; y: number };
    };
    const edges: Edge[] = [];
    for (const sub of subTasks) {
      const toPos = posMap.get(sub.id);
      if (!toPos) continue;
      for (const depId of sub.depends_on) {
        const fromPos = posMap.get(depId);
        if (fromPos) edges.push({ from: fromPos, to: toPos });
      }
    }

    return { nodes, edges, svgW, svgH, nodeR };
  }, [subTasks]);

  if (!layout || layout.nodes.length === 0) {
    return (
      <p className="text-[11px] text-slate-500 py-3 text-center">
        Bağımlılık verisi yok.
      </p>
    );
  }

  const { nodes, edges, svgW, svgH, nodeR } = layout;

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        className="w-full min-w-[280px]"
        style={{ maxHeight: 200 }}
        role="img"
        aria-label="Alt görev bağımlılık grafiği"
      >
        <defs>
          <marker
            id="dep-arrow"
            markerWidth="6"
            markerHeight="4"
            refX="5"
            refY="2"
            orient="auto"
          >
            <polygon points="0 0, 6 2, 0 4" fill="#475569" />
          </marker>
        </defs>

        {/* Edges */}
        {edges.map((e, i) => {
          const dx = e.to.x - e.from.x;
          const cpOffset = Math.max(dx * 0.3, 16);
          return (
            <path
              key={`edge-${i}`}
              d={`M${e.from.x + nodeR},${e.from.y} C${e.from.x + nodeR + cpOffset},${e.from.y} ${e.to.x - nodeR - cpOffset},${e.to.y} ${e.to.x - nodeR},${e.to.y}`}
              fill="none"
              stroke="#334155"
              strokeWidth="1.5"
              markerEnd="url(#dep-arrow)"
            />
          );
        })}

        {/* Nodes */}
        {nodes.map(({ id, sub, x, y }) => {
          const info = getAgentInfo(sub.assigned_agent);
          const isCompleted = sub.status === "completed";
          const isFailed = sub.status === "failed";
          const isRunning = sub.status === "running";

          return (
            <g
              key={id}
              role="img"
              aria-label={`${sub.description} - ${statusLabel(sub.status)}`}
            >
              {/* Outer ring for running */}
              {isRunning && (
                <circle
                  cx={x}
                  cy={y}
                  r={nodeR + 3}
                  fill="none"
                  stroke={info.color}
                  strokeWidth="1"
                  opacity="0.4"
                  className="animate-pulse"
                />
              )}
              {/* Node circle */}
              <circle
                cx={x}
                cy={y}
                r={nodeR}
                fill={isFailed ? "#1c0a0a" : "#0f172a"}
                stroke={
                  isFailed ? "#ef4444" : isCompleted ? "#10b981" : info.color
                }
                strokeWidth={isRunning ? 2 : 1.5}
                opacity={sub.status === "pending" ? 0.4 : 0.9}
              />
              {/* Agent icon */}
              <text
                x={x}
                y={y + 1}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize="11"
              >
                {info.icon}
              </text>
              {/* Status badge */}
              <circle
                cx={x + nodeR - 2}
                cy={y - nodeR + 2}
                r="3"
                fill={
                  isCompleted
                    ? "#10b981"
                    : isFailed
                      ? "#ef4444"
                      : isRunning
                        ? "#38bdf8"
                        : "#475569"
                }
                stroke="#0f172a"
                strokeWidth="1"
              />
              {/* Label below */}
              <text
                x={x}
                y={y + nodeR + 10}
                textAnchor="middle"
                fontSize="7"
                fill="#94a3b8"
                fontFamily="monospace"
              >
                {shortId(id)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SECTION 7: COLLAPSIBLE SECTION WRAPPER
   ═══════════════════════════════════════════════════════════════ */

function Section({
  icon,
  title,
  defaultOpen = true,
  badge,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-slate-800/60">
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full px-3 lg:px-4 py-2.5 flex items-center justify-between gap-2 hover:bg-slate-800/20 transition-colors"
        aria-expanded={open}
      >
        <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
          {icon}
          <span>{title}</span>
          {badge}
        </div>
        <ChevronDown
          className={`w-3 h-3 text-slate-500 transition-transform duration-200 ${open ? "" : "-rotate-90"}`}
          aria-hidden="true"
        />
      </button>
      {open && <div className="px-3 lg:px-4 pb-3">{children}</div>}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN EXPORT: TASK FLOW MONITOR
   ═══════════════════════════════════════════════════════════════ */

export function TaskFlowMonitor({ thread, liveEvents }: Props) {
  const logs = useMemo(
    () => toLogItems(thread, liveEvents),
    [thread, liveEvents],
  );
  const tasks = useMemo(
    () => (thread?.tasks ?? []).slice().reverse().slice(0, 12),
    [thread],
  );
  const latestTask = tasks[0] ?? null;
  const allSubTasks = useMemo(() => tasks.flatMap((t) => t.sub_tasks), [tasks]);
  const agentMetrics = thread?.agent_metrics ?? {};

  return (
    <section
      className="h-full flex flex-col bg-slate-950/60"
      aria-label="Görev akış monitörü"
    >
      {/* Header */}
      <header className="px-3 lg:px-4 py-3 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-fuchsia-400" aria-hidden="true" />
          <h2 className="text-xs lg:text-sm font-semibold text-slate-100">
            Görev Akış Monitörü
          </h2>
        </div>
        {latestTask && (
          <span
            className={`text-[9px] px-2 py-0.5 border rounded font-mono ${statusChipClass(latestTask.status)}`}
          >
            {statusLabel(latestTask.status)}
          </span>
        )}
      </header>

      {/* Scrollable content */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* 1. Stage Diagram */}
        <Section
          icon={
            <Activity
              className="w-3.5 h-3.5 text-cyan-400"
              aria-hidden="true"
            />
          }
          title="Aşama Diyagramı"
          badge={
            tasks.length > 0 ? (
              <span className="text-[9px] text-slate-500 font-mono ml-1">
                {tasks.length}
              </span>
            ) : undefined
          }
        >
          <div
            className="space-y-2 max-h-[35vh] overflow-y-auto pr-1"
            role="list"
            aria-label="Görev aşamaları"
          >
            {tasks.length === 0 && (
              <p className="text-[11px] text-slate-500 py-2">
                Henüz görev bulunmuyor.
              </p>
            )}
            {tasks.map((task) => (
              <article
                key={task.id}
                className="rounded border border-slate-800/60 bg-slate-900/30 p-2.5"
                role="listitem"
              >
                <StageDiagram task={task} />
              </article>
            ))}
          </div>
        </Section>

        {/* 2. Gantt Chart */}
        {latestTask && latestTask.sub_tasks.length > 0 && (
          <Section
            icon={
              <BarChart3
                className="w-3.5 h-3.5 text-amber-400"
                aria-hidden="true"
              />
            }
            title="Gantt Zaman Çizelgesi"
            defaultOpen={true}
          >
            <GanttChart task={latestTask} />
          </Section>
        )}

        {/* 3. Agent Health Dashboard */}
        <Section
          icon={
            <Users className="w-3.5 h-3.5 text-teal-400" aria-hidden="true" />
          }
          title="Agent Sağlık Durumu"
          defaultOpen={Object.keys(agentMetrics).length > 0}
        >
          <AgentHealthDashboard metrics={agentMetrics} />
        </Section>

        {/* 4. Performance Metrics */}
        <Section
          icon={
            <Zap className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
          }
          title="Performans Metrikleri"
        >
          <PerformancePanel thread={thread} tasks={tasks} />
        </Section>

        {/* 5. Dependency Graph */}
        {allSubTasks.length > 0 &&
          allSubTasks.some((s) => s.depends_on.length > 0) && (
            <Section
              icon={
                <Target
                  className="w-3.5 h-3.5 text-orange-400"
                  aria-hidden="true"
                />
              }
              title="Bağımlılık Grafiği"
              defaultOpen={false}
            >
              <DependencyGraph subTasks={allSubTasks} />
            </Section>
          )}
      </div>

      {/* 6. Log Stream - always visible at bottom, takes remaining space */}
      <div className="flex-1 min-h-[180px] max-h-[40vh] flex flex-col border-t border-slate-800/60">
        <LogStream logs={logs} />
      </div>
    </section>
  );
}
