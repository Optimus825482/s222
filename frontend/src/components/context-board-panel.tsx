"use client";

import { useCallback, useEffect, useState } from "react";
import { fetcher } from "@/lib/api";

/* ── Types ────────────────────────────────────────────────────── */

type ItemType = "note" | "finding" | "link" | "code_snippet" | "metric";

interface CBItem {
  id: string;
  type: ItemType;
  title: string;
  content: string;
  created_by: string;
  tags: string[];
  pinned: boolean;
  created_at: string;
}

interface CBStats {
  total: number;
  total_items?: number;
  by_type: Record<string, number>;
  by_agent?: Record<string, number>;
  pinned_count?: number;
}

/* ── Constants ────────────────────────────────────────────────── */

const TYPE_ICONS: Record<ItemType, string> = {
  note: "📝",
  finding: "🔍",
  link: "🔗",
  code_snippet: "💻",
  metric: "📊",
};

const TYPE_LABELS: Record<ItemType, string> = {
  note: "Not",
  finding: "Bulgu",
  link: "Bağlantı",
  code_snippet: "Kod",
  metric: "Metrik",
};

const ALL_TYPES: ItemType[] = [
  "note",
  "finding",
  "link",
  "code_snippet",
  "metric",
];

const TABS = [
  { key: "all", label: "Tümü" },
  { key: "note", label: "Notlar" },
  { key: "finding", label: "Bulgular" },
  { key: "link", label: "Bağlantılar" },
] as const;

const AGENT_COLORS: Record<string, string> = {
  orchestrator: "#ec4899",
  thinker: "#00e5ff",
  speed: "#a78bfa",
  researcher: "#f59e0b",
  reasoner: "#10b981",
  critic: "#06b6d4",
};

const AGENTS = Object.keys(AGENT_COLORS);

