"use client";

import { useCallback, useEffect, useState } from "react";
import { History, Loader2, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { setPendingThread } from "@/lib/ws-store";
import type { ThreadSummary } from "@/lib/types";

export function XpSessionsPanel() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listThreads(50);
      setThreads(list);
    } catch (err) {
      console.error("[XpSessions] load error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: string) => {
    try {
      await api.deleteThread(id);
      setThreads((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      console.error("[XpSessions] delete error:", err);
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm("Tüm oturumlar silinsin mi?")) return;
    try {
      await api.deleteAllThreads();
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
            className="flex items-start gap-2 p-3 hover:bg-[#e8e4d4] transition-colors group cursor-pointer"
            onClick={() => {
              setPendingThread(t.id);
              window.dispatchEvent(
                new CustomEvent("open-thread", { detail: t.id }),
              );
              window.dispatchEvent(
                new CustomEvent("open-app", { detail: "chat" }),
              );
            }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setPendingThread(t.id);
                window.dispatchEvent(
                  new CustomEvent("open-thread", { detail: t.id }),
                );
                window.dispatchEvent(
                  new CustomEvent("open-app", { detail: "chat" }),
                );
              }
            }}
          >
            <div className="flex-1 min-w-0">
              <div className="text-xs text-gray-700 truncate">
                {t.preview || t.id.slice(0, 12)}
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5">
                {fmtDate(t.created_at)} · {t.task_count} görev · {t.event_count}{" "}
                olay
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
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
