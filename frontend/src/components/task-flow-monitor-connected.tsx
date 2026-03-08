"use client";

import { useSyncExternalStore } from "react";
import { getWSSnapshot, subscribeWS } from "@/lib/ws-store";
import { TaskFlowMonitor } from "./task-flow-monitor";

/**
 * TaskFlowMonitor wired to global WebSocket store.
 * When opened as "Görev Merkezi", shows the same live event stream as the chat panel.
 */
export function TaskFlowMonitorConnected() {
  const snapshot = useSyncExternalStore(
    subscribeWS,
    getWSSnapshot,
    getWSSnapshot,
  );
  return (
    <TaskFlowMonitor
      thread={snapshot.activeThread}
      liveEvents={snapshot.liveEvents}
    />
  );
}