/* ── Shared UI ────────────────────────────────────────────────── */

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-white/5 rounded ${className}`}
      aria-hidden
    />
  );
}

function InlineError({ message }: { message: string }) {
  return (
    <p className="text-xs text-red-400 py-2" role="alert">
      {message}
    </p>
  );
}

/* ── Add Item Form ────────────────────────────────────────────── */

function AddItemForm({ onAdded }: { onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<ItemType>("note");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [createdBy, setCreatedBy] = useState("orchestrator");
  const [tagsRaw, setTagsRaw] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    if (!title.trim()) return;
    try {
      setSubmitting(true);
      setError(null);
      const tags = tagsRaw
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await fetcher("/api/context-board/items", {
        method: "POST",
        body: JSON.stringify({
          type,
          title: title.trim(),
          content: content.trim(),
          created_by: createdBy,
          tags,
          pinned: false,
        }),
      });
      setTitle("");
      setContent("");
      setTagsRaw("");
      setOpen(false);
      onAdded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Eklenemedi");
    } finally {
      setSubmitting(false);
    }
  }, [type, title, content, createdBy, tagsRaw, onAdded]);

  return (
    <div className="space-y-1.5">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-2 py-1.5 text-[11px] font-medium text-slate-400 hover:text-slate-700 bg-white/5 hover:bg-white/8 rounded border border-border/50 transition-colors"
      >
        {open ? "▾ Formu Kapat" : "＋ Yeni Öğe Ekle"}
      </button>

      {open && (
        <div className="space-y-1.5 p-2 rounded bg-white/[0.03] border border-border/40">
          {/* Type + Agent row */}
          <div className="flex gap-1.5">
            <select
              value={type}
              onChange={(e) => setType(e.target.value as ItemType)}
              className="flex-1 bg-white/5 border border-border rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-blue-500/50"
              aria-label="Tür"
            >
              {ALL_TYPES.map((t) => (
                <option key={t} value={t}>
                  {TYPE_ICONS[t]} {TYPE_LABELS[t]}
                </option>
              ))}
            </select>
            <select
              value={createdBy}
              onChange={(e) => setCreatedBy(e.target.value)}
              className="flex-1 bg-white/5 border border-border rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-blue-500/50"
              aria-label="Oluşturan ajan"
            >
              {AGENTS.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>

          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Başlık..."
            className="w-full bg-white/5 border border-border rounded px-2 py-1 text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
            aria-label="Başlık"
          />

          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="İçerik..."
            rows={2}
            className="w-full bg-white/5 border border-border rounded px-2 py-1 text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 resize-none"
            aria-label="İçerik"
          />

          <input
            type="text"
            value={tagsRaw}
            onChange={(e) => setTagsRaw(e.target.value)}
            placeholder="Etiketler (virgülle ayır)..."
            className="w-full bg-white/5 border border-border rounded px-2 py-1 text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
            aria-label="Etiketler"
          />

          {error && <InlineError message={error} />}

          <button
            onClick={submit}
            disabled={submitting || !title.trim()}
            className="w-full px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 text-[11px] font-medium rounded border border-blue-500/20 transition-colors disabled:opacity-50"
          >
            {submitting ? "Ekleniyor..." : "Ekle"}
          </button>
        </div>
      )}
    </div>
  );
}

/* ── Item Card ────────────────────────────────────────────────── */

function ItemCard({
  item,
  onPin,
  onDelete,
}: {
  item: CBItem;
  onPin: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const agentColor = AGENT_COLORS[item.created_by] ?? "#6b7280";
  const timeStr = (() => {
    try {
      const d = new Date(item.created_at);
      return d.toLocaleString("tr-TR", {
        hour: "2-digit",
        minute: "2-digit",
        day: "2-digit",
        month: "2-digit",
      });
    } catch {
      return "";
    }
  })();

  return (
    <div className="group px-2 py-1.5 rounded bg-white/5 hover:bg-white/8 border border-border/30 transition-colors space-y-1">
      {/* Header row */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs shrink-0" title={TYPE_LABELS[item.type]}>
          {TYPE_ICONS[item.type]}
        </span>
        {item.pinned && (
          <span className="text-[10px] shrink-0" title="Sabitlenmiş">
            📌
          </span>
        )}
        <span className="text-[11px] font-medium text-slate-200 truncate flex-1">
          {item.title}
        </span>
        <span
          className="text-[9px] px-1.5 py-0.5 rounded font-medium shrink-0"
          style={{ backgroundColor: `${agentColor}20`, color: agentColor }}
        >
          {item.created_by}
        </span>
      </div>

      {/* Content preview */}
      {item.content && (
        <p className="text-[10px] text-slate-500 line-clamp-2 leading-relaxed">
          {item.content}
        </p>
      )}

      {/* Tags + meta row */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {item.tags.map((tag) => (
          <span
            key={tag}
            className="text-[9px] px-1 py-0.5 rounded bg-white/5 text-slate-500"
          >
            #{tag}
          </span>
        ))}
        <span className="text-[9px] text-slate-600 ml-auto shrink-0">
          {timeStr}
        </span>

        {/* Actions (visible on hover) */}
        <button
          onClick={() => onPin(item.id)}
          className="opacity-0 group-hover:opacity-100 text-[10px] text-slate-500 hover:text-amber-400 transition-all"
          title={item.pinned ? "Sabitlemeyi kaldır" : "Sabitle"}
          aria-label={item.pinned ? "Sabitlemeyi kaldır" : "Sabitle"}
        >
          {item.pinned ? "◉" : "○"}
        </button>
        <button
          onClick={() => onDelete(item.id)}
          className="opacity-0 group-hover:opacity-100 text-[10px] text-slate-500 hover:text-red-400 transition-all"
          title="Sil"
          aria-label="Öğeyi sil"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

/* ── Main Export ──────────────────────────────────────────────── */

export function ContextBoardPanel() {
  const [tab, setTab] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<CBItem[]>([]);
  const [stats, setStats] = useState<CBStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* ── Fetch items ── */
  const loadItems = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({ limit: "50" });
      if (tab !== "all") params.set("type", tab);
      if (search.trim()) params.set("search", search.trim());
      const raw = await fetcher<{ items: CBItem[]; total: number }>(
        `/api/context-board/items?${params}`,
      );
      const arr =
        (raw as { items?: CBItem[] })?.items ?? (Array.isArray(raw) ? raw : []);
      setItems(arr);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, [tab, search]);

  /* ── Fetch stats ── */
  const loadStats = useCallback(async () => {
    try {
      const data = await fetcher<CBStats>("/api/context-board/stats");
      setStats(data);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    loadItems();
  }, [loadItems]);
  useEffect(() => {
    loadStats();
  }, [loadStats]);

  /* ── Actions ── */
  const handlePin = useCallback(
    async (id: string) => {
      try {
        await fetcher(`/api/context-board/items/${id}/pin`, { method: "POST" });
        loadItems();
      } catch {
        /* silent */
      }
    },
    [loadItems],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await fetcher(`/api/context-board/items/${id}`, { method: "DELETE" });
        loadItems();
        loadStats();
      } catch {
        /* silent */
      }
    },
    [loadItems, loadStats],
  );

  /* ── Sort: pinned first ── */
  const sorted = [...items].sort((a, b) =>
    a.pinned === b.pinned ? 0 : a.pinned ? -1 : 1,
  );

  return (
    <div className="space-y-2" role="region" aria-label="Bağlam Panosu">
      {/* ── Tab Bar ── */}
      <div className="flex gap-0.5 bg-white/[0.03] rounded p-0.5">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 px-2 py-1 text-[10px] font-medium rounded transition-colors ${
              tab === t.key
                ? "bg-white/10 text-slate-200"
                : "text-slate-500 hover:text-slate-300 hover:bg-white/5"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Search ── */}
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Ara..."
        className="w-full bg-white/5 border border-border rounded px-2 py-1 text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
        aria-label="Öğelerde ara"
      />

      {/* ── Add Form ── */}
      <AddItemForm
        onAdded={() => {
          loadItems();
          loadStats();
        }}
      />

      {/* ── Items List ── */}
      {loading ? (
        <div className="space-y-1.5">
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
        </div>
      ) : error ? (
        <InlineError message={error} />
      ) : sorted.length === 0 ? (
        <p className="text-[11px] text-slate-600 py-6 text-center">
          Henüz öğe yok
        </p>
      ) : (
        <div className="space-y-1 max-h-[420px] overflow-y-auto">
          {sorted.map((item) => (
            <ItemCard
              key={item.id}
              item={item}
              onPin={handlePin}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* ── Stats Bar ── */}
      {stats && (
        <div className="flex items-center gap-2 flex-wrap px-1 pt-1 border-t border-border/40">
          <span className="text-[10px] text-slate-500 font-medium">
            {stats.total_items ?? stats.total} öğe
          </span>
          {Object.entries(stats.by_type ?? {}).map(([t, count]) => (
            <span key={t} className="text-[9px] text-slate-600">
              {TYPE_ICONS[t as ItemType] ?? "•"} {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
