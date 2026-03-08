"use client";

import { useEffect, useSyncExternalStore } from "react";

import { api } from "@/lib/api";
import type {
  AgentHealth,
  AnomalyReport,
  AutonomousConversation,
  SystemStats,
} from "@/lib/types";

interface HeartbeatTaskSummary {
  name: string;
  frequency: string;
  enabled: boolean;
  last_run: string | null;
  run_count: number;
  error_count: number;
}

interface HeartbeatEventSummary {
  task: string;
  timestamp: string;
  result?: unknown;
  error?: string;
}

interface MonitoringSnapshot {
  agentHealth: AgentHealth[];
  systemStats: SystemStats | null;
  anomalies: AnomalyReport | null;
  autonomousConversations: AutonomousConversation[];
  heartbeatTasks: HeartbeatTaskSummary[];
  heartbeatEvents: HeartbeatEventSummary[];
  sharedLoading: boolean;
  heartbeatLoading: boolean;
  autonomousLoading: boolean;
  sharedError: string | null;
  heartbeatError: string | null;
  autonomousError: string | null;
}

const SHARED_INTERVAL_MS = 30_000;
const HEARTBEAT_INTERVAL_MS = 60_000;

const listeners = new Set<() => void>();

const store: MonitoringSnapshot = {
  agentHealth: [],
  systemStats: null,
  anomalies: null,
  autonomousConversations: [],
  heartbeatTasks: [],
  heartbeatEvents: [],
  sharedLoading: true,
  heartbeatLoading: true,
  autonomousLoading: true,
  sharedError: null,
  heartbeatError: null,
  autonomousError: null,
};

let snapshot: MonitoringSnapshot = { ...store };
let subscriberCount = 0;
let sharedTimer: ReturnType<typeof setInterval> | null = null;
let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let visibilityHandler: (() => void) | null = null;
let sharedInFlight: Promise<void> | null = null;
let heartbeatInFlight: Promise<void> | null = null;
let autonomousInFlight: Promise<void> | null = null;

function notify() {
  snapshot = {
    ...store,
    agentHealth: [...store.agentHealth],
    autonomousConversations: [...store.autonomousConversations],
    heartbeatTasks: [...store.heartbeatTasks],
    heartbeatEvents: [...store.heartbeatEvents],
  };
  listeners.forEach((listener) => listener());
}

function getSnapshot(): MonitoringSnapshot {
  return snapshot;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function isDocumentHidden(): boolean {
  return (
    typeof document !== "undefined" && document.visibilityState !== "visible"
  );
}

async function refreshSharedData(): Promise<void> {
  if (sharedInFlight) {
    return sharedInFlight;
  }

  sharedInFlight = (async () => {
    try {
      const [agentHealth, systemStats, anomalies] = await Promise.all([
        api.getAgentsHealth(),
        api.getSystemStats(),
        api.getAnomalies(),
      ]);
      store.agentHealth = agentHealth;
      store.systemStats = systemStats;
      store.anomalies = anomalies;
      store.sharedError = null;
    } catch (error) {
      store.sharedError =
        error instanceof Error
          ? error.message
          : "Monitoring verileri alınamadı";
    } finally {
      store.sharedLoading = false;
      notify();
      sharedInFlight = null;
    }
  })();

  return sharedInFlight;
}

async function refreshHeartbeatData(): Promise<void> {
  if (heartbeatInFlight) {
    return heartbeatInFlight;
  }

  heartbeatInFlight = (async () => {
    try {
      const [tasks, events] = await Promise.all([
        api.getHeartbeatTasks(),
        api.getHeartbeatEvents(15),
      ]);
      store.heartbeatTasks = tasks.tasks ?? [];
      store.heartbeatEvents = events.events ?? [];
      store.heartbeatError = null;
    } catch (error) {
      store.heartbeatTasks = [];
      store.heartbeatEvents = [];
      store.heartbeatError =
        error instanceof Error ? error.message : "Heartbeat verileri alınamadı";
    } finally {
      store.heartbeatLoading = false;
      notify();
      heartbeatInFlight = null;
    }
  })();

  return heartbeatInFlight;
}

async function refreshAutonomousConversations(): Promise<void> {
  if (autonomousInFlight) {
    return autonomousInFlight;
  }

  autonomousInFlight = (async () => {
    try {
      const data = await api.getAutonomousConversations(8);
      store.autonomousConversations = data.conversations ?? [];
      store.autonomousError = null;
    } catch (error) {
      store.autonomousConversations = [];
      store.autonomousError =
        error instanceof Error ? error.message : "Otonom konuşmalar alınamadı";
    } finally {
      store.autonomousLoading = false;
      notify();
      autonomousInFlight = null;
    }
  })();

  return autonomousInFlight;
}

function clearPollingTimers() {
  if (sharedTimer) {
    clearInterval(sharedTimer);
    sharedTimer = null;
  }

  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function ensurePollingTimers() {
  if (subscriberCount === 0 || isDocumentHidden()) {
    clearPollingTimers();
    return;
  }

  if (!sharedTimer) {
    sharedTimer = setInterval(() => {
      void refreshSharedData();
    }, SHARED_INTERVAL_MS);
  }

  if (!heartbeatTimer) {
    heartbeatTimer = setInterval(() => {
      void refreshHeartbeatData();
    }, HEARTBEAT_INTERVAL_MS);
  }
}

function startMonitoringData() {
  subscriberCount += 1;
  if (subscriberCount > 1) {
    ensurePollingTimers();
    return;
  }

  void Promise.all([
    refreshSharedData(),
    refreshHeartbeatData(),
    refreshAutonomousConversations(),
  ]);

  ensurePollingTimers();

  if (typeof document !== "undefined") {
    visibilityHandler = () => {
      ensurePollingTimers();
      if (!isDocumentHidden()) {
        void Promise.all([refreshSharedData(), refreshHeartbeatData()]);
      }
    };
    document.addEventListener("visibilitychange", visibilityHandler);
  }
}

function stopMonitoringData() {
  subscriberCount = Math.max(0, subscriberCount - 1);
  if (subscriberCount > 0) {
    return;
  }

  clearPollingTimers();

  if (typeof document !== "undefined" && visibilityHandler) {
    document.removeEventListener("visibilitychange", visibilityHandler);
    visibilityHandler = null;
  }
}

export function useMonitoringData() {
  const data = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  useEffect(() => {
    startMonitoringData();
    return () => {
      stopMonitoringData();
    };
  }, []);

  return {
    ...data,
    refreshSharedData,
    refreshHeartbeatData,
    refreshAutonomousConversations,
  };
}
