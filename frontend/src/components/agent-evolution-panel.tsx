"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type {
  AgentLeaderboardEntry,
  AgentRole,
  ApplyLearningResult,
  AutoDiscoveryResult,
  FailureLearning,
  ImprovementPlan,
  ProactiveSuggestionsResponse,
  SkillRecommendation,
} from "@/lib/types";
import { AGENT_ROLES, ROLE_ICON, ROLE_COLOR } from "@/lib/constants";

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

// ── Tab Constants ───────────────────────────────────────────────

type TabKey = "gelisim" | "ozerk-evrim";

const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: "gelisim", label: "Gelişim", icon: "📊" },
  { key: "ozerk-evrim", label: "Özerk Evrim", icon: "🧬" },
];

// ── Section: Agent Performance Comparison ───────────────────────

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

// ── Section: Proactive Skill Suggestions ────────────────────────

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

// ── Section: Skill Recommendations ──────────────────────────────

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
              <div className="flex items-start justify-between gap-2">
                <h4 className="text-xs font-medium text-slate-200 leading-snug">
                  {skill.name}
                </h4>
                <span className="flex-shrink-0 text-[10px] font-bold tabular-nums text-emerald-400">
                  %{((skill.relevance_score ?? 0) * 100).toFixed(0)}
                </span>
              </div>

              <p className="text-[11px] text-slate-400 leading-snug line-clamp-2">
                {skill.description}
              </p>

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

// ── Section: Auto Discovery ─────────────────────────────────────

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

// ── Section: Improvement Plan View ──────────────────────────────

const PRIORITY_STYLES: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/40",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/40",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  low: "bg-slate-500/20 text-slate-400 border-slate-500/40",
};

