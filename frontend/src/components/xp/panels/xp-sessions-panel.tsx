"use client";

import { useCallback, useEffect, useState } from "react";
import { Clock3, GitBranch, History, Loader2, Radio, Scissors, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { setPendingThread } from "@/lib/ws-store";
import { useSessionPersistence, type SessionMeta } from "@/lib/use-session-persistence";

interface SessionListItem {
  id: string;
  title: string;
  taskCount: number;
  eventCount: number;
  updatedAt: string;
  branchLabel?: string | null;
  compactedSummary?: string | null;
}

export function XpSessionsPanel() {
  const {
    listSessions,
    deleteSession,
    clearAll,
    lastSessionId,
    isReady: persistReady,
  } = useSessionPersistence();
  const [threads, setThreads] = useState<SessionListItem[]>([]);
  const [loading, setLoading] = useState(false);

  const mapSessionMeta = useCallback((session: SessionMeta): SessionListItem => {
    return {
      id: session.id,
      title: session.title,
      taskCount: session.taskCount,
      eventCount: session.messageCount,
      updatedAt: session.lastUpdated,
      branchLabel: session.branch_label,
      compactedSummary: session.compacted_summary,
    };
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (persistReady) {
        const list = await listSessions();
        setThreads(list.map(mapSessionMeta));
      } else {
        const list = await api.listThreads(50);
        setThreads(
          list.map((thread) => ({
            id: thread.id,
            title: thread.preview || thread.id.slice(0, 12),
            taskCount: thread.task_count,
            eventCount: thread.event_count,
            updatedAt: thread.created_at,
            branchLabel: thread.branch_label,
            compactedSummary: thread.compacted_summary,
          })),
        );
      }
    } catch (err) {
      console.error("[XpSessions] load error:", err);
    } finally {
      setLoading(false);
    }
  }, [listSessions, mapSessionMeta, persistReady]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: string) => {
    try {
      await Promise.allSettled([api.deleteThread(id), deleteSession(id)]);
      setThreads((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      console.error("[XpSessions] delete error:", err);
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm("Tüm oturumlar silinsin mi?")) return;
    try {
      await Promise.allSettled([api.deleteAllThreads(), clearAll()]);
      setThreads([]);
    } catch (err) {
      console.error("[XpSessions] deleteAll error:", err);
    }
  };

  const fmtDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("tr-TR", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="flex flex-col h-full bg-white text-gray-900">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#d6d2c2]">
        <History className="w-4 h-4 text-[#0066cc]" />
        <span className="text-xs font-medium text-gray-700">Oturumlar</span>
        {loading && (
          <Loader2 className="w-3 h-3 animate-spin text-[#0066cc] ml-auto" />
        )}
        {!loading && threads.length > 0 && (
          <button
            onClick={handleDeleteAll}
            className="ml-auto text-[10px] text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-500/10 transition-colors"
          >
            Tümünü Sil
          </button>
        )}
      </div>
      <div className="flex-1 overflow-auto divide-y divide-[#d6d2c2]">
        {threads.length === 0 && !loading && (
          <div className="p-6 text-center text-sm text-gray-500">
            Kayıtlı oturum yok
          </div>
        )}
        {threads.map((t) => (
          <div
            key={t.id}
            className="flex items-start gap-2 p-3 hover:bg-[#e8e4d4] transition-colors group"
          >
            <button
              type="button"
              className="flex-1 min-w-0 text-left cursor-pointer"
              onClick={() => {
                setPendingThread(t.id);
                window.dispatchEvent(
                  new CustomEvent("open-thread", { detail: t.id }),
                );
                window.dispatchEvent(
                  new CustomEvent("open-app", { detail: "chat" }),
                );
              }}
            >
              <div className="text-xs text-gray-700 truncate">
                {t.title || t.id.slice(0, 12)}
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="inline-flex items-center gap-1">
                  <Clock3 className="w-3 h-3" />
                  {fmtDate(t.updatedAt)}
                </span>
                <span>{t.taskCount} görev</span>
                <span>{t.eventCount} olay</span>
                {lastSessionId === t.id && (
                  <span className="inline-flex items-center gap-1 text-[#0066cc] font-medium">
                    <Radio className="w-3 h-3" />
                    Aktif
                  </span>
                )}
                {t.branchLabel && (
                  <span className="inline-flex items-center gap-1 text-[#6b46c1] font-medium">
                    <GitBranch className="w-3 h-3" />
                    {t.branchLabel}
                  </span>
                )}
                {t.compactedSummary && (
                  <span className="inline-flex items-center gap-1 text-[#92400e] font-medium">
                    <Scissors className="w-3 h-3" />
                    Compact
                  </span>
                )}
              </div>
            </button>
            <button
              type="button"
              onClick={() => {
                handleDelete(t.id);
              }}
              className="opacity-0 group-hover:opacity-100 p-1 text-red-400 hover:text-red-300 transition-all"
              aria-label="Oturumu sil"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
