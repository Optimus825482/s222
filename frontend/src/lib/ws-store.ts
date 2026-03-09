"use client";

/**
 * Singleton WebSocket store — shared across all components.
 * Prevents multiple WS connections; all panels read from the same event stream.
 * Also holds a pending thread ID for cross-panel navigation.
 * Stream state (thinking, text, toolCalls) is stored here so the task monitor can consume it.
 */

import type { WSLiveEvent, Thread } from "./types";

type Status = "idle" | "connecting" | "running" | "complete" | "error";
type Listener = () => void;

const MAX_LIVE_EVENTS = 500;

export interface StreamToolCall {
  id: string;
  name: string;
  args: string;
  status: "running" | "complete";
}

interface WSStore {
  status: Status;
  liveEvents: WSLiveEvent[];
  pendingThreadId: string | null;
  activeThread: Thread | null;
  /* Stream state — consumed by task monitor */
  streamThinking: string;
  streamText: string;
  streamAgent: string;
  streamToolCalls: StreamToolCall[];
  listeners: Set<Listener>;
}

const store: WSStore = {
  status: "idle",
  liveEvents: [],
  pendingThreadId: null,
  activeThread: null,
  streamThinking: "",
  streamText: "",
  streamAgent: "",
  streamToolCalls: [],
  listeners: new Set(),
};

/** Cached snapshot — only replaced when notify() fires */
let _snapshot = {
  status: store.status,
  liveEvents: store.liveEvents,
  activeThread: store.activeThread,
  streamThinking: store.streamThinking,
  streamText: store.streamText,
  streamAgent: store.streamAgent,
  streamToolCalls: store.streamToolCalls,
};

function notify() {
  _snapshot = {
    status: store.status,
    liveEvents: store.liveEvents,
    activeThread: store.activeThread,
    streamThinking: store.streamThinking,
    streamText: store.streamText,
    streamAgent: store.streamAgent,
    streamToolCalls: store.streamToolCalls,
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

/* ── Stream state for task monitor ── */

export function setStreamThinking(val: string) {
  store.streamThinking = val;
  notify();
}

export function appendStreamThinking(delta: string) {
  store.streamThinking += delta;
  notify();
}

export function setStreamText(val: string) {
  store.streamText = val;
  notify();
}

export function appendStreamText(delta: string) {
  store.streamText += delta;
  notify();
}

export function setStreamAgent(agent: string) {
  store.streamAgent = agent;
  notify();
}

export function setStreamToolCalls(calls: StreamToolCall[]) {
  store.streamToolCalls = calls;
  notify();
}

export function pushStreamToolCall(call: StreamToolCall) {
  store.streamToolCalls = [...store.streamToolCalls, call];
  notify();
}

export function updateStreamToolCall(
  id: string,
  update: Partial<StreamToolCall>,
) {
  store.streamToolCalls = store.streamToolCalls.map((tc) =>
    tc.id === id ? { ...tc, ...update } : tc,
  );
  notify();
}

export function appendStreamToolCallArgs(id: string, argsDelta: string) {
  store.streamToolCalls = store.streamToolCalls.map((tc) =>
    tc.id === id ? { ...tc, args: tc.args + argsDelta } : tc,
  );
  notify();
}

export function clearStreamState() {
  store.streamThinking = "";
  store.streamText = "";
  store.streamAgent = "";
  store.streamToolCalls = [];
  notify();
}
