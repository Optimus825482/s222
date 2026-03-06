"use client";

import { useEffect, useMemo, useRef } from "react";
import type { Thread, Task, TaskStatus, WSLiveEvent } from "@/lib/types";
import { EVENT_ICONS, getAgentInfo } from "@/lib/agents";
import { Activity, GitBranch, Radio, Circle, CheckCircle2, AlertTriangle, BarChart3, Calendar } from "lucide-react";
import { TimelineChart } from "./timeline-chart";
import { PerformanceMetrics } from "./performance-metrics";

interface Props {
    thread: Thread | null;
    liveEvents: WSLiveEvent[];
}

type Stage = {
    key: TaskStatus;
    label: string;
    colorClass: string;
    lineClass: string;
};

type LogItem = {
    id: string;
    timestamp: number;
    content: string;
    eventType: string;
    agent: string;
    isLive: boolean;
};

const STAGES: Stage[] = [
    { key: "pending", label: "Beklemede", colorClass: "text-slate-400 border-slate-500/60", lineClass: "bg-slate-700" },
    { key: "routing", label: "Yönlendiriliyor", colorClass: "text-amber-300 border-amber-400/70", lineClass: "bg-amber-500/70" },
    { key: "running", label: "Çalışıyor", colorClass: "text-sky-300 border-sky-400/70", lineClass: "bg-sky-500/70" },
    { key: "reviewing", label: "İnceleniyor", colorClass: "text-violet-300 border-violet-400/70", lineClass: "bg-violet-500/70" },
    { key: "completed", label: "Tamamlandı", colorClass: "text-emerald-300 border-emerald-400/70", lineClass: "bg-emerald-500/70" },
    { key: "failed", label: "Hata", colorClass: "text-rose-300 border-rose-400/70", lineClass: "bg-rose-500/70" },
];

