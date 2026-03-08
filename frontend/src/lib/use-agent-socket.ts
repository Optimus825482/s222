"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  WSMessage,
  WSLiveEvent,
  WSStreamEvent,
  Thread,
  PipelineType,
} from "./types";
import { useAuth } from "@/lib/auth";
import { setWSStatus, pushWSLiveEvent, clearWSLiveEvents } from "./ws-store";

const INITIAL_RECONNECT_MS = 1_000;
const MAX_RECONNECT_MS = 30_000;
const MAX_RECONNECT_ATTEMPTS = 10;
const MAX_LIVE_EVENTS = 500;

function toLiveEventWithKey(event: WSLiveEvent): WSLiveEvent {
  if (event.logKey) return event;

  return {
    ...event,
    logKey: `${event.timestamp}:${event.agent}:${event.event_type}`,
  };
}

interface UseAgentSocketOptions {
  /** When false, does not connect (avoids "closed before connection" on redirect). */
  enabled?: boolean;
  onLiveEvent?: (event: WSLiveEvent) => void;
  onStreamEvent?: (event: WSStreamEvent) => void;
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
  const mountedRef = useRef(true);

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

    // Build base URL (never includes query params)
    let baseUrl =
      currentWsUrlRef.current ||
      process.env.NEXT_PUBLIC_WS_URL ||
      "ws://localhost:8001/ws/chat";

    // Strip any existing query params from base
    const qIdx = baseUrl.indexOf("?");
    if (qIdx !== -1) baseUrl = baseUrl.slice(0, qIdx);

    // URL is used as-is from env var — no path rewriting

    // Store clean base URL (no token, no query params)
    currentWsUrlRef.current = baseUrl;

    // Build connection URL with token
    let connectUrl = baseUrl;
    const token = getToken();
    if (token) {
      connectUrl += "?token=" + encodeURIComponent(token);
    }
    const ws = new WebSocket(connectUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      reconnectAttempts.current = 0;
      setStatus("idle");
      setWSStatus("idle");
    };

    ws.onmessage = (ev) => {
      if (!mountedRef.current) return;
      try {
        const msg: WSMessage = JSON.parse(ev.data);

        switch (msg.type) {
          case "live_event":
            {
              const nextEvent = toLiveEventWithKey(msg);
              setLiveEvents((prev) => {
                const next = prev.concat(nextEvent);
                return next.length > MAX_LIVE_EVENTS
                  ? next.slice(next.length - MAX_LIVE_EVENTS)
                  : next;
              });
              pushWSLiveEvent(nextEvent);
              optsRef.current.onLiveEvent?.(nextEvent);
            }
            break;
          case "monitor_start":
            setStatus("running");
            setLiveEvents([]);
            setWSStatus("running");
            clearWSLiveEvents();
            optsRef.current.onStatusChange?.("running");
            break;
          case "monitor_complete":
            setStatus("complete");
            setWSStatus("complete");
            optsRef.current.onStatusChange?.("complete");
            break;
          case "monitor_error":
            setStatus("error");
            setWSStatus("error");
            optsRef.current.onError?.(msg.message);
            optsRef.current.onStatusChange?.("error");
            break;
          case "result":
            optsRef.current.onResult?.(msg.thread_id, msg.result, msg.thread);
            break;
          case "error":
            setStatus("error");
            setWSStatus("error");
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
          case "stream_event":
            optsRef.current.onStreamEvent?.(msg as WSStreamEvent);
            break;
        }
      } catch {
        /* ignore parse errors */
      }
    };

    ws.onclose = (ev) => {
      if (!mountedRef.current) return;
      setStatus("idle");
      setWSStatus("idle");

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

      // No URL rewriting on reconnect

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
      if (!mountedRef.current) return;
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
    mountedRef.current = true;
    if (enabled) {
      connect();
    } else {
      clearReconnectTimer();
      if (wsRef.current) {
        if (
          wsRef.current.readyState === WebSocket.OPEN ||
          wsRef.current.readyState === WebSocket.CLOSING
        ) {
          wsRef.current.close();
        } else {
          wsRef.current.onopen = null;
          wsRef.current.onclose = null;
          wsRef.current.onmessage = null;
          wsRef.current.onerror = null;
        }
        wsRef.current = null;
      }
    }
    return () => {
      mountedRef.current = false;
      clearReconnectTimer();
      const ws = wsRef.current;
      if (ws) {
        if (
          ws.readyState === WebSocket.OPEN ||
          ws.readyState === WebSocket.CLOSING
        ) {
          ws.close();
        } else {
          ws.onopen = null;
          ws.onclose = null;
          ws.onmessage = null;
          ws.onerror = null;
        }
        wsRef.current = null;
      }
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
