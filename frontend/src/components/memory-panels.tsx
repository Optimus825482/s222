"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";

// ── Shared Helpers ──────────────────────────────────────────────

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-slate-700/50 ${className}`}
      aria-hidden="true"
    />
  );
}

function InlineError({ message }: { message: string }) {
  return (
    <div role="alert" className="text-xs text-red-400 py-2 px-1">
      ⚠️ {message}
    </div>
  );
}

const CATEGORY_COLORS: Record<string, string> = {
  task: "#f59e0b",
  conversation: "#00e5ff",
  skill: "#10b981",
  fact: "#ec4899",
  preference: "#a78bfa",
  error: "#ef4444",
  default: "#64748b",
};

function getCategoryColor(cat: string): string {
  return CATEGORY_COLORS[cat.toLowerCase()] || CATEGORY_COLORS.default;
}

type GroupBy = "hour" | "day" | "category";
type TimeRange = 24 | 48 | 168 | 8760;

const GROUP_LABELS: Record<GroupBy, string> = {
  hour: "Saatlik",
  day: "Günlük",
  category: "Kategori",
};

const RANGE_LABELS: Record<TimeRange, string> = {
  24: "24s",
  48: "48s",
  168: "7g",
  8760: "Tümü",
};

// ── Component 1: MemoryTimelinePanel ────────────────────────────

type TimelineItem = { period?: string; group?: string; count: number };

export function MemoryTimelinePanel() {
  const [data, setData] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [groupBy, setGroupBy] = useState<GroupBy>("day");
  const [hours, setHours] = useState<TimeRange>(168);

  const fetchTimeline = useCallback(async () => {
    try {
      const result = await api.getMemoryTimeline(hours, groupBy);
      setData(result);
      setError(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Veri alınamadı";
      console.error("[MemoryTimeline] Fetch error:", msg, e);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [hours, groupBy]);

  useEffect(() => {
    setLoading(true);
    fetchTimeline();
    const interval = setInterval(fetchTimeline, 60_000);
    return () => clearInterval(interval);
  }, [fetchTimeline]);

  const maxCount = Math.max(1, ...data.map((d) => d.count));

  return (
    <section aria-label="Bellek zaman çizelgesi" className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-xs font-semibold text-slate-200">
          Bellek Zaman Çizelgesi
        </h3>
        <div className="flex items-center gap-1.5">
          {(Object.entries(GROUP_LABELS) as [GroupBy, string][]).map(
            ([key, label]) => (
              <button
                key={key}
                onClick={() => setGroupBy(key)}
                className={`text-[10px] px-2 py-0.5 rounded-full border transition-colors ${
                  groupBy === key
                    ? "bg-slate-200 text-[#0f1219] border-slate-200"
                    : "border-border text-slate-400 hover:text-slate-700"
                }`}
              >
                {label}
              </button>
            ),
          )}
          <span className="w-px h-3 bg-border mx-0.5" aria-hidden="true" />
          {(Object.entries(RANGE_LABELS) as [string, string][]).map(
            ([key, label]) => (
              <button
                key={key}
                onClick={() => setHours(Number(key) as TimeRange)}
                className={`text-[10px] px-2 py-0.5 rounded-full border transition-colors ${
                  hours === Number(key)
                    ? "bg-slate-200 text-[#0f1219] border-slate-200"
                    : "border-border text-slate-400 hover:text-slate-700"
                }`}
              >
                {label}
              </button>
            ),
          )}
        </div>
      </div>

      {error && <InlineError message={error} />}

      {loading ? (
        <div className="flex items-end gap-1 h-32">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="flex-1 animate-pulse rounded bg-slate-700/50"
              style={{ height: `${20 + (((i * 17) % 60) + 20)}%` }}
              aria-hidden="true"
            />
          ))}
        </div>
      ) : data.length === 0 ? (
        <p className="text-xs text-slate-500 py-6 text-center">
          Bu aralıkta veri bulunamadı
        </p>
      ) : (
        <div
          className="flex items-end gap-[3px] h-36 px-1"
          role="img"
          aria-label={`${data.length} dönem için bellek aktivitesi grafiği`}
        >
          {data.map((item, i) => {
            const label = item.period || item.group || `#${i + 1}`;
            const pct = (item.count / maxCount) * 100;
            const color =
              groupBy === "category" ? getCategoryColor(label) : "#00e5ff";
            return (
              <div
                key={`${label}-${i}`}
                className="flex-1 flex flex-col items-center gap-1 group min-w-0"
              >
                <span className="text-[9px] text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                  {item.count}
                </span>
                <div
                  className="w-full rounded-sm transition-all duration-300 hover:brightness-125"
                  style={{
                    height: `${Math.max(pct, 3)}%`,
                    backgroundColor: color,
                    opacity: 0.8,
                  }}
                  title={`${label}: ${item.count}`}
                  role="presentation"
                />
                <span className="text-[8px] text-slate-500 truncate w-full text-center">
                  {label.length > 6 ? label.slice(-5) : label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

// ── Component 2: MemoryCorrelationPanel ─────────────────────────

interface ClusterMember {
  content?: string;
  category?: string;
  similarity?: number;
  created_at?: string;
}

interface Cluster {
  primary_category?: string;
  primary_agent?: string;
  avg_similarity?: number;
  members?: ClusterMember[];
}

export function MemoryCorrelationPanel() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [totalFound, setTotalFound] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<Set<number>>(new Set());
  const inputRef = useRef<HTMLInputElement>(null);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.correlateMemories(q, 10);
      setClusters(result.clusters as Cluster[]);
      setTotalFound(result.total_found);
      setExpandedIdx(new Set());
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Arama başarısız";
      console.error("[MemoryCorrelation] Search error:", msg, e);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittedQuery(query);
    search(query);
  };

  // Auto-load recent memories on mount
  useEffect(() => {
    search("*");
    setSubmittedQuery("*");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleCluster = (idx: number) => {
    setExpandedIdx((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <section aria-label="Bellek korelasyonu" className="space-y-3">
      <h3 className="text-xs font-semibold text-slate-200">
        Bellek Korelasyonu
      </h3>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Korelasyon sorgusu girin..."
          className="flex-1 bg-[#1a1f2e] border border-border rounded-md px-2.5 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-slate-400 transition-colors"
          aria-label="Korelasyon arama sorgusu"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="text-[10px] font-medium px-3 py-1.5 rounded-md bg-slate-200 text-[#0f1219] hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Aranıyor..." : "Ara"}
        </button>
      </form>

      {error && <InlineError message={error} />}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      ) : submittedQuery && clusters.length === 0 ? (
        <p className="text-xs text-slate-500 py-4 text-center">
          Eşleşen küme bulunamadı
        </p>
      ) : (
        <>
          {totalFound > 0 && (
            <p className="text-[10px] text-slate-500">
              {totalFound} sonuç, {clusters.length} küme
            </p>
          )}
          <div className="space-y-1.5 max-h-[360px] overflow-y-auto pr-1">
            {clusters.map((cluster, idx) => {
              const catColor = getCategoryColor(
                cluster.primary_category || "default",
              );
              const isOpen = expandedIdx.has(idx);
              const memberCount = cluster.members?.length || 0;

              return (
                <div
                  key={idx}
                  className="bg-[#1a1f2e] border border-border rounded-lg overflow-hidden"
                >
                  <button
                    onClick={() => toggleCluster(idx)}
                    className="w-full flex items-center justify-between p-2.5 text-left hover:bg-white/[0.02] transition-colors"
                    aria-expanded={isOpen}
                    aria-controls={`cluster-${idx}`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: catColor }}
                        aria-hidden="true"
                      />
                      <span className="text-xs font-medium text-slate-200 truncate">
                        {cluster.primary_category || "Bilinmeyen"}
                      </span>
                      {cluster.primary_agent && (
                        <span className="text-[10px] text-slate-500">
                          · {cluster.primary_agent}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {cluster.avg_similarity != null && (
                        <span className="text-[10px] text-slate-400">
                          %{((cluster.avg_similarity ?? 0) * 100).toFixed(0)}
                        </span>
                      )}
                      <span className="text-[10px] text-slate-500">
                        {memberCount} öğe
                      </span>
                      <span
                        className={`text-[10px] text-slate-500 transition-transform ${isOpen ? "rotate-180" : ""}`}
                        aria-hidden="true"
                      >
                        ▾
                      </span>
                    </div>
                  </button>

                  {isOpen && cluster.members && (
                    <div
                      id={`cluster-${idx}`}
                      className="border-t border-border px-2.5 pb-2 space-y-1.5 pt-1.5"
                    >
                      {cluster.members.map((member, mIdx) => (
                        <div
                          key={mIdx}
                          className="flex items-start gap-2 text-[11px]"
                        >
                          <span
                            className="w-1 h-1 rounded-full mt-1.5 shrink-0"
                            style={{
                              backgroundColor: getCategoryColor(
                                member.category || "default",
                              ),
                            }}
                            aria-hidden="true"
                          />
                          <div className="min-w-0 flex-1">
                            <p className="text-slate-300 leading-snug line-clamp-2">
                              {member.content || "—"}
                            </p>
                            <div className="flex items-center gap-2 mt-0.5 text-[9px] text-slate-500">
                              {member.category && (
                                <span>{member.category}</span>
                              )}
                              {member.similarity != null && (
                                <span>
                                  benzerlik: %
                                  {((member.similarity ?? 0) * 100).toFixed(0)}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}
