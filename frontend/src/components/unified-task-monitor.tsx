"use client";

import {
  useState,
  useEffect,
  useRef,
  useMemo,
  useSyncExternalStore,
} from "react";
import { getWSSnapshot, subscribeWS } from "@/lib/ws-store";
import type { StreamToolCall } from "@/lib/ws-store";
import type { WSLiveEvent } from "@/lib/types";
import { getAgentInfo, EVENT_ICONS } from "@/lib/agents";
import {
  Activity,
  Brain,
  ChevronDown,
  ChevronRight,
  Cpu,
  Loader2,
  Check,
  Wrench,
  Radio,
  Users,
  Zap,
  Search,
  Target,
  GitBranch,
  Layers,
  Shield,
  Clock,
  MessageSquare,
} from "lucide-react";
import { DetailModal } from "./detail-modal";

/* ═══════════════════════════════════════════════════════════
   5-Phase Pipeline Definition
   ═══════════════════════════════════════════════════════════ */

interface PipelinePhase {
  id: string;
  label: string;
  icon: typeof Target;
  description: string;
  eventTypes: string[]; // which event_types map to this phase
}

const PIPELINE_PHASES: PipelinePhase[] = [
  {
    id: "intent",
    label: "Niyet Analizi",
    icon: Search,
    description: "Mesaj analiz ediliyor, niyet çıkarılıyor",
    eventTypes: ["routing_decision", "routing", "intent_analysis"],
  },
  {
    id: "pipeline",
    label: "Pipeline Seçimi",
    icon: GitBranch,
    description: "En uygun pipeline belirleniyor",
    eventTypes: ["pipeline_start", "pipeline", "pipeline_step"],
  },
  {
    id: "skills",
    label: "Skill Keşfi",
    icon: Layers,
    description: "Gerekli yetenekler keşfediliyor",
    eventTypes: ["skill_discovery", "skill_match"],
  },
  {
    id: "delegate",
    label: "Görev Dağıtımı",
    icon: Users,
    description: "Agent'lara görevler atanıyor",
    eventTypes: [
      "agent_start",
      "thinking",
      "agent_thinking",
      "tool_call",
      "tool_result",
    ],
  },
  {
    id: "synthesize",
    label: "Sentez + Kalite",
    icon: Shield,
    description: "Sonuçlar birleştiriliyor, kalite kontrolü yapılıyor",
    eventTypes: [
      "synthesis",
      "quality_gate",
      "confidence_analysis",
      "pipeline_complete",
      "final_report",
    ],
  },
];

/* ═══════════════════════════════════════════════════════════
   Phase Detection — derive current phase from live events
   ═══════════════════════════════════════════════════════════ */

function detectPhaseIndex(events: WSLiveEvent[]): number {
  let maxPhase = -1;
  for (const ev of events) {
    for (let i = 0; i < PIPELINE_PHASES.length; i++) {
      if (PIPELINE_PHASES[i].eventTypes.includes(ev.event_type)) {
        maxPhase = Math.max(maxPhase, i);
      }
    }
  }
  return maxPhase;
}

function isPhaseComplete(
  phaseIdx: number,
  currentPhase: number,
  status: string,
): boolean {
  if (status === "complete") return true;
  return phaseIdx < currentPhase;
}

/* ═══════════════════════════════════════════════════════════
   Active Agents — extract unique agents from recent events
   ═══════════════════════════════════════════════════════════ */

interface ActiveAgent {
  role: string;
  lastEvent: string;
  lastContent: string;
  timestamp: number;
  eventCount: number;
}

function extractActiveAgents(events: WSLiveEvent[]): ActiveAgent[] {
  const map = new Map<string, ActiveAgent>();
  for (const ev of events) {
    if (!ev.agent || ev.agent === "system") continue;
    const existing = map.get(ev.agent);
    map.set(ev.agent, {
      role: ev.agent,
      lastEvent: ev.event_type,
      lastContent: ev.content,
      timestamp: ev.timestamp,
      eventCount: (existing?.eventCount ?? 0) + 1,
    });
  }
  return Array.from(map.values()).sort((a, b) => b.timestamp - a.timestamp);
}

