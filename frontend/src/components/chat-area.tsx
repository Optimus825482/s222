"use client";

import { useEffect, useRef } from "react";
import type { Thread, AgentEvent } from "@/lib/types";
import { getAgentInfo } from "@/lib/agents";
import { Brain, CheckCircle, Clock, Coins } from "lucide-react";

interface Props {
  thread: Thread | null;
}

const CHAT_EVENTS = new Set(["user_message", "agent_response", "error"]);

export function ChatArea({ thread }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread?.events?.length]);

  if (!thread || !thread.events.length) {
    return <WelcomeScreen />;
  }

  const chatEvents = thread.events.filter((e) => CHAT_EVENTS.has(e.event_type));

  return (
    <div
      className="flex-1 overflow-y-auto px-3 md:px-6 py-4 space-y-3"
      role="log"
      aria-label="Sohbet geçmişi"
      aria-live="polite"
    >
      {chatEvents.map((event) => (
        <ChatBubble key={event.id} event={event} thread={thread} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function WelcomeScreen() {
  const hints = [
    { label: "Derin Araştırma", desc: "Kapsamlı analiz" },
    { label: "Paralel", desc: "Hızlı çoklu agent" },
    { label: "Uzlaşı", desc: "Ortak karar" },
    { label: "Fikir→Proje", desc: "Plan oluştur" },
    { label: "Beyin Fırtınası", desc: "Çok yönlü tartışma" },
  ];

  return (
    <div className="flex-1 flex items-center justify-center px-4">
      <div className="text-center max-w-sm">
        <Brain
          className="w-10 h-10 md:w-12 md:h-12 mx-auto mb-4 text-pink-400"
          aria-hidden="true"
        />
        <h1 className="text-lg md:text-xl font-bold text-slate-200 mb-2">
          Multi-Agent Ops Center
        </h1>
        <p className="text-sm text-slate-500 mb-6">
          Görev gönder — orchestrator analiz edip specialist agent&apos;lara
          yönlendirsin.
        </p>
        <div className="flex gap-2 justify-center flex-wrap">
          {hints.map((h) => (
            <span
              key={h.label}
              className="px-3 py-1.5 rounded-full bg-surface-overlay text-xs text-slate-400 border border-border"
            >
              {h.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function ChatBubble({ event, thread }: { event: AgentEvent; thread: Thread }) {
  if (event.event_type === "user_message") {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[85%] md:max-w-[70%] bg-blue-600/20 border border-blue-500/30 rounded-2xl rounded-br-md px-3 md:px-4 py-3">
          <div className="text-[10px] text-blue-400 font-semibold mb-1">
            SEN
          </div>
          <div className="text-sm text-slate-200 whitespace-pre-wrap break-words">
            {event.content}
          </div>
        </div>
      </div>
    );
  }

  if (event.event_type === "error") {
    return (
      <div className="animate-fade-in" role="alert">
        <div className="bg-red-950/30 border border-red-900/40 rounded-xl px-3 md:px-4 py-3 text-sm text-red-300">
          {event.content}
        </div>
      </div>
    );
  }

  const role = event.agent_role ?? "orchestrator";
  const info = getAgentInfo(role);
  const isFinal = role === "orchestrator" && event.content.length > 100;

  // Find matching task for metadata
  const lastTask = thread?.tasks?.length
    ? thread.tasks[thread.tasks.length - 1]
    : null;

  return (
    <div className="animate-slide-up">
      <div
        className={`rounded-2xl rounded-bl-md px-3 md:px-4 py-3 max-w-[100%] md:max-w-[85%] ${
          isFinal
            ? "bg-surface-overlay border-2 border-opacity-40"
            : "bg-surface-raised border border-border"
        }`}
        style={{ borderColor: isFinal ? info.color : undefined }}
      >
        {/* Agent header */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg" aria-hidden="true">
            {info.icon}
          </span>
          <span className="text-xs font-bold" style={{ color: info.color }}>
            {info.name}
          </span>
          {isFinal && (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-green-900/40 text-green-400 border border-green-800/40 inline-flex items-center gap-0.5">
              <CheckCircle className="w-3 h-3" aria-hidden="true" />
              SONUÇ
            </span>
          )}
        </div>

        {/* Content */}
        <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed break-words">
          {event.content}
        </div>

        {/* Mobile-friendly metadata footer for final results */}
        {isFinal && lastTask && (
          <div className="mt-3 pt-2 border-t border-border/50 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-500">
            {lastTask.total_tokens > 0 && (
              <span className="inline-flex items-center gap-0.5">
                <Coins className="w-3 h-3" aria-hidden="true" />
                {lastTask.total_tokens.toLocaleString("tr-TR")} token
              </span>
            )}
            {lastTask.total_latency_ms > 0 && (
              <span className="inline-flex items-center gap-0.5">
                <Clock className="w-3 h-3" aria-hidden="true" />
                {(lastTask.total_latency_ms / 1000).toFixed(1)}s
              </span>
            )}
            {lastTask.sub_tasks?.length > 0 && (
              <span className="inline-flex items-center gap-0.5">
                <Brain className="w-3 h-3" aria-hidden="true" />
                {lastTask.sub_tasks.length} agent
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
