"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Thread, WSLiveEvent, AgentEvent } from "@/lib/types";
import type { AgentDirectMessage } from "@/lib/types";
import { api } from "@/lib/api";
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
  const [chatTab, setChatTab] = useState<"events" | "messages">("events");

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
      {/* Header with tabs */}
      <div className="flex items-center gap-2 px-3 lg:px-4 py-2 border-b border-border">
        <MessageSquare className="w-4 h-4 text-slate-300" aria-hidden="true" />
        <div className="flex gap-1">
          <button
            onClick={() => setChatTab("events")}
            className={`px-2 py-0.5 text-[10px] font-medium rounded transition-colors ${
              chatTab === "events"
                ? "bg-blue-500/20 text-blue-400"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Olaylar ({interEvents.length + liveInterAgent.length})
          </button>
          <button
            onClick={() => setChatTab("messages")}
            className={`px-2 py-0.5 text-[10px] font-medium rounded transition-colors ${
              chatTab === "messages"
                ? "bg-purple-500/20 text-purple-400"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Mesajlar
          </button>
        </div>
      </div>

      {chatTab === "messages" ? (
        <DirectMessagePanel />
      ) : (
        <>
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
        </>
      )}

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

function DirectMessagePanel() {
  const [messages, setMessages] = useState<AgentDirectMessage[]>([]);
  const [sender, setSender] = useState("orchestrator");
  const [receiver, setReceiver] = useState("thinker");
  const [content, setContent] = useState("");
  const [sending, setSending] = useState(false);

  const loadMessages = useCallback(async () => {
    try {
      const res = await api.getAgentMessages(30);
      setMessages(res.messages);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    loadMessages();
    const interval = setInterval(loadMessages, 10000);
    return () => clearInterval(interval);
  }, [loadMessages]);

  const handleSend = async () => {
    if (!content.trim() || sending) return;
    try {
      setSending(true);
      await api.sendAgentMessage(sender, receiver, content.trim());
      setContent("");
      await loadMessages();
    } catch {
      // silent
    } finally {
      setSending(false);
    }
  };

  const roles = Object.keys(AGENT_ROLE_ICONS);

  return (
    <div className="flex flex-col h-full">
      {/* Messages list */}
      <div
        className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5"
        role="log"
        aria-label="Ajan mesajları"
      >
        {messages.length === 0 && (
          <div className="text-center text-xs text-slate-600 py-8">
            Henüz doğrudan mesaj yok
          </div>
        )}
        {messages.map((msg) => {
          const senderInfo = getAgentInfo(msg.sender);
          const receiverInfo = getAgentInfo(msg.receiver);
          const SenderIcon = AGENT_ROLE_ICONS[msg.sender] ?? Settings;
          return (
            <div
              key={msg.id}
              className="flex gap-2 p-1.5 rounded hover:bg-white/5 transition-colors"
            >
              <div className="flex-shrink-0 mt-0.5">
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center"
                  style={{
                    backgroundColor: senderInfo.color + "20",
                    color: senderInfo.color,
                  }}
                >
                  <SenderIcon className="w-3 h-3" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1 mb-0.5">
                  <span
                    className="text-[10px] font-semibold"
                    style={{ color: senderInfo.color }}
                  >
                    {senderInfo.name}
                  </span>
                  <span className="text-[9px] text-slate-600">→</span>
                  <span
                    className="text-[10px] font-semibold"
                    style={{ color: receiverInfo.color }}
                  >
                    {receiverInfo.name}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 leading-snug break-words">
                  {msg.content}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Send form */}
      <div className="border-t border-border px-3 py-2 space-y-1.5">
        <div className="flex gap-1.5">
          <select
            value={sender}
            onChange={(e) => setSender(e.target.value)}
            className="flex-1 bg-white/5 border border-border rounded px-1.5 py-1 text-[10px] text-slate-300 focus:outline-none focus:border-blue-500/50"
            aria-label="Gönderen ajan"
          >
            {roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <span className="text-[10px] text-slate-600 self-center">→</span>
          <select
            value={receiver}
            onChange={(e) => setReceiver(e.target.value)}
            className="flex-1 bg-white/5 border border-border rounded px-1.5 py-1 text-[10px] text-slate-300 focus:outline-none focus:border-blue-500/50"
            aria-label="Alıcı ajan"
          >
            {roles
              .filter((r) => r !== sender)
              .map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
          </select>
        </div>
        <div className="flex gap-1.5">
          <input
            type="text"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend();
            }}
            placeholder="Mesaj yaz..."
            className="flex-1 bg-white/5 border border-border rounded px-2 py-1 text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
            aria-label="Mesaj içeriği"
          />
          <button
            onClick={handleSend}
            disabled={sending || !content.trim()}
            className="px-2.5 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 text-[10px] font-medium rounded border border-blue-500/20 transition-colors disabled:opacity-50"
          >
            {sending ? "..." : "Gönder"}
          </button>
        </div>
      </div>
    </div>
  );
}

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
