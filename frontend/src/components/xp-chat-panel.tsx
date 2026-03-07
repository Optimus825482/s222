"use client";

import { useState, useEffect } from "react";
import { useAgentSocket } from "@/lib/use-agent-socket";
import { useAuth } from "@/lib/auth";
import type { Thread, PipelineType } from "@/lib/types";
import { PipelineSelector } from "@/components/pipeline-selector";
import { ChatArea } from "@/components/chat-area";
import { ChatInput } from "@/components/chat-input";
import { LiveEventLog } from "@/components/live-event-log";
import { api } from "@/lib/api";
import { consumePendingThread } from "@/lib/ws-store";

export default function ChatDesktopPanel() {
  const { user } = useAuth();
  const [thread, setThread] = useState<Thread | null>(null);
  const [pipeline, setPipeline] = useState<PipelineType>("auto");
  const [lastError, setLastError] = useState<string | null>(null);

  const { status, liveEvents, sendMessage, stop } = useAgentSocket({
    enabled: !!user,
    onResult: (_tid, _result, updatedThread) => {
      setThread(updatedThread);
      setLastError(null);
    },
    onError: (msg) => setLastError(msg),
  });

  // On mount: check if a pending thread was set before this panel mounted
  useEffect(() => {
    const pending = consumePendingThread();
    if (pending) {
      api
        .getThread(pending)
        .then((loaded) => setThread(loaded))
        .catch((err) =>
          console.error("[ChatDesktopPanel] pending thread load error:", err),
        );
    }
  }, []);

  // Listen for "open-thread" custom events from XpSessionsPanel (when already mounted)
  useEffect(() => {
    const handler = async (e: Event) => {
      const threadId = (e as CustomEvent<string>).detail;
      if (!threadId) return;
      try {
        const loaded = await api.getThread(threadId);
        setThread(loaded);
      } catch (err) {
        console.error("[ChatDesktopPanel] load thread error:", err);
      }
    };
    window.addEventListener("open-thread", handler);
    return () => window.removeEventListener("open-thread", handler);
  }, []);

  const isProcessing = status === "running" || status === "connecting";

  const handleSend = (message: string) => {
    sendMessage(message, thread?.id, pipeline);
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center gap-2 shrink-0 px-2 py-1 border-b border-slate-700/50">
        <div className="flex-1 min-w-0">
          <PipelineSelector selected={pipeline} onSelect={setPipeline} />
        </div>
      </div>
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        <ChatArea thread={thread} isProcessing={isProcessing} status={status} />
      </div>
      {lastError && (
        <div className="shrink-0 px-3 py-1.5 bg-red-950/50 border-t border-red-900/50 text-red-300 text-xs flex items-center justify-between">
          <span className="truncate">{lastError}</span>
          <button
            onClick={() => setLastError(null)}
            className="text-red-400 hover:text-red-200 text-xs px-1"
            aria-label="Kapat"
          >
            ✕
          </button>
        </div>
      )}
      <div className="shrink-0">
        <ChatInput
          onSend={handleSend}
          onStop={stop}
          isProcessing={isProcessing}
        />
      </div>
      {liveEvents.length > 0 && (
        <div className="shrink-0 max-h-24 overflow-y-auto border-t border-slate-700/50">
          <LiveEventLog events={liveEvents} status={status} />
        </div>
      )}
    </div>
  );
}
