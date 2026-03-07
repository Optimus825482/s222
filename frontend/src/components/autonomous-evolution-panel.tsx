"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type {
  AgentRole,
  ImprovementPlan,
  FailureLearning,
  ApplyLearningResult,
} from "@/lib/types";

// ── Shared Constants ────────────────────────────────────────────

const AGENT_ROLES: AgentRole[] = [
  "orchestrator",
  "thinker",
  "speed",
  "researcher",
  "reasoner",
  "critic",
];

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

const PRIORITY_STYLES: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/40",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/40",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  low: "bg-slate-500/20 text-slate-400 border-slate-500/40",
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

// ── Section 1: Improvement Plan View ────────────────────────────

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
      {/* Agent selector */}
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
          {/* Score + Summary */}
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
            {/* Score bar */}
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

          {/* Strengths & Weaknesses */}
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

          {/* Actions */}
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

// ── Section 2: Failure Learning View ────────────────────────────

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
      {/* Agent selector */}
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
          {/* Header stats */}
          <div className="bg-[#1a1f2e] border border-border rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-200">
                {learning.agent_name}
              </span>
              <span className="text-[10px] text-slate-500">
                {learning.total_failures} başarısız görev
              </span>
            </div>
            {/* Learning rate bar */}
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

          {/* Insights */}
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

          {/* Strategy Adjustments */}
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

              {/* Apply button */}
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

          {/* Apply result */}
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

// ── Main Panel ──────────────────────────────────────────────────

export function AutonomousEvolutionPanel() {
  return (
    <section className="space-y-6" aria-label="Özerk Gelişim Paneli">
      {/* Section 1: Improvement Plans */}
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">📋</span>
          Otomatik Geliştirme Planları
        </h3>
        <ImprovementPlanView />
      </div>

      <hr className="border-border" />

      {/* Section 2: Failure Learning */}
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">🧬</span>
          Başarısız Görevlerden Öğrenme
        </h3>
        <FailureLearningView />
      </div>
    </section>
  );
}
