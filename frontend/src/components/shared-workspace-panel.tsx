"use client";

import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/* ── Types ── */
interface WorkspaceItem {
  id: string;
  workspace_id: string;
  item_type: string;
  content: string;
  author_id: string;
  created_at?: string;
}
interface WorkspaceMeta {
  workspace_id: string;
  name: string;
  owner_id: string;
  members: string[];
  item_count?: number;
}
interface WorkspaceStats {
  total_items: number;
  by_type: Record<string, number>;
  members: number;
}

/* ── Helpers ── */
const crd = "bg-slate-800/60 rounded-lg border border-slate-700/50 p-3";
const btn =
  "px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-40";
const inp =
  "bg-slate-900/60 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 w-full focus:outline-none focus:ring-1 focus:ring-cyan-500/50";

function Sk({ n = 3 }: { n?: number }) {
  return (
    <div className="space-y-2 animate-pulse">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="h-8 bg-slate-700/40 rounded" />
      ))}
    </div>
  );
}

export function SharedWorkspacePanel() {
  const { user } = useAuth();

  const [workspaces, setWorkspaces] = useState<WorkspaceMeta[]>([]);
  const [active, setActive] = useState<WorkspaceMeta | null>(null);
  const [items, setItems] = useState<WorkspaceItem[]>([]);
  const [stats, setStats] = useState<WorkspaceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // create form
  const [newName, setNewName] = useState("");
  // add item form
  const [itemType, setItemType] = useState("note");
  const [itemContent, setItemContent] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetcher<{ workspaces: WorkspaceMeta[] }>(
        "/api/workspaces",
      );
      setWorkspaces(data.workspaces ?? []);
    } catch (e: any) {
      setError(e?.message ?? "API error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openWorkspace = async (ws: WorkspaceMeta) => {
    setActive(ws);
    try {
      const [itemsData, statsData] = await Promise.all([
        fetcher<{ items: WorkspaceItem[] }>(
          `/api/workspaces/${ws.workspace_id}/items`,
        ),
        fetcher<WorkspaceStats>(`/api/workspaces/${ws.workspace_id}/stats`),
      ]);
      setItems(itemsData.items ?? []);
      setStats(statsData);
    } catch {
      setItems([]);
      setStats(null);
    }
  };

  const createWorkspace = async () => {
    if (!newName.trim()) return;
    try {
      await fetcher("/api/workspaces", {
        method: "POST",
        body: JSON.stringify({
          workspace_id: `ws_${Date.now()}`,
          name: newName.trim(),
        }),
      });
      setNewName("");
      load();
    } catch {}
  };

  const addItem = async () => {
    if (!active || !itemContent.trim()) return;
    try {
      await fetcher(`/api/workspaces/${active.workspace_id}/items`, {
        method: "POST",
        body: JSON.stringify({
          item_type: itemType,
          content: itemContent.trim(),
        }),
      });
      setItemContent("");
      openWorkspace(active);
    } catch {}
  };

  const deleteItem = async (itemId: string) => {
    if (!active) return;
    try {
      await fetcher(`/api/workspaces/${active.workspace_id}/items/${itemId}`, {
        method: "DELETE",
      });
      openWorkspace(active);
    } catch {}
  };

  if (loading)
    return (
      <div className="p-4">
        <Sk />
      </div>
    );
  if (error)
    return (
      <div className="p-4 text-center">
        <p className="text-red-400 text-xs mb-2">{error}</p>
        <button onClick={load} className={`${btn} bg-slate-700 text-slate-200`}>
          Tekrar Dene
        </button>
      </div>
    );

  return (
    <div className="h-full flex flex-col gap-3 p-4 text-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <span className="text-lg">🗂️</span> Shared Workspace
        </h2>
        <button
          onClick={load}
          className={`${btn} bg-slate-700 hover:bg-slate-600 text-slate-300`}
        >
          ↻
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3 flex-1 min-h-0">
        {/* Left: workspace list */}
        <div className={`${crd} flex flex-col`}>
          <h3 className="text-xs font-medium text-slate-400 mb-2">
            Çalışma Alanları
          </h3>

          {/* Create */}
          <div className="flex gap-1 mb-3">
            <input
              className={inp}
              placeholder="Yeni alan adı..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createWorkspace()}
            />
            <button
              onClick={createWorkspace}
              disabled={!newName.trim()}
              className={`${btn} bg-cyan-600 hover:bg-cyan-500 text-white shrink-0`}
            >
              +
            </button>
          </div>

          <div className="flex-1 overflow-auto space-y-1">
            {workspaces.length === 0 && (
              <p className="text-[10px] text-slate-500">Henüz alan yok</p>
            )}
            {workspaces.map((ws) => (
              <button
                key={ws.workspace_id}
                onClick={() => openWorkspace(ws)}
                className={`w-full text-left p-2 rounded text-xs transition-colors ${
                  active?.workspace_id === ws.workspace_id
                    ? "bg-cyan-900/40 border border-cyan-700/50"
                    : "hover:bg-slate-700/50 border border-transparent"
                }`}
              >
                <div className="font-medium truncate">{ws.name}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  {(ws.members ?? []).length} üye · {ws.item_count ?? "?"} öğe
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right: workspace detail */}
        <div className={`${crd} col-span-2 flex flex-col`}>
          {active ? (
            <>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-xs font-semibold">{active.name}</h3>
                  <span className="text-[10px] text-slate-500">
                    {active.workspace_id} · Sahip: {active.owner_id}
                  </span>
                </div>
                {stats && (
                  <div className="flex gap-2 text-[10px] text-slate-400">
                    <span>{stats.total_items} öğe</span>
                    <span>{stats.members} üye</span>
                  </div>
                )}
              </div>

              {/* Add item */}
              <div className="flex gap-1 mb-3">
                <select
                  className={`${inp} w-24`}
                  value={itemType}
                  onChange={(e) => setItemType(e.target.value)}
                >
                  <option value="note">Not</option>
                  <option value="code">Kod</option>
                  <option value="link">Link</option>
                  <option value="decision">Karar</option>
                  <option value="finding">Bulgu</option>
                </select>
                <input
                  className={inp}
                  placeholder="İçerik ekle..."
                  value={itemContent}
                  onChange={(e) => setItemContent(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addItem()}
                />
                <button
                  onClick={addItem}
                  disabled={!itemContent.trim()}
                  className={`${btn} bg-emerald-600 hover:bg-emerald-500 text-white shrink-0`}
                >
                  Ekle
                </button>
              </div>

              {/* Items list */}
              <div className="flex-1 overflow-auto space-y-1.5">
                {items.length === 0 && (
                  <p className="text-[10px] text-slate-500 text-center py-6">
                    Bu alanda henüz öğe yok
                  </p>
                )}
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start gap-2 p-2 rounded bg-slate-900/40 border border-slate-700/30"
                  >
                    <span className="text-[10px] shrink-0 mt-0.5 px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-400">
                      {item.item_type}
                    </span>
                    <p className="text-xs flex-1 break-all whitespace-pre-wrap">
                      {item.content}
                    </p>
                    <div className="flex flex-col items-end shrink-0">
                      <span className="text-[9px] text-slate-600">
                        {item.author_id}
                      </span>
                      <button
                        onClick={() => deleteItem(item.id)}
                        className="text-[10px] text-red-500/60 hover:text-red-400 mt-1"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500">
              <div className="text-center">
                <span className="text-3xl block mb-2 opacity-40">🗂️</span>
                <p className="text-xs">Bir çalışma alanı seçin</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default SharedWorkspacePanel;