const LOGGABLE_EVENTS = new Set([
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

function stageIndex(status: TaskStatus): number {
    const idx = STAGES.findIndex((s) => s.key === status);
    if (idx >= 0) return idx;
    return 0;
}

function shortId(id: string): string {
    if (!id) return "-";
    return id.length > 8 ? id.slice(0, 8) : id;
}

function statusChipClass(status: TaskStatus): string {
    switch (status) {
        case "completed":
            return "bg-emerald-500/15 text-emerald-300 border-emerald-400/30";
        case "failed":
            return "bg-rose-500/15 text-rose-300 border-rose-400/30";
        case "running":
            return "bg-sky-500/15 text-sky-300 border-sky-400/30";
        case "reviewing":
            return "bg-violet-500/15 text-violet-300 border-violet-400/30";
        case "routing":
            return "bg-amber-500/15 text-amber-300 border-amber-400/30";
        default:
            return "bg-slate-500/15 text-slate-300 border-slate-400/30";
    }
}

function statusLabel(status: TaskStatus): string {
    return STAGES.find((s) => s.key === status)?.label ?? status;
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

function eventToneClass(eventType: string): string {
    switch (eventType) {
        case "routing_decision":
            return "border-l-fuchsia-400";
        case "agent_start":
            return "border-l-blue-400";
        case "agent_thinking":
            return "border-l-violet-400";
        case "tool_call":
            return "border-l-amber-400";
        case "tool_result":
            return "border-l-emerald-400";
        case "pipeline_start":
            return "border-l-cyan-400";
        case "pipeline_step":
            return "border-l-cyan-500";
        case "pipeline_complete":
            return "border-l-emerald-500";
        case "synthesis":
            return "border-l-purple-400";
        case "error":
            return "border-l-rose-500";
        default:
            return "border-l-slate-500";
    }
}

function eventLabelToneClass(eventType: string): string {
    switch (eventType) {
        case "routing_decision":
            return "text-fuchsia-300";
        case "agent_start":
            return "text-blue-300";
        case "agent_thinking":
            return "text-violet-300";
        case "tool_call":
            return "text-amber-300";
        case "tool_result":
            return "text-emerald-300";
        case "pipeline_start":
        case "pipeline_step":
            return "text-cyan-300";
        case "pipeline_complete":
            return "text-emerald-300";
        case "synthesis":
            return "text-purple-300";
        case "error":
            return "text-rose-300";
        default:
            return "text-slate-300";
    }
}

function agentToneClass(agentRole: string): string {
    switch (agentRole) {
        case "orchestrator":
            return "text-pink-300";
        case "thinker":
            return "text-cyan-300";
        case "speed":
            return "text-violet-300";
        case "researcher":
            return "text-amber-300";
        case "reasoner":
            return "text-emerald-300";
        default:
            return "text-slate-300";
    }
}

function toLogItems(thread: Thread | null, liveEvents: WSLiveEvent[]): LogItem[] {
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
        .slice(-120);
}

function StageDiagram({ task }: { task: Task }) {
    const current = stageIndex(task.status);
    const isFailed = task.status === "failed";

    return (
        <div className="space-y-2" aria-label={`Görev ${shortId(task.id)} akış durumu`}>
            <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] text-slate-300 truncate">#{shortId(task.id)}</span>
                <span className={`text-[10px] px-2 py-0.5 border rounded-full ${statusChipClass(task.status)}`}>
                    {statusLabel(task.status)}
                </span>
            </div>

            <div className="relative">
                <div className="absolute left-3 right-3 top-3 h-px bg-slate-700" aria-hidden="true" />
                <ol className="relative grid grid-cols-6 gap-1" role="list">
                    {STAGES.map((stage, index) => {
                        const completed = !isFailed && index <= current;
                        const failedNode = isFailed && stage.key === "failed";
                        const active = index === current;
                        const nodeClass = failedNode
                            ? "text-rose-300 border-rose-400/80 bg-rose-500/20"
                            : completed
                                ? `${stage.colorClass} bg-white/5`
                                : "text-slate-500 border-slate-700 bg-slate-900/30";

                        return (
                            <li key={stage.key} className="relative flex flex-col items-center gap-1">
                                <span
                                    className={`w-6 h-6 rounded-full border flex items-center justify-center text-[10px] ${nodeClass} ${active ? "ring-2 ring-white/20" : ""}`}
                                    aria-current={active ? "step" : undefined}
                                >
                                    {failedNode ? <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" /> : completed ? <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" /> : <Circle className="w-3.5 h-3.5" aria-hidden="true" />}
                                </span>
                                <span className={`text-[9px] leading-tight text-center ${completed || failedNode ? "text-slate-300" : "text-slate-500"}`}>
                                    {stage.label}
                                </span>
                            </li>
                        );
                    })}
                </ol>
            </div>
        </div>
    );
}

export function TaskFlowMonitor({ thread, liveEvents }: Props) {
    const scrollRef = useRef<HTMLDivElement | null>(null);
    const logs = useMemo(() => toLogItems(thread, liveEvents), [thread, liveEvents]);
    const tasks = useMemo(() => (thread?.tasks ?? []).slice().reverse().slice(0, 8), [thread]);

    useEffect(() => {
        if (!scrollRef.current) return;
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [logs.length]);

    return (
        <section className="h-full flex flex-col bg-surface/40" aria-label="Görev akış monitörü">
            <header className="px-3 lg:px-4 py-3 border-b border-border flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-fuchsia-300" aria-hidden="true" />
                <h2 className="text-xs lg:text-sm font-semibold text-slate-100">Görev Akış Monitörü</h2>
            </header>

            <div className="px-3 lg:px-4 py-3 border-b border-border/80 space-y-3">
                <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
                    <Activity className="w-3.5 h-3.5 text-cyan-300" aria-hidden="true" />
                    Aşama Diyagramı
                </div>

                <div className="space-y-3 max-h-[40vh] overflow-y-auto pr-1" role="list" aria-label="Görev aşamaları">
                    {tasks.length === 0 && <p className="text-[11px] text-slate-500">Henüz görev bulunmuyor.</p>}
                    {tasks.map((task) => (
                        <article key={task.id} className="rounded-lg border border-border/80 bg-slate-900/30 p-2.5" role="listitem">
                            <StageDiagram task={task} />
                        </article>
                    ))}
                </div>
            </div>

            {/* Timeline ve Performans Metrikleri Bölümleri */}
            <div className="px-3 lg:px-4 py-3 border-b border-border/80 space-y-3">
                <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
                    <Calendar className="w-3.5 h-3.5 text-amber-300" aria-hidden="true" />
                    Zaman Çizelgesi
                </div>
                <TimelineChart
                    events={liveEvents.map(event => ({
                        id: typeof event.extra?.event_id === 'string' ? event.extra.event_id : event.timestamp.toString(),
                        timestamp: new Date(event.timestamp * 1000), // saniye cinsinden olduğu için 1000 ile çarp
                        eventType: event.event_type,
                        content: event.content,
                        agent: event.agent
                    }))}
                />
            </div>

            <div className="px-3 lg:px-4 py-3 border-b border-border/80 space-y-3">
                <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
                    <BarChart3 className="w-3.5 h-3.5 text-emerald-300" aria-hidden="true" />
                    Performans Metrikleri
                </div>
                <PerformanceMetrics
                    metrics={[
                        { name: 'Toplam Olay', value: liveEvents.length, unit: 'adet' },
                        {
                            name: 'Aktif Thread',
                            value: thread?.id ? thread.id.substring(0, 8) : 'Yok',
                            unit: thread?.id ? 'ID' : undefined
                        },
                        {
                            name: 'Son Olay',
                            value: liveEvents.length > 0
                                ? new Date(liveEvents[liveEvents.length - 1].timestamp).toLocaleTimeString('tr-TR')
                                : 'Yok',
                            unit: liveEvents.length > 0 ? 'saat' : undefined
                        },
                        {
                            name: 'Olay Türü',
                            value: [...new Set(liveEvents.map(e => e.event_type))].length,
                            unit: 'tür'
                        }
                    ]}
                />
            </div>

            <div className="flex-1 min-h-0 flex flex-col">
                <div className="px-3 lg:px-4 py-2 border-b border-border/70 flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
                        <Radio className="w-3.5 h-3.5 text-emerald-300" aria-hidden="true" />
                        Dinamik Log Akışı
                    </div>
                    <span className="text-[10px] text-slate-500">{logs.length} kayıt</span>
                </div>

                <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto px-3 lg:px-4 py-2 space-y-1.5" role="log" aria-live="polite" aria-label="Canlı görev logları">
                    {logs.length === 0 && (
                        <p className="text-[11px] text-slate-500 py-6 text-center">Log bekleniyor...</p>
                    )}

                    {logs.map((log) => {
                        const eventCfg = EVENT_ICONS[log.eventType] ?? {
                            icon: "•",
                            label: log.eventType,
                            color: "#64748b",
                        };
                        const agent = getAgentInfo(log.agent);

                        return (
                            <article
                                key={log.id}
                                className={`rounded-md border-l-2 bg-slate-900/50 px-2.5 py-2 dynamic-log-enter ${eventToneClass(log.eventType)} ${log.isLive ? "ring-1 ring-cyan-400/20" : ""}`}
                            >
                                <div className="flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-2 min-w-0">
                                        <span className={`text-[10px] font-semibold ${eventLabelToneClass(log.eventType)}`}>
                                            {eventCfg.label}
                                        </span>
                                        <span className={`text-[10px] truncate ${agentToneClass(log.agent)}`}>
                                            {agent.name}
                                        </span>
                                    </div>
                                    <span className="text-[10px] text-slate-500 whitespace-nowrap">{toTimeString(log.timestamp)}</span>
                                </div>
                                <p className="mt-1 text-[11px] text-slate-300 leading-snug">{log.content}</p>
                            </article>
                        );
                    })}
                </div>
            </div>
        </section>
    );
}
