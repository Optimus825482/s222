"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Thread } from "./types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SessionMeta {
  id: string;
  title: string;
  messageCount: number;
  lastUpdated: string;
  taskCount: number;
}

interface StoredSession {
  thread_id: string;
  thread: Thread;
  title: string;
  messageCount: number;
  taskCount: number;
  lastUpdated: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DB_NAME = "nexus-ai";
const STORE_NAME = "sessions";
const DB_VERSION = 1;
const MAX_SESSIONS = 50;
const LAST_SESSION_KEY = "lastActiveSessionId";

// ---------------------------------------------------------------------------
// IndexedDB helpers (module-level, shared across hook instances)
// ---------------------------------------------------------------------------

let dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;

  dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB unavailable"));
      return;
    }

    const req = indexedDB.open(DB_NAME, DB_VERSION);

    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, {
          keyPath: "thread_id",
        });
        store.createIndex("lastUpdated", "lastUpdated", { unique: false });
      }
    };

    req.onsuccess = () => resolve(req.result);
    req.onerror = () => {
      dbPromise = null;
      reject(req.error);
    };
  });

  return dbPromise;
}

function tx(
  mode: IDBTransactionMode,
): Promise<{ store: IDBObjectStore; done: Promise<void> }> {
  return openDB().then((db) => {
    const transaction = db.transaction(STORE_NAME, mode);
    const store = transaction.objectStore(STORE_NAME);
    const done = new Promise<void>((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
    return { store, done };
  });
}

function idbRequest<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function deriveTitle(thread: Thread): string {
  const firstUserMsg = thread.events.find(
    (e) => e.event_type === "user_message",
  );
  if (firstUserMsg?.content) {
    return firstUserMsg.content.length > 60
      ? firstUserMsg.content.slice(0, 57) + "..."
      : firstUserMsg.content;
  }
  return `Session ${thread.id.slice(0, 8)}`;
}

function toStoredSession(thread: Thread): StoredSession {
  return {
    thread_id: thread.id,
    thread,
    title: deriveTitle(thread),
    messageCount: thread.events.length,
    taskCount: thread.tasks.length,
    lastUpdated: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// Eviction — keep store at MAX_SESSIONS by removing oldest entries
// ---------------------------------------------------------------------------

async function evictOldest(): Promise<void> {
  const { store, done } = await tx("readwrite");
  const index = store.index("lastUpdated");

  const count = await idbRequest(store.count());
  if (count <= MAX_SESSIONS) return;

  const toRemove = count - MAX_SESSIONS;
  let removed = 0;

  const cursorReq = index.openCursor(null, "next");

  await new Promise<void>((resolve, reject) => {
    cursorReq.onsuccess = () => {
      const cursor = cursorReq.result;
      if (!cursor || removed >= toRemove) {
        resolve();
        return;
      }
      cursor.delete();
      removed++;
      cursor.continue();
    };
    cursorReq.onerror = () => reject(cursorReq.error);
  });

  await done;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSessionPersistence() {
  const [isReady, setIsReady] = useState(false);
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Hydrate on mount
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        await openDB();
        if (cancelled) return;

        const stored =
          typeof localStorage !== "undefined"
            ? localStorage.getItem(LAST_SESSION_KEY)
            : null;

        setLastSessionId(stored);
        setIsReady(true);
      } catch {
        // IndexedDB unavailable — degrade gracefully
        if (!cancelled) setIsReady(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // ------- Public API -------

  const saveSession = useCallback(async (thread: Thread): Promise<void> => {
    try {
      const record = toStoredSession(thread);
      const { store, done } = await tx("readwrite");
      store.put(record);
      await done;

      localStorage.setItem(LAST_SESSION_KEY, thread.id);
      setLastSessionId(thread.id);

      await evictOldest();
    } catch {
      // Silently degrade
    }
  }, []);

  const saveSessionDebounced = useCallback(
    (thread: Thread) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        saveSession(thread);
      }, 2_000);
    },
    [saveSession],
  );

  const loadSession = useCallback(
    async (threadId: string): Promise<Thread | null> => {
      try {
        const { store, done } = await tx("readonly");
        const record = await idbRequest<StoredSession | undefined>(
          store.get(threadId),
        );
        await done;

        if (record) {
          localStorage.setItem(LAST_SESSION_KEY, threadId);
          setLastSessionId(threadId);
          return record.thread;
        }
        return null;
      } catch {
        return null;
      }
    },
    [],
  );

  const listSessions = useCallback(async (): Promise<SessionMeta[]> => {
    try {
      const { store, done } = await tx("readonly");
      const index = store.index("lastUpdated");
      const all = await idbRequest<StoredSession[]>(index.getAll());
      await done;

      // Newest first
      return all
        .reverse()
        .map(({ thread_id, title, messageCount, lastUpdated, taskCount }) => ({
          id: thread_id,
          title,
          messageCount,
          lastUpdated,
          taskCount,
        }));
    } catch {
      return [];
    }
  }, []);

  const deleteSession = useCallback(
    async (threadId: string): Promise<void> => {
      try {
        const { store, done } = await tx("readwrite");
        store.delete(threadId);
        await done;

        if (lastSessionId === threadId) {
          localStorage.removeItem(LAST_SESSION_KEY);
          setLastSessionId(null);
        }
      } catch {
        // Silently degrade
      }
    },
    [lastSessionId],
  );

  const clearAll = useCallback(async (): Promise<void> => {
    try {
      const { store, done } = await tx("readwrite");
      store.clear();
      await done;

      localStorage.removeItem(LAST_SESSION_KEY);
      setLastSessionId(null);
    } catch {
      // Silently degrade
    }
  }, []);

  return {
    saveSession,
    saveSessionDebounced,
    loadSession,
    listSessions,
    deleteSession,
    clearAll,
    lastSessionId,
    isReady,
  };
}
