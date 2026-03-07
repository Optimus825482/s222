"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type {
  AgentLeaderboardEntry,
  AgentRole,
  SkillRecommendation,
  AutoDiscoveryResult,
  ProactiveSuggestionsResponse,
} from "@/lib/types";

// ── Shared Constants ────────────────────────────────────────────

const ROLE_ICON: Record<AgentRole, string> = {
  orchestrator: "🧠",
  thinker: "🔬",
  speed: "⚡",
  researcher: "🔍",
  reasoner: "🌊",
  critic: "🎯",
};

const ROLE_COLOR: Record<AgentRole, string> = {
  orchestrator: "#ec4899",
  thinker: "#00e5ff",
  speed: "#a78bfa",
  researcher: "#f59e0b",
  reasoner: "#10b981",
  critic: "#06b6d4",
};

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

// ── Section 1: Agent Performance Comparison ─────────────────────

function AgentPerformanceChart() {
  const [entries, setEntries] = useState<AgentLeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const data = await api.getAgentLeaderboard();
      setEntries(data.sort((a, b) => b.score - a.score));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Veri alınamadı");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="space-y-2" aria-label="Performans verileri yükleniyor">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-8 rounded" />
        ))}
      </div>
    );
  }

  if (error) return <InlineError message={error} />;

  const maxScore = Math.max(...entries.map((e) => e.score), 1);

  return (
    <div
      className="space-y-2.5"
      role="list"
      aria-label="Agent performans sıralaması"
    >
      {entries.map((entry) => {
        const pct = (entry.score / maxScore) * 100;
        return (
          <div
            key={entry.role}
            className="group relative"
            role="listitem"
            aria-label={`${entry.name}: skor ${(entry.score ?? 0).toFixed(0)}`}
          >
            {/* Agent label row */}
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-sm" aria-hidden="true">
                  {ROLE_ICON[entry.role]}
                </span>
                <span
                  className="text-xs font-medium truncate"
                  style={{ color: ROLE_COLOR[entry.role] }}
                >
                  {entry.name}
                </span>
                {entry.rank === 1 && (
                  <span className="text-[10px]" aria-label="Birinci sıra">
                    👑
                  </span>
                )}
              </div>
              <span className="text-xs font-bold text-slate-200 tabular-nums">
                {(entry.score ?? 0).toFixed(0)}
              </span>
            </div>

            {/* Bar */}
            <div className="h-2.5 rounded-sm bg-slate-800 overflow-hidden">
              <div
                className="h-full rounded-sm transition-all duration-700 ease-out"
                style={{
                  width: `${Math.min(pct, 100)}%`,
                  backgroundColor: ROLE_COLOR[entry.role],
                  opacity: 0.85,
                }}
                role="progressbar"
                aria-valuenow={entry.score}
                aria-valuemin={0}
                aria-valuemax={maxScore}
              />
            </div>

            {/* Hover detail row */}
            <div className="flex gap-3 mt-1 text-[10px] text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity">
              <span>
                Başarı:{" "}
                <span className="text-slate-300">
                  {(entry.success_rate ?? 0).toFixed(1)}%
                </span>
              </span>
              <span>
                Gecikme:{" "}
                <span className="text-slate-300">
                  {(entry.avg_latency_ms ?? 0).toFixed(0)}ms
                </span>
              </span>
              <span>
                Verim:{" "}
                <span className="text-slate-300">
                  {(entry.efficiency ?? 0).toFixed(2)}
                </span>
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Section 2: Proactive Skill Suggestions ─────────────────────

const CATEGORY_STYLE: Record<
  string,
  { bg: string; border: string; text: string }
> = {
  usage_pattern: {
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    text: "text-blue-400",
  },
  error_recovery: {
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    text: "text-red-400",
  },
  behavior_insight: {
    bg: "bg-purple-500/10",
    border: "border-purple-500/30",
    text: "text-purple-400",
  },
  teaching_based: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    text: "text-amber-400",
  },
  trending: {
    bg: "bg-orange-500/10",
    border: "border-orange-500/30",
    text: "text-orange-400",
  },
};

const CATEGORY_LABEL: Record<string, string> = {
  usage_pattern: "Kullanım Deseni",
  error_recovery: "Hata Kurtarma",
  behavior_insight: "Davranış Analizi",
  teaching_based: "Öğretim Bazlı",
  trending: "Trend",
};

const ACTION_LABEL: Record<string, { label: string; cls: string }> = {
  install: {
    label: "Yükle",
    cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  },
  learn: {
    label: "Öğren",
    cls: "bg-sky-500/20 text-sky-400 border-sky-500/30",
  },
  activate: {
    label: "Etkinleştir",
    cls: "bg-violet-500/20 text-violet-400 border-violet-500/30",
  },
};

function ProactiveSkillSuggestions() {
  const [data, setData] = useState<ProactiveSuggestionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getProactiveSkillSuggestions();
      setData(res);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Veri alınamadı");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) return <InlineError message={error} />;

  const suggestions = data?.suggestions ?? [];
  const summary = data?.analysis_summary;

  return (
    <div className="space-y-3">
      {/* Analysis summary */}
      {summary && (
        <div className="flex flex-wrap gap-2 text-[10px] text-slate-500">
          <span>🔧 {summary.tools_analyzed} araç</span>
          <span>·</span>
          <span>👤 {summary.behaviors_analyzed} davranış</span>
          <span>·</span>
          <span>📚 {summary.teachings_count} öğreti</span>
          <span>·</span>
          <span>💬 {summary.threads_scanned} sohbet</span>
        </div>
      )}

      {suggestions.length === 0 ? (
        <div className="text-xs text-slate-500 text-center py-6 space-y-1">
          <span className="text-2xl block">🔮</span>
          <p>Henüz yeterli veri yok — sistemi kullandıkça öneriler oluşacak.</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
          {suggestions.map((s) => {
            const style = CATEGORY_STYLE[s.category] ?? CATEGORY_STYLE.trending;
            const action =
              ACTION_LABEL[s.suggested_action] ?? ACTION_LABEL.learn;
            return (
              <article
                key={s.id}
                className={`${style.bg} border ${style.border} rounded-lg p-3 space-y-2 hover:brightness-110 transition-all`}
                aria-label={`Öneri: ${s.skill_name}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-base shrink-0" aria-hidden="true">
                      {s.icon}
                    </span>
                    <h4
                      className={`text-xs font-semibold truncate ${style.text}`}
                    >
                      {s.skill_name}
                    </h4>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${action.cls}`}
                    >
                      {action.label}
                    </span>
                    <span className="text-[10px] font-bold tabular-nums text-emerald-400">
                      %{Math.round(s.confidence * 100)}
                    </span>
                  </div>
                </div>

                <p className="text-[11px] text-slate-400 leading-snug">
                  {s.reason}
                </p>

                <div className="flex items-center justify-between">
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded-sm ${style.bg} ${style.text} border ${style.border}`}
                  >
                    {CATEGORY_LABEL[s.category] ?? s.category}
                  </span>
                  <span className="text-[9px] text-slate-600 truncate max-w-[140px]">
                    {s.source_data}
                  </span>
                </div>

                {/* Confidence bar */}
                <div className="h-1 rounded-full bg-slate-700/50 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-500"
                    style={{ width: `${Math.min(s.confidence * 100, 100)}%` }}
                    role="progressbar"
                    aria-valuenow={s.confidence * 100}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`Güven: %${Math.round(s.confidence * 100)}`}
                  />
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* Refresh button */}
      <button
        onClick={fetchSuggestions}
        disabled={loading}
        className="w-full py-2 text-[11px] font-medium text-slate-400 bg-slate-800/40 border border-slate-700/50 rounded-lg hover:bg-slate-700/40 hover:text-slate-200 disabled:opacity-40 transition-colors"
        aria-label="Önerileri yenile"
      >
        🔄 Analizi Yenile
      </button>
    </div>
  );
}

// ── Section 3: Skill Recommendations ────────────────────────────

function SkillRecommendations() {
  const [skills, setSkills] = useState<SkillRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const fetchSkills = useCallback(async (q = "") => {
    setLoading(true);
    try {
      const data = await api.getSkillRecommendations(q);
      setSkills(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Veri alınamadı");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  const handleSearch = () => {
    if (query.trim()) fetchSkills(query.trim());
  };

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Yetenek ara..."
          className="flex-1 bg-slate-800/60 border border-slate-700 rounded-sm px-2.5 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-slate-500 transition-colors"
          aria-label="Yetenek arama"
        />
        <button
          onClick={handleSearch}
          disabled={!query.trim()}
          className="px-3 py-1.5 text-xs font-medium bg-slate-700 text-slate-200 rounded-sm border border-slate-600 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          aria-label="Ara"
        >
          Ara
        </button>
      </div>

      {error && <InlineError message={error} />}

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : skills.length === 0 ? (
        <div className="text-xs text-slate-500 text-center py-4">
          Öneri bulunamadı
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[280px] overflow-y-auto pr-1">
          {skills.map((skill) => (
            <article
              key={skill.skill_id}
              className="bg-[#1a1f2e] border border-border rounded-lg p-3 space-y-2 hover:border-slate-600 transition-colors"
              aria-label={`Yetenek: ${skill.name}`}
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-2">
                <h4 className="text-xs font-medium text-slate-200 leading-snug">
                  {skill.name}
                </h4>
                <span className="flex-shrink-0 text-[10px] font-bold tabular-nums text-emerald-400">
                  %{((skill.relevance_score ?? 0) * 100).toFixed(0)}
                </span>
              </div>

              {/* Description */}
              <p className="text-[11px] text-slate-400 leading-snug line-clamp-2">
                {skill.description}
              </p>

              {/* Footer: category + agent */}
              <div className="flex items-center justify-between">
                <span className="text-[10px] px-1.5 py-0.5 rounded-sm bg-slate-700/60 text-slate-300 border border-slate-600/50">
                  {skill.category}
                </span>
                {skill.recommended_agent && (
                  <span
                    className="flex items-center gap-1 text-[10px]"
                    style={{ color: ROLE_COLOR[skill.recommended_agent] }}
                  >
                    <span aria-hidden="true">
                      {ROLE_ICON[skill.recommended_agent]}
                    </span>
                    {skill.recommended_agent}
                  </span>
                )}
              </div>

              {/* Relevance bar */}
              <div className="h-1 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                  style={{
                    width: `${Math.min(skill.relevance_score * 100, 100)}%`,
                  }}
                  role="progressbar"
                  aria-valuenow={skill.relevance_score * 100}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`Uygunluk: %${((skill.relevance_score ?? 0) * 100).toFixed(0)}`}
                />
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Section 3: Auto Discovery ───────────────────────────────────

function AutoDiscovery() {
  const [result, setResult] = useState<AutoDiscoveryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDiscover = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.autoDiscoverSkills();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Keşif başarısız");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <button
          onClick={handleDiscover}
          disabled={loading}
          className="px-4 py-2 text-xs font-medium rounded-sm border transition-all duration-200 bg-emerald-600/20 text-emerald-400 border-emerald-500/40 hover:bg-emerald-600/30 hover:border-emerald-500/60 disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Otomatik yetenek keşfi başlat"
        >
          {loading ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="w-3 h-3 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
              Keşfediliyor...
            </span>
          ) : (
            "🔎 Keşfi Başlat"
          )}
        </button>

        {result && !loading && (
          <span className="text-[11px] text-slate-400">
            <span className="text-emerald-400 font-medium">
              {result.discovered}
            </span>{" "}
            yeni yetenek bulundu
          </span>
        )}
      </div>

      {error && <InlineError message={error} />}

      {result && result.skills.length > 0 && (
        <div
          className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1"
          role="list"
          aria-label="Keşfedilen yetenekler"
        >
          {result.skills.map((skill) => (
            <div
              key={skill.skill_id}
              className="flex items-center justify-between bg-[#1a1f2e] border border-border rounded-lg px-3 py-2 hover:border-slate-600 transition-colors"
              role="listitem"
            >
              <div className="min-w-0">
                <div className="text-xs font-medium text-slate-200 truncate">
                  {skill.name}
                </div>
                <div className="text-[10px] text-slate-500 truncate">
                  {skill.pattern}
                </div>
              </div>
              <span className="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded-sm bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                Yeni
              </span>
            </div>
          ))}
        </div>
      )}

      {result && result.skills.length === 0 && (
        <div className="text-xs text-slate-500 text-center py-3">
          Yeni yetenek bulunamadı — sistem güncel
        </div>
      )}
    </div>
  );
}

// ── Main Panel ──────────────────────────────────────────────────

export function AgentEvolutionPanel() {
  return (
    <section className="space-y-6" aria-label="Özerk Gelişim Paneli">
      {/* Section 1: Performance Comparison */}
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">📊</span>
          Ajan Performans Karşılaştırması
        </h3>
        <AgentPerformanceChart />
      </div>

      <hr className="border-border" />

      {/* Section 2: Proactive Skill Suggestions */}
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">🔮</span>
          Proaktif Skill Önerileri
        </h3>
        <ProactiveSkillSuggestions />
      </div>

      <hr className="border-border" />

      {/* Section 3: Skill Recommendations */}
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">💡</span>
          Yetenek Önerileri
        </h3>
        <SkillRecommendations />
      </div>

      <hr className="border-border" />

      {/* Section 4: Auto Discovery */}
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">🔎</span>
          Otomatik Keşif
        </h3>
        <AutoDiscovery />
      </div>
    </section>
  );
}
