"use client";

/**
 * Singleton WebSocket store — shared across all components.
 * Prevents multiple WS connections; all panels read from the same event stream.
 */

import type { WSLiveEvent } from "./types";

type Status = "idle" | "connecting" | "running" | "complete" | "error";
type Listener = () => void;

interface WSStore {
  status: Status;
  liveEvents: WSLiveEvent[];
  listeners: Set<Listener>;
}

const store: WSStore = {
  status: "idle",
  liveEvents: [],
  listeners: new Set(),
};

function notify() {
  store.listeners.forEach((fn) => fn());
}

export function getWSSnapshot() {
  return { status: store.status, liveEvents: store.liveEvents };
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
  store.liveEvents = events;
  notify();
}

export function pushWSLiveEvent(event: WSLiveEvent) {
  store.liveEvents = [...store.liveEvents, event];
  notify();
}

export function clearWSLiveEvents() {
  store.liveEvents = [];
  notify();
}
