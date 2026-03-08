"use client";

/**
 * Singleton WebSocket store — shared across all components.
 * Prevents multiple WS connections; all panels read from the same event stream.
 * Also holds a pending thread ID for cross-panel navigation.
 */

import type { WSLiveEvent, Thread } from "./types";

type Status = "idle" | "connecting" | "running" | "complete" | "error";
type Listener = () => void;

const MAX_LIVE_EVENTS = 500;

interface WSStore {
  status: Status;
  liveEvents: WSLiveEvent[];
  pendingThreadId: string | null;
  activeThread: Thread | null;
  listeners: Set<Listener>;
}

const store: WSStore = {
  status: "idle",
  liveEvents: [],
  pendingThreadId: null,
  activeThread: null,
  listeners: new Set(),
};

/** Cached snapshot — only replaced when notify() fires */
let _snapshot = {
  status: store.status,
  liveEvents: store.liveEvents,
  activeThread: store.activeThread,
};

function notify() {
  _snapshot = {
    status: store.status,
    liveEvents: store.liveEvents,
    activeThread: store.activeThread,
  };
  store.listeners.forEach((fn) => fn());
}

export function getWSSnapshot() {
  return _snapshot;
}

export function subscribeWS(listener: Listener): () => void {
  store.listeners.add(listener);
  return () => {
    store.listeners.delete(listener);
  };
}

export function setWSStatus(s: Status) {
  store.status = s;
  notify();
}

export function setWSLiveEvents(events: WSLiveEvent[]) {
  store.liveEvents = events.slice(-MAX_LIVE_EVENTS);
  notify();
}

export function pushWSLiveEvent(event: WSLiveEvent) {
  store.liveEvents.push(event);
  if (store.liveEvents.length > MAX_LIVE_EVENTS) {
    store.liveEvents = store.liveEvents.slice(-MAX_LIVE_EVENTS);
  }
  notify();
}

export function clearWSLiveEvents() {
  store.liveEvents = [];
  notify();
}

/* ── Pending thread for cross-panel navigation ── */

/** Set a pending thread ID for ChatDesktopPanel to pick up on mount */
export function setPendingThread(threadId: string | null) {
  store.pendingThreadId = threadId;
  notify();
}

/** Consume the pending thread ID (returns it and clears) */
export function consumePendingThread(): string | null {
  const id = store.pendingThreadId;
  if (id) {
    store.pendingThreadId = null;
    // no notify needed — consumer already read it
  }
  return id;
}

/* ── Active thread for cross-panel data sharing ── */

/** Set the active thread so other panels (Görev Merkezi etc.) can read it */
export function setActiveThread(thread: Thread | null) {
  store.activeThread = thread;
  notify();
}

/** Get the current active thread */
export function getActiveThread(): Thread | null {
  return store.activeThread;
}
