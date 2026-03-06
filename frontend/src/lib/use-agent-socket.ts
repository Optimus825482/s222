"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WSMessage, WSLiveEvent, Thread, PipelineType } from "./types";

const INITIAL_RECONNECT_MS = 1_000;
const MAX_RECONNECT_MS = 30_000;
const MAX_RECONNECT_ATTEMPTS = 10;

interface UseAgentSocketOptions {
  onLiveEvent?: (event: WSLiveEvent) => void;
  onResult?: (threadId: string, result: string, thread: Thread) => void;
  onError?: (message: string) => void;
  onStatusChange?: (
    status: "idle" | "connecting" | "running" | "complete" | "error",
  ) => void;
}

export function useAgentSocket(opts: UseAgentSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<
    "idle" | "connecting" | "running" | "complete" | "error"
  >("idle");
  const [liveEvents, setLiveEvents] = useState<WSLiveEvent[]>([]);
  const optsRef = useRef(opts);
  optsRef.current = opts;

  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimer.current !== null) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
  }, []);

  const getToken = useCallback(() => {
    try {
      const stored = typeof window !== "undefined" ? localStorage.getItem("ops-center-auth") : null;
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
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    let wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws/chat";
    const token = getToken();
    if (token) {
      wsUrl += (wsUrl.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(token);
    }
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
        }
      } catch {
        /* ignore parse errors */
      }
    };

    ws.onclose = () => {
      setStatus("idle");

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
  }, [clearReconnectTimer, getToken]);

  /** Manually reset backoff counter and reconnect */
  const reconnect = useCallback(() => {
    clearReconnectTimer();
    wsRef.current?.close();
    reconnectAttempts.current = 0;
    connect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearReconnectTimer, connect]);

  useEffect(() => {
    connect();
    return () => {
      clearReconnectTimer();
      wsRef.current?.close();
    };
  }, [connect, clearReconnectTimer]);

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

  return { status, liveEvents, sendMessage, stop, reconnect };
}
