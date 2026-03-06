"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WSMessage, WSLiveEvent, Thread, PipelineType } from "./types";
import { useAuth } from "@/lib/auth";

const INITIAL_RECONNECT_MS = 1_000;
const MAX_RECONNECT_MS = 30_000;
const MAX_RECONNECT_ATTEMPTS = 10;

interface UseAgentSocketOptions {
  /** When false, does not connect (avoids "closed before connection" on redirect). */
  enabled?: boolean;
  onLiveEvent?: (event: WSLiveEvent) => void;
  onResult?: (threadId: string, result: string, thread: Thread) => void;
  onError?: (message: string) => void;
  onStatusChange?: (
    status: "idle" | "connecting" | "running" | "complete" | "error",
  ) => void;
  onOrchestratorChatReply?: (content: string, isStatus: boolean) => void;
}

export function useAgentSocket(opts: UseAgentSocketOptions = {}) {
  const enabled = opts.enabled ?? true;
  const optsRef = useRef(opts);
  optsRef.current = opts;

  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<
    "idle" | "connecting" | "running" | "complete" | "error"
  >("idle");
  const [liveEvents, setLiveEvents] = useState<WSLiveEvent[]>([]);

  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentWsUrlRef = useRef<string | null>(null);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimer.current !== null) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
  }, []);

  const getToken = useCallback(() => {
    try {
      const stored =
        typeof window !== "undefined"
          ? localStorage.getItem("ops-center-auth")
          : null;
      if (stored) {
        const parsed = JSON.parse(stored);
        return parsed?.state?.user?.token ?? "";
      }
    } catch {
      /* ignore */
    }
    return "";
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    let wsUrl =
      currentWsUrlRef.current ||
      process.env.NEXT_PUBLIC_WS_URL ||
      "ws://localhost:8001/ws/chat";
    if (wsUrl.includes("/ws/chat") && !wsUrl.includes("/api/ws/chat")) {
      wsUrl = wsUrl.replace("/ws/chat", "/api/ws/chat");
    }
    const token = getToken();
    if (token) {
      wsUrl +=
        (wsUrl.includes("?") ? "&" : "?") +
        "token=" +
        encodeURIComponent(token);
    }
    currentWsUrlRef.current = wsUrl;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      // Reset backoff on successful connection
      reconnectAttempts.current = 0;
      setStatus("idle");
    };

    ws.onmessage = (ev) => {
      try {
        const msg: WSMessage = JSON.parse(ev.data);

        switch (msg.type) {
          case "live_event":
            setLiveEvents((prev) => [...prev, msg]);
            optsRef.current.onLiveEvent?.(msg);
            break;
          case "monitor_start":
            setStatus("running");
            setLiveEvents([]);
            optsRef.current.onStatusChange?.("running");
            break;
          case "monitor_complete":
            setStatus("complete");
            optsRef.current.onStatusChange?.("complete");
            break;
          case "monitor_error":
            setStatus("error");
            optsRef.current.onError?.(msg.message);
            optsRef.current.onStatusChange?.("error");
            break;
          case "result":
            optsRef.current.onResult?.(msg.thread_id, msg.result, msg.thread);
            break;
          case "error":
            setStatus("error");
            optsRef.current.onError?.(msg.message);
            optsRef.current.onStatusChange?.("error");
            break;
          case "orchestrator_chat_reply":
            if ("content" in msg && typeof msg.content === "string") {
              optsRef.current.onOrchestratorChatReply?.(
                msg.content,
                !!("is_status" in msg && msg.is_status),
              );
            }
            break;
        }
      } catch {
        /* ignore parse errors */
      }
    };

    ws.onclose = (ev) => {
      setStatus("idle");

      // 4001 = backend auth rejected. Do not reconnect-loop with stale token.
      if (ev.code === 4001) {
        try {
          localStorage.removeItem("ops-center-auth");
          sessionStorage.removeItem("auth:validated-token");
        } catch {
          /* ignore */
        }
        try {
          useAuth.setState({ user: null });
        } catch {
          /* ignore */
        }
        clearReconnectTimer();
        return;
      }

      // Fallback for reverse proxies that expose websocket under /api/ws/chat.
      if (
        reconnectAttempts.current === 0 &&
        currentWsUrlRef.current?.includes("/ws/chat")
      ) {
        currentWsUrlRef.current = currentWsUrlRef.current.replace(
          "/ws/chat",
          "/api/ws/chat",
        );
      }

      if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) return;

      const delay = Math.min(
        INITIAL_RECONNECT_MS * 2 ** reconnectAttempts.current,
        MAX_RECONNECT_MS,
      );
      reconnectAttempts.current += 1;

      clearReconnectTimer();
      reconnectTimer.current = setTimeout(() => connect(), delay);
    };

    ws.onerror = () => {
      setStatus("error");
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearReconnectTimer, getToken, enabled]);

  /** Manually reset backoff counter and reconnect */
  const reconnect = useCallback(() => {
    clearReconnectTimer();
    wsRef.current?.close();
    reconnectAttempts.current = 0;
    connect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearReconnectTimer, connect]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      clearReconnectTimer();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    }
    return () => {
      clearReconnectTimer();
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect, clearReconnectTimer, enabled]);

  const sendMessage = useCallback(
    (
      message: string,
      threadId?: string,
      pipelineType: PipelineType = "auto",
    ) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        connect();
        // Retry after connection
        setTimeout(() => sendMessage(message, threadId, pipelineType), 500);
        return;
      }
      setStatus("connecting");
      setLiveEvents([]);

      // Get user_id from localStorage
      let userId = "";
      try {
        const stored = localStorage.getItem("ops-center-auth");
        if (stored) {
          const parsed = JSON.parse(stored);
          userId = parsed?.state?.user?.user_id || "";
        }
      } catch {
        /* ignore */
      }

      ws.send(
        JSON.stringify({
          type: "chat",
          message,
          thread_id: threadId,
          pipeline_type: pipelineType,
          user_id: userId,
        }),
      );
    },
    [connect],
  );

  const stop = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: "stop" }));
  }, []);

  const sendOrchestratorChat = useCallback(
    (message: string, threadId?: string) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      ws.send(
        JSON.stringify({
          type: "orchestrator_chat",
          message: message.trim(),
          thread_id: threadId,
        }),
      );
    },
    [],
  );

  return {
    status,
    liveEvents,
    sendMessage,
    sendOrchestratorChat,
    stop,
    reconnect,
  };
}