function ImprovementPlanView() {
  const [selectedRole, setSelectedRole] = useState<AgentRole>("orchestrator");
  const [plan, setPlan] = useState<ImprovementPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPlan = useCallback(async (role: AgentRole) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getImprovementPlan(role);
      setPlan(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan alınamadı");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlan(selectedRole);
  }, [fetchPlan, selectedRole]);

  return (
    <div className="space-y-3">
      <div className="flex gap-1.5 flex-wrap">
        {AGENT_ROLES.map((role) => (
          <button
            key={role}
            type="button"
            onClick={() => setSelectedRole(role)}
            className={`px-2.5 py-1.5 text-[11px] font-medium rounded-sm border transition-all duration-200 ${
              selectedRole === role
                ? "bg-white/10 border-white/20 text-white"
                : "bg-transparent border-slate-700 text-slate-500 hover:text-slate-300 hover:border-slate-600"
            }`}
            style={
              selectedRole === role
                ? { borderColor: ROLE_COLOR[role], color: ROLE_COLOR[role] }
                : undefined
            }
            aria-label={`${role} geliştirme planı`}
            aria-pressed={selectedRole === role}
          >
            <span aria-hidden="true">{ROLE_ICON[role]}</span> {role}
          </button>
        ))}
      </div>

      {loading && (
        <div className="space-y-2">
          <Skeleton className="h-16 rounded-lg" />
          <Skeleton className="h-10 rounded-lg" />
          <Skeleton className="h-10 rounded-lg" />
        </div>
      )}

      {error && <InlineError message={error} />}

      {plan && !loading && (
        <div className="space-y-3">
          <div className="bg-[#1a1f2e] border border-border rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-200">
                {plan.agent_name}
              </span>
              <div className="flex items-center gap-2">
                <span
                  className={`text-lg font-bold tabular-nums ${
                    plan.overall_score >= 75
                      ? "text-emerald-400"
                      : plan.overall_score >= 50
                        ? "text-amber-400"
                        : "text-red-400"
                  }`}
                >
                  {(plan.overall_score ?? 0).toFixed(0)}
                </span>
                <span className="text-[10px] text-slate-500">/100</span>
              </div>
            </div>
            <div className="h-2 rounded-full bg-slate-800 overflow-hidden mb-2">
              <div
                className={`h-full rounded-full transition-all duration-700 ${
                  plan.overall_score >= 75
                    ? "bg-emerald-500"
                    : plan.overall_score >= 50
                      ? "bg-amber-500"
                      : "bg-red-500"
                }`}
                style={{ width: `${Math.min(plan.overall_score, 100)}%` }}
                role="progressbar"
                aria-valuenow={plan.overall_score}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              {plan.summary}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-2.5">
              <h4 className="text-[10px] font-semibold text-emerald-400 mb-1.5">
                💪 Güçlü Yönler
              </h4>
              <ul className="space-y-1" role="list">
                {plan.strengths.map((s, i) => (
                  <li
                    key={i}
                    className="text-[10px] text-slate-300 leading-snug"
                  >
                    • {s}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-2.5">
              <h4 className="text-[10px] font-semibold text-red-400 mb-1.5">
                ⚠️ Zayıf Yönler
              </h4>
              <ul className="space-y-1" role="list">
                {plan.weaknesses.map((w, i) => (
                  <li
                    key={i}
                    className="text-[10px] text-slate-300 leading-snug"
                  >
                    • {w}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {plan.actions.length > 0 && (
            <div className="space-y-1.5" role="list" aria-label="Aksiyon planı">
              {plan.actions.map((action) => (
                <div
                  key={action.id}
                  className="bg-[#1a1f2e] border border-border rounded-lg p-2.5 hover:border-slate-600 transition-colors"
                  role="listitem"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="text-[11px] font-medium text-slate-200">
                      {action.title}
                    </span>
                    <span
                      className={`flex-shrink-0 text-[9px] px-1.5 py-0.5 rounded-sm border ${PRIORITY_STYLES[action.priority] || PRIORITY_STYLES.low}`}
                    >
                      {action.priority === "critical"
                        ? "KRİTİK"
                        : action.priority === "high"
                          ? "YÜKSEK"
                          : action.priority === "medium"
                            ? "ORTA"
                            : "DÜŞÜK"}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-snug mb-1.5">
                    {action.description}
                  </p>
                  <div className="flex gap-3 text-[9px] text-slate-500">
                    <span>
                      Etki:{" "}
                      <span className="text-slate-300">
                        {action.expected_impact}
                      </span>
                    </span>
                    <span>
                      Efor:{" "}
                      <span className="text-slate-300">
                        {action.estimated_effort}
                      </span>
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Section: Failure Learning View ──────────────────────────────

function FailureLearningView() {
  const [selectedRole, setSelectedRole] = useState<AgentRole>("orchestrator");
  const [learning, setLearning] = useState<FailureLearning | null>(null);
  const [applyResult, setApplyResult] = useState<ApplyLearningResult | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLearning = useCallback(async (role: AgentRole) => {
    setLoading(true);
    setError(null);
    setApplyResult(null);
    try {
      const data = await api.getFailureLearnings(role);
      setLearning(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analiz alınamadı");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLearning(selectedRole);
  }, [fetchLearning, selectedRole]);

  const handleApply = async () => {
    setApplying(true);
    try {
      const result = await api.applyLearning(selectedRole);
      setApplyResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Uygulama başarısız");
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-1.5 flex-wrap">
        {AGENT_ROLES.map((role) => (
          <button
            key={role}
            type="button"
            onClick={() => setSelectedRole(role)}
            className={`px-2.5 py-1.5 text-[11px] font-medium rounded-sm border transition-all duration-200 ${
              selectedRole === role
                ? "bg-white/10 border-white/20 text-white"
                : "bg-transparent border-slate-700 text-slate-500 hover:text-slate-300 hover:border-slate-600"
            }`}
            style={
              selectedRole === role
                ? { borderColor: ROLE_COLOR[role], color: ROLE_COLOR[role] }
                : undefined
            }
            aria-label={`${role} hata analizi`}
            aria-pressed={selectedRole === role}
          >
            <span aria-hidden="true">{ROLE_ICON[role]}</span> {role}
          </button>
        ))}
      </div>

      {loading && (
        <div className="space-y-2">
          <Skeleton className="h-12 rounded-lg" />
          <Skeleton className="h-20 rounded-lg" />
        </div>
      )}

      {error && <InlineError message={error} />}

      {learning && !loading && (
        <div className="space-y-3">
          <div className="bg-[#1a1f2e] border border-border rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-200">
                {learning.agent_name}
              </span>
              <span className="text-[10px] text-slate-500">
                {learning.total_failures} başarısız görev
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-500 w-20">
                Öğrenme Hızı
              </span>
              <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    learning.learning_rate >= 0.7
                      ? "bg-emerald-500"
                      : learning.learning_rate >= 0.4
                        ? "bg-amber-500"
                        : "bg-red-500"
                  }`}
                  style={{
                    width: `${Math.min(learning.learning_rate * 100, 100)}%`,
                  }}
                  role="progressbar"
                  aria-valuenow={learning.learning_rate * 100}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
              <span className="text-[10px] font-bold text-slate-300 tabular-nums w-10 text-right">
                %{((learning.learning_rate ?? 0) * 100).toFixed(0)}
              </span>
            </div>
          </div>

          {learning.insights.length > 0 && (
            <div
              className="space-y-1.5"
              role="list"
              aria-label="Öğrenme içgörüleri"
            >
              {learning.insights.map((insight, i) => (
                <div
                  key={i}
                  className="bg-[#1a1f2e] border border-border rounded-lg p-2.5 hover:border-slate-600 transition-colors"
                  role="listitem"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-medium text-slate-200">
                      {insight.pattern}
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded-sm border ${
                        insight.auto_applied
                          ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                          : "bg-amber-500/15 text-amber-400 border-amber-500/30"
                      }`}
                    >
                      {insight.auto_applied ? "Uygulandı" : "Bekliyor"}
                    </span>
                  </div>
                  {insight.frequency > 0 && (
                    <span className="text-[9px] text-slate-500">
                      Sıklık: {insight.frequency}×
                    </span>
                  )}
                  {insight.resolution && (
                    <p className="text-[10px] text-slate-400 mt-1 leading-snug">
                      💡 {insight.resolution}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {learning.strategy_adjustments.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-[10px] font-semibold text-slate-400">
                Strateji Ayarlamaları
              </h4>
              {learning.strategy_adjustments.map((adj, i) => (
                <div
                  key={i}
                  className="bg-[#1a1f2e] border border-border rounded-lg p-2.5"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <code className="text-[10px] text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded">
                      {adj.parameter}
                    </code>
                    <span className="text-[9px] text-slate-500">
                      {adj.old_value} → {adj.new_value}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-snug">
                    {adj.reason}
                  </p>
                </div>
              ))}

              <button
                type="button"
                onClick={handleApply}
                disabled={applying}
                className="w-full px-4 py-2 text-xs font-medium rounded-sm border transition-all duration-200 bg-cyan-600/20 text-cyan-400 border-cyan-500/40 hover:bg-cyan-600/30 hover:border-cyan-500/60 disabled:opacity-40 disabled:cursor-not-allowed"
                aria-label="Öğrenimleri uygula"
              >
                {applying ? (
                  <span className="inline-flex items-center gap-1.5">
                    <span className="w-3 h-3 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
                    Uygulanıyor...
                  </span>
                ) : (
                  "🧬 Öğrenimleri Uygula"
                )}
              </button>
            </div>
          )}

          {applyResult && (
            <div className="bg-[#1a1f2e] border border-emerald-500/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[11px] font-medium text-emerald-400">
                  ✅ Uygulama Sonucu
                </span>
                <span className="text-[10px] text-slate-400">
                  {applyResult.applied_count} uygulandı,{" "}
                  {applyResult.skipped_count} atlandı
                </span>
              </div>
              <div className="space-y-1">
                {applyResult.details.map((d, i) => (
                  <div key={i} className="flex items-center gap-2 text-[10px]">
                    <span
                      className={
                        d.result === "applied"
                          ? "text-emerald-400"
                          : "text-slate-500"
                      }
                    >
                      {d.result === "applied" ? "✓" : "–"}
                    </span>
                    <span className="text-slate-300">{d.action}</span>
                    <span className="text-slate-500 text-[9px]">
                      ({d.reason})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Gelişim Tab Content ─────────────────────────────────────────

function GelisimContent() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">📊</span>
          Ajan Performans Karşılaştırması
        </h3>
        <AgentPerformanceChart />
      </div>

      <hr className="border-border" />

      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">🔮</span>
          Proaktif Skill Önerileri
        </h3>
        <ProactiveSkillSuggestions />
      </div>

      <hr className="border-border" />

      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">💡</span>
          Yetenek Önerileri
        </h3>
        <SkillRecommendations />
      </div>

      <hr className="border-border" />

      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">🔎</span>
          Otomatik Keşif
        </h3>
        <AutoDiscovery />
      </div>
    </div>
  );
}

// ── Özerk Evrim Tab Content ─────────────────────────────────────

function OzerkEvrimContent() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">📋</span>
          Otomatik Geliştirme Planları
        </h3>
        <ImprovementPlanView />
      </div>

      <hr className="border-border" />

      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">🧬</span>
          Başarısız Görevlerden Öğrenme
        </h3>
        <FailureLearningView />
      </div>
    </div>
  );
}

// ── Unified Main Panel ──────────────────────────────────────────

function UnifiedEvolutionPanel({ defaultTab = "gelisim" as TabKey }) {
  const [activeTab, setActiveTab] = useState<TabKey>(defaultTab);

  return (
    <section className="space-y-4" aria-label="Özerk Gelişim Paneli">
      {/* Tab buttons */}
      <div className="flex gap-1.5" role="tablist" aria-label="Panel sekmeleri">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            aria-controls={`tabpanel-${tab.key}`}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 text-xs rounded-md transition-all duration-200 ${
              activeTab === tab.key
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40"
                : "text-slate-500 border border-transparent hover:text-slate-300 hover:border-slate-700"
            }`}
          >
            <span aria-hidden="true">{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      <div
        id={`tabpanel-${activeTab}`}
        role="tabpanel"
        aria-label={TABS.find((t) => t.key === activeTab)?.label}
      >
        {activeTab === "gelisim" ? <GelisimContent /> : <OzerkEvrimContent />}
      </div>
    </section>
  );
}

// ── Exports ─────────────────────────────────────────────────────

export function AgentEvolutionPanel() {
  return <UnifiedEvolutionPanel defaultTab="gelisim" />;
}

export function AutonomousEvolutionPanel() {
  return <UnifiedEvolutionPanel defaultTab="ozerk-evrim" />;
}