/* ═══════════════════════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════════════════════ */

type TabId = "pipeline" | "timeline" | "agents" | "system";

export function UnifiedTaskMonitor() {
  const [activeTab, setActiveTab] = useState<TabId>("pipeline");
  const snapshot = useSyncExternalStore(
    subscribeWS,
    getWSSnapshot,
    getWSSnapshot,
  );
  const {
    status,
    liveEvents,
    streamThinking,
    streamText,
    streamAgent,
    streamToolCalls,
  } = snapshot;

  const isActive = status === "running";

  useEffect(() => {
    if (status === "running") setActiveTab("pipeline");
  }, [status]);

  // External tab-switch
  useEffect(() => {
    const handler = (e: Event) => {
      const tab = (e as CustomEvent<TabId>).detail;
      if (tab) setActiveTab(tab);
    };
    window.addEventListener("task-monitor-tab", handler);
    return () => window.removeEventListener("task-monitor-tab", handler);
  }, []);

  const TABS: { id: TabId; label: string; icon: typeof Radio }[] = [
    { id: "pipeline", label: "Pipeline", icon: Activity },
    { id: "timeline", label: "Zaman Çizelgesi", icon: Clock },
    { id: "agents", label: "Agentlar", icon: Users },
    { id: "system", label: "Sistem", icon: Cpu },
  ];

  return (
    <div className="flex flex-col h-full min-h-0 bg-white text-gray-900">
      {/* Tab bar */}
      <div className="flex items-center border-b border-[#d6d2c2] bg-[#ECE9D8] px-1 shrink-0">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] border border-transparent rounded-t transition-colors cursor-pointer"
              style={{
                fontFamily: "Tahoma, sans-serif",
                fontWeight: isSelected ? 600 : 400,
                background: isSelected ? "#fff" : "transparent",
                border: isSelected
                  ? "1px solid #d6d2c2"
                  : "1px solid transparent",
                borderBottom: isSelected
                  ? "1px solid #fff"
                  : "1px solid #d6d2c2",
                marginBottom: -1,
                color: isSelected ? "#000" : "#555",
              }}
            >
              <Icon className="w-3 h-3" />
              {tab.label}
            </button>
          );
        })}
        {/* Status badge */}
        <div className="ml-auto flex items-center gap-1.5 pr-2">
          {isActive && (
            <Activity className="w-3 h-3 text-emerald-500 animate-pulse" />
          )}
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded ${
              isActive
                ? "bg-[#e6f5e6] text-[#339966]"
                : status === "complete"
                  ? "bg-[#e6f5e6] text-[#339966]"
                  : status === "error"
                    ? "bg-[#ffe6e6] text-[#cc3333]"
                    : "bg-gray-200 text-gray-500"
            }`}
          >
            {isActive
              ? "Aktif"
              : status === "complete"
                ? "Tamamlandı"
                : status === "error"
                  ? "Hata"
                  : "Bekleniyor"}
          </span>
          {liveEvents.length > 0 && (
            <span className="text-[9px] text-gray-400">
              {liveEvents.length} olay
            </span>
          )}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 min-h-0 overflow-auto">
        {activeTab === "pipeline" && (
          <PipelineTab
            events={liveEvents}
            status={status}
            streamThinking={streamThinking}
            streamText={streamText}
            streamAgent={streamAgent}
            streamToolCalls={streamToolCalls}
          />
        )}
        {activeTab === "timeline" && (
          <TimelineTab events={liveEvents} status={status} />
        )}
        {activeTab === "agents" && <AgentsTab events={liveEvents} />}
        {activeTab === "system" && <SystemTab />}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Tab 1: Pipeline — 5-Phase progress + active agent + tools + thinking
   ═══════════════════════════════════════════════════════════ */

function PipelineTab({
  events,
  status,
  streamThinking,
  streamText,
  streamAgent,
  streamToolCalls,
}: {
  events: WSLiveEvent[];
  status: string;
  streamThinking: string;
  streamText: string;
  streamAgent: string;
  streamToolCalls: StreamToolCall[];
}) {
  const currentPhase = detectPhaseIndex(events);
  const isRunning = status === "running";
  const isDone = status === "complete";
  const thinkingRef = useRef<HTMLPreElement>(null);

  // Auto-scroll thinking
  useEffect(() => {
    if (thinkingRef.current) {
      thinkingRef.current.scrollTop = thinkingRef.current.scrollHeight;
    }
  }, [streamThinking]);

  // Active agents from events
  const activeAgents = useMemo(() => extractActiveAgents(events), [events]);
  const currentAgent = streamAgent
    ? getAgentInfo(streamAgent)
    : activeAgents.length > 0
      ? getAgentInfo(activeAgents[0].role)
      : null;
  const currentAgentRole =
    streamAgent || (activeAgents.length > 0 ? activeAgents[0].role : "");

  // Empty state
  if (events.length === 0 && !isRunning) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-400 px-6">
        <Activity className="w-8 h-8 text-gray-300" />
        <p className="text-xs text-center">
          Görev bekleniyor — sohbetten bir mesaj gönderin
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 p-3 gap-3">
      {/* ── Phase Progress Bar ── */}
      <div className="shrink-0 bg-[#f8f7f4] border border-[#d6d2c2] rounded-lg p-3">
        <div className="flex items-center gap-1">
          {PIPELINE_PHASES.map((phase, idx) => {
            const Icon = phase.icon;
            const isCompleted = isPhaseComplete(idx, currentPhase, status);
            const isCurrent = idx === currentPhase && isRunning;
            const isPending = idx > currentPhase;

            return (
              <div key={phase.id} className="flex items-center flex-1 min-w-0">
                <div className="flex flex-col items-center gap-1 flex-1 min-w-0">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center transition-all duration-300 ${
                      isCompleted
                        ? "bg-emerald-500 text-white"
                        : isCurrent
                          ? "bg-blue-500 text-white ring-2 ring-blue-300 ring-offset-1 animate-pulse"
                          : "bg-gray-200 text-gray-400"
                    }`}
                  >
                    {isCompleted ? (
                      <Check className="w-3.5 h-3.5" />
                    ) : isCurrent ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Icon className="w-3.5 h-3.5" />
                    )}
                  </div>
                  <span
                    className={`text-[9px] text-center leading-tight truncate w-full ${
                      isCurrent
                        ? "text-blue-600 font-semibold"
                        : isCompleted
                          ? "text-emerald-600"
                          : "text-gray-400"
                    }`}
                  >
                    {phase.label}
                  </span>
                </div>
                {idx < PIPELINE_PHASES.length - 1 && (
                  <div
                    className={`h-0.5 w-4 shrink-0 mx-0.5 rounded transition-colors ${
                      isCompleted ? "bg-emerald-400" : "bg-gray-200"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
        {currentPhase >= 0 && isRunning && (
          <p className="text-[10px] text-gray-500 mt-2 text-center">
            {PIPELINE_PHASES[currentPhase]?.description}
          </p>
        )}
        {isDone && (
          <p className="text-[10px] text-emerald-600 mt-2 text-center font-medium">
            ✅ Pipeline tamamlandı
          </p>
        )}
      </div>

      {/* ── Active Agent Indicator ── */}
      {currentAgent && isRunning && (
        <div className="shrink-0 flex items-center gap-2 px-3 py-2 bg-[#f8f7f4] border border-[#d6d2c2] rounded-lg">
          <span className="text-lg">{currentAgent.icon}</span>
          <div className="flex-1 min-w-0">
            <div
              className="text-xs font-semibold"
              style={{ color: currentAgent.color }}
            >
              {currentAgent.name}
            </div>
            <div className="text-[10px] text-gray-500 truncate">
              {activeAgents
                .find((a) => a.role === currentAgentRole)
                ?.lastContent?.slice(0, 80) || "Çalışıyor..."}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <span
              className="h-2 w-2 rounded-full animate-pulse"
              style={{ backgroundColor: currentAgent.color }}
            />
            <span className="text-[9px] text-gray-400">aktif</span>
          </div>
        </div>
      )}

      {/* ── Tool Calls ── */}
      {streamToolCalls.length > 0 && (
        <div className="shrink-0 bg-[#f8f7f4] border border-[#d6d2c2] rounded-lg p-2">
          <div className="text-[10px] text-gray-500 font-medium mb-1.5 flex items-center gap-1">
            <Wrench className="w-3 h-3" />
            Araç Çağrıları ({streamToolCalls.length})
          </div>
          <div className="space-y-1 max-h-24 overflow-y-auto">
            {streamToolCalls.map((tc) => (
              <div
                key={tc.id || tc.name}
                className="flex items-start gap-1.5 text-[11px]"
              >
                {tc.status === "running" ? (
                  <Loader2 className="w-3 h-3 text-amber-500 animate-spin shrink-0 mt-0.5" />
                ) : (
                  <Check className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" />
                )}
                <span className="font-medium text-gray-700">{tc.name}</span>
                {tc.args && (
                  <span className="text-gray-400 truncate text-[9px] font-mono">
                    {tc.args.slice(0, 100)}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Thinking Stream ── */}
      {streamThinking && isRunning && (
        <div className="shrink-0 bg-[#fefce8] border border-[#e5e0b0] rounded-lg p-2 max-h-32">
          <div className="text-[10px] text-amber-600 font-medium mb-1 flex items-center gap-1">
            <Brain className="w-3 h-3" />
            {streamAgent} düşünüyor...
          </div>
          <pre
            ref={thinkingRef}
            className="text-[10px] text-gray-600 font-mono whitespace-pre-wrap break-words max-h-20 overflow-y-auto leading-relaxed"
          >
            {streamThinking.slice(-1000)}
            <span className="animate-pulse text-amber-500">▊</span>
          </pre>
        </div>
      )}

      {/* ── Response Stream ── */}
      {streamText && isRunning && (
        <div className="shrink-0 bg-[#f0fdf4] border border-[#bbf7d0] rounded-lg p-2 max-h-32">
          <div className="text-[10px] text-emerald-600 font-medium mb-1 flex items-center gap-1">
            <MessageSquare className="w-3 h-3" />
            {streamAgent} yanıtlıyor...
          </div>
          <div className="text-[11px] text-gray-700 max-h-20 overflow-y-auto">
            {streamText.slice(-500)}
          </div>
        </div>
      )}

      {/* ── Recent Events (compact) ── */}
      <div className="flex-1 min-h-0 overflow-auto">
        <RecentEventsCompact events={events} />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Recent Events Compact — last N events in a mini-log
   ═══════════════════════════════════════════════════════════ */

function RecentEventsCompact({ events }: { events: WSLiveEvent[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [modalEvent, setModalEvent] = useState<WSLiveEvent | null>(null);
  const recent = events.slice(-30);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  if (recent.length === 0) return null;

  return (
    <div className="space-y-0.5">
      <div className="text-[10px] text-gray-400 font-medium px-1 mb-1 sticky top-0 bg-white">
        Son Olaylar ({events.length})
      </div>
      {recent.map((ev, i) => {
        const info = getAgentInfo(ev.agent);
        const evInfo = EVENT_ICONS[ev.event_type];
        return (
          <div
            key={ev.logKey || `${ev.timestamp}-${i}`}
            className="flex items-start gap-1.5 px-1 py-1 text-[10px] hover:bg-gray-50 rounded transition-colors cursor-pointer select-none"
            onDoubleClick={() => setModalEvent(ev)}
            title="Detay için çift tıkla"
          >
            <span className="shrink-0 mt-0.5">{evInfo?.icon || "📌"}</span>
            <span
              className="shrink-0 font-medium"
              style={{ color: info.color }}
            >
              {ev.agent}
            </span>
            <span className="text-gray-500 truncate flex-1 min-w-0">
              {ev.content.slice(0, 120)}
            </span>
            <span className="text-gray-300 shrink-0 text-[9px]">
              {new Date(ev.timestamp * 1000).toLocaleTimeString("tr-TR", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>
          </div>
        );
      })}
      <div ref={bottomRef} />
      {modalEvent && (
        <DetailModal
          title={`${getAgentInfo(modalEvent.agent).icon} ${modalEvent.agent} — ${EVENT_ICONS[modalEvent.event_type]?.label || modalEvent.event_type}`}
          content={modalEvent.content}
          color={getAgentInfo(modalEvent.agent).color}
          badge={
            EVENT_ICONS[modalEvent.event_type]?.label || modalEvent.event_type
          }
          onClose={() => setModalEvent(null)}
        />
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Tab 2: Timeline — full chronological event log
   ═══════════════════════════════════════════════════════════ */

function TimelineTab({
  events,
  status,
}: {
  events: WSLiveEvent[];
  status: string;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  const uniqueTypes = useMemo(() => {
    const types = new Set(events.map((e) => e.event_type));
    return Array.from(types).sort();
  }, [events]);

  const filtered =
    filter === "all" ? events : events.filter((e) => e.event_type === filter);

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-400 px-6">
        <Clock className="w-6 h-6 text-gray-300" />
        <p className="text-xs text-center">Henüz olay yok</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Filter bar */}
      <div className="shrink-0 flex items-center gap-1 px-3 py-2 border-b border-[#d6d2c2] bg-[#f8f7f4] flex-wrap">
        <button
          onClick={() => setFilter("all")}
          className={`px-2 py-0.5 rounded text-[10px] transition-colors cursor-pointer ${
            filter === "all"
              ? "bg-blue-500 text-white"
              : "bg-gray-100 text-gray-500 hover:bg-gray-200"
          }`}
        >
          Tümü ({events.length})
        </button>
        {uniqueTypes.map((t) => {
          const evInfo = EVENT_ICONS[t];
          const count = events.filter((e) => e.event_type === t).length;
          return (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-2 py-0.5 rounded text-[10px] transition-colors cursor-pointer flex items-center gap-1 ${
                filter === t
                  ? "bg-blue-500 text-white"
                  : "bg-gray-100 text-gray-500 hover:bg-gray-200"
              }`}
            >
              <span>{evInfo?.icon || "📌"}</span>
              {evInfo?.label || t} ({count})
            </button>
          );
        })}
      </div>

      {/* Event list */}
      <div className="flex-1 min-h-0 overflow-auto px-3 py-2 space-y-1">
        {filtered.map((ev, i) => {
          const info = getAgentInfo(ev.agent);
          const evInfo = EVENT_ICONS[ev.event_type];
          return (
            <TimelineEvent
              key={ev.logKey || `${ev.timestamp}-${i}`}
              ev={ev}
              info={info}
              evInfo={evInfo}
            />
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function TimelineEvent({
  ev,
  info,
  evInfo,
}: {
  ev: WSLiveEvent;
  info: ReturnType<typeof getAgentInfo>;
  evInfo: { icon: string; label: string; color: string } | undefined;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const isLong = ev.content.length > 150;

  return (
    <div className="border border-[#e8e5da] rounded-lg bg-white hover:border-[#d6d2c2] transition-colors">
      <button
        onClick={() => isLong && setExpanded(!expanded)}
        onDoubleClick={(e) => {
          e.preventDefault();
          setShowModal(true);
        }}
        className="w-full flex items-start gap-2 px-3 py-2 text-left cursor-pointer select-none"
        title="Detay için çift tıkla"
      >
        <span className="text-sm shrink-0 mt-0.5">{evInfo?.icon || "📌"}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span
              className="text-[10px] font-semibold"
              style={{ color: info.color }}
            >
              {info.icon} {ev.agent}
            </span>
            <span
              className="text-[9px] px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: `${evInfo?.color || "#6b7280"}15`,
                color: evInfo?.color || "#6b7280",
              }}
            >
              {evInfo?.label || ev.event_type}
            </span>
            <span className="text-[9px] text-gray-300 ml-auto shrink-0">
              {new Date(ev.timestamp * 1000).toLocaleTimeString("tr-TR")}
            </span>
          </div>
          <p className="text-[11px] text-gray-600 break-words">
            {expanded ? ev.content : ev.content.slice(0, 150)}
            {isLong && !expanded && "..."}
          </p>
        </div>
        {isLong && (
          <span className="shrink-0 mt-1 text-gray-300">
            {expanded ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
          </span>
        )}
      </button>
      {showModal && (
        <DetailModal
          title={`${info.icon} ${ev.agent} — ${evInfo?.label || ev.event_type}`}
          content={ev.content}
          color={info.color}
          badge={evInfo?.label || ev.event_type}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Tab 3: Agents — active agent cards with event counts
   ═══════════════════════════════════════════════════════════ */

function AgentsTab({ events }: { events: WSLiveEvent[] }) {
  const agents = useMemo(() => extractActiveAgents(events), [events]);

  if (agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-400 px-6">
        <Users className="w-6 h-6 text-gray-300" />
        <p className="text-xs text-center">Henüz aktif agent yok</p>
      </div>
    );
  }

  return (
    <div className="p-3 space-y-2">
      {agents.map((agent) => {
        const info = getAgentInfo(agent.role);
        const agentEvents = events.filter((e) => e.agent === agent.role);
        const toolCalls = agentEvents.filter(
          (e) => e.event_type === "tool_call",
        ).length;
        const thinkingEvents = agentEvents.filter(
          (e) =>
            e.event_type === "thinking" || e.event_type === "agent_thinking",
        ).length;

        return (
          <div
            key={agent.role}
            className="border border-[#d6d2c2] rounded-lg bg-[#f8f7f4] p-3"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">{info.icon}</span>
              <div className="flex-1 min-w-0">
                <div
                  className="text-sm font-semibold"
                  style={{ color: info.color }}
                >
                  {info.name}
                </div>
                <div className="text-[10px] text-gray-500">{agent.role}</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] text-gray-400">
                  {new Date(agent.timestamp * 1000).toLocaleTimeString("tr-TR")}
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-3 text-[10px] text-gray-500">
              <span className="flex items-center gap-1">
                <Zap className="w-3 h-3" />
                {agent.eventCount} olay
              </span>
              {toolCalls > 0 && (
                <span className="flex items-center gap-1">
                  <Wrench className="w-3 h-3" />
                  {toolCalls} araç
                </span>
              )}
              {thinkingEvents > 0 && (
                <span className="flex items-center gap-1">
                  <Brain className="w-3 h-3" />
                  {thinkingEvents} düşünce
                </span>
              )}
            </div>

            {/* Last activity */}
            <div className="mt-2 text-[10px] text-gray-400 truncate">
              Son: {agent.lastContent.slice(0, 100)}
            </div>

            {/* Agent event mini-timeline */}
            <div className="mt-2 flex gap-0.5 flex-wrap">
              {agentEvents.slice(-20).map((ev, i) => {
                const evInfo = EVENT_ICONS[ev.event_type];
                return (
                  <span
                    key={i}
                    className="w-4 h-4 rounded flex items-center justify-center text-[8px]"
                    style={{
                      backgroundColor: `${evInfo?.color || "#6b7280"}15`,
                    }}
                    title={`${ev.event_type}: ${ev.content.slice(0, 50)}`}
                  >
                    {evInfo?.icon || "·"}
                  </span>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Tab 4: System — lazy-loaded monitoring panels
   ═══════════════════════════════════════════════════════════ */

function SystemTab() {
  // Lazy import to avoid circular deps
  const [panels, setPanels] = useState<{
    SystemStatsPanel: React.ComponentType;
    AnomalyPanel: React.ComponentType;
    HeartbeatPanel: React.ComponentType;
  } | null>(null);

  useEffect(() => {
    import("./monitoring-panels").then((m) => {
      setPanels({
        SystemStatsPanel: m.SystemStatsPanel,
        AnomalyPanel: m.AnomalyPanel,
        HeartbeatPanel: m.HeartbeatPanel,
      });
    });
  }, []);

  if (!panels) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <panels.SystemStatsPanel />
      <panels.AnomalyPanel />
      <panels.HeartbeatPanel />
    </div>
  );
}
