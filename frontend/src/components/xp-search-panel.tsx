"use client";

import { useState, useCallback } from "react";
import {
  Search,
  Loader2,
  FileText,
  FolderOpen,
  MessageSquare,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ThreadSummary } from "@/lib/types";

interface ProjectItem {
  name: string;
  phases: string[];
  phase_count: number;
  total_phases: number;
}

export function XpSearchPanel() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async () => {
    const q = query.trim().toLowerCase();
    if (!q) return;
    setLoading(true);
    setSearched(true);
    try {
      const [threadList, projectList] = await Promise.all([
        api.listThreads(100),
        api.listProjects(),
      ]);
      setThreads(
        threadList.filter(
          (t) =>
            (t.preview || "").toLowerCase().includes(q) ||
            t.id.toLowerCase().includes(q),
        ),
      );
      setProjects(
        projectList.filter(
          (p) =>
            p.name.toLowerCase().includes(q) ||
            p.phases.some((ph) => ph.toLowerCase().includes(q)),
        ),
      );
    } catch (err) {
      console.error("[XpSearch] error:", err);
    } finally {
      setLoading(false);
    }
  }, [query]);

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

  const total = threads.length + projects.length;

  return (
    <div className="flex flex-col h-full bg-[#0a0e1a] text-slate-200">
      {/* Search Header */}
      <div className="px-3 py-3 border-b border-slate-700/50 space-y-2">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-medium text-slate-300">
            Görev &amp; Rapor Arama
          </span>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Oturum, proje veya görev ara..."
            className="flex-1 bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-xs rounded font-medium transition-colors flex items-center gap-1.5"
          >
            {loading ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Search className="w-3 h-3" />
            )}
            Ara
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-auto">
        {!searched && (
          <div className="p-6 text-center text-sm text-slate-500">
            Önceki görevler ve raporlar arasında arama yapın
          </div>
        )}

        {searched && !loading && total === 0 && (
          <div className="p-6 text-center text-sm text-slate-500">
            &quot;{query}&quot; için sonuç bulunamadı
          </div>
        )}

        {searched && total > 0 && (
          <div className="divide-y divide-slate-700/30">
            {/* Threads */}
            {threads.length > 0 && (
              <div>
                <div className="px-3 py-2 bg-slate-800/40 flex items-center gap-2">
                  <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
                  <span className="text-[11px] font-semibold text-slate-400">
                    Oturumlar ({threads.length})
                  </span>
                </div>
                {threads.map((t) => (
                  <div
                    key={t.id}
                    className="px-3 py-2.5 hover:bg-slate-800/40 transition-colors"
                  >
                    <div className="flex items-start gap-2">
                      <FileText className="w-3.5 h-3.5 text-slate-500 mt-0.5 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-xs text-slate-300 truncate">
                          {t.preview || t.id.slice(0, 20)}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          {fmtDate(t.created_at)} · {t.task_count} görev ·{" "}
                          {t.event_count} olay
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Projects */}
            {projects.length > 0 && (
              <div>
                <div className="px-3 py-2 bg-slate-800/40 flex items-center gap-2">
                  <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
                  <span className="text-[11px] font-semibold text-slate-400">
                    Projeler ({projects.length})
                  </span>
                </div>
                {projects.map((p) => (
                  <div
                    key={p.name}
                    className="px-3 py-2.5 hover:bg-slate-800/40 transition-colors"
                  >
                    <div className="flex items-start gap-2">
                      <FolderOpen className="w-3.5 h-3.5 text-amber-500/60 mt-0.5 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-xs text-slate-300 truncate">
                          {p.name}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          {p.phase_count}/{p.total_phases} aşama tamamlandı
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
