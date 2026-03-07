"use client";

import { useState, useEffect, useCallback } from "react";
import { workflowOptimizerApi } from "@/lib/api";
import { WORKFLOW_TEMPLATES } from "@/lib/workflow-templates"; // This will be a local file

/* ── Types ─────────────────────────────────────────────────────── */

interface OptimizationSuggestion {
  suggestion_id: string;
  workflow_id: string;
  workflow_name: string;
  type: string;
  current_state: string;
  suggested_change: string;
  estimated_impact: string;
  confidence: number;
  automated: boolean;
}

interface WorkflowOptimizerStats {
  total_executions_analyzed: number;
  slow_workflows: number;
  error_workflows: number;
  global_patterns: {
    type: string;
    pattern: string;
    occurrence_count: number;
    suggestion: string;
  }[];
}

interface WorkflowStats {
  name: string;
  executions: any[];
  stats: {
    total_executions: number;
    success_count: number;
    failure_count: number;
    avg_duration_ms: number;
    min_duration_ms: number;
    max_duration_ms: number;
    error_rate_pct: number;
  };
}

interface OptimizationResult {
  original_steps: Array<{ step_id: string; step_type: string }>;
  suggestions: {
    type: string;
    severity: string;
    current: string;
    suggestion: string;
    affected_steps: string[];
  }[];
  optimized_steps: Array<{ step_id: string; step_type: string }>;
  applied: string[];
  recommendations: string[];
}

/* ── Constants ─────────────────────────────────────────────────── */

type OptTab = "overview" | "suggestions" | "workflow" | "patterns";
const TABS: { key: OptTab; label: string; icon: string }[] = [
  { key: "overview", label: "Genel Bakış", icon: "📊" },
  { key: "suggestions", label: "Optimizasyon Önerileri", icon: "💡" },
  { key: "workflow", label: "Workflow Detailed", icon: "🚀" },
  { key: "patterns", label: "Pattern Library", icon: "摞" },
];

const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";

const CATEGORY_STYLE: Record<string, string> = {
  performance: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  reliability: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  quality: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  cost: "bg-amber-500/15 text-amber-400 border-amber-500/30",
};

const PRIORITY_STYLE: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  low: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};

const PRIORITY_LABEL: Record<string, string> = {
  critical: "Kritik",
  high: "Yüksek",
  medium: "Orta",
  low: "Düşük",
};

/* ── Helpers ────────────────────────────────────────────────────── */

function Sk({ n = 4 }: { n?: number }) {
  return (
    <div
      className="space-y-3 animate-pulse"
      role="status"
      aria-label="Yükleniyor"
    >
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="h-8 bg-slate-700/40 rounded" />
      ))}
    </div>
  );
}

function Er({ m, r }: { m: string; r: () => void }) {
  return (
    <div className="flex flex-col items-center gap-2 py-8">
      <span className="text-xs text-red-400">⚠️ {m}</span>
      <button
        onClick={r}
        className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded transition-colors"
      >
        Tekrar Dene
      </button>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 flex-1 min-w-0">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider truncate">
        {label}
      </div>
      <div
        className={`text-lg font-bold tabular-nums ${accent ?? "text-slate-200"}`}
      >
        {value}
      </div>
    </div>
  );
}

function Bar({ v, mx, c, l }: { v: number; mx: number; c: string; l: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-400 w-24 truncate" title={l}>
        {l}
      </span>
      <div className="flex-1 bg-slate-700/50 rounded-full h-2 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${mx > 0 ? Math.min((v / mx) * 100, 100) : 0}%`,
            backgroundColor: c,
          }}
        />
      </div>
      <span className="text-[10px] text-slate-500 w-8 text-right tabular-nums">
        {v}
      </span>
    </div>
  );
}

const CL = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
];

/* ── Tab 1: Overview ───────────────────────────────────────────── */

function OverviewTab() {
  const [stats, setStats] = useState<WorkflowOptimizerStats | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await workflowOptimizerApi.getStats();
      setStats(data);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const optimizeAll = useCallback(async () => {
    try {
      setAnalyzing(true);
      await workflowOptimizerApi.optimizeTemplate("research-and-report");
      await load();
    } catch {
    } finally {
      setAnalyzing(false);
    }
  }, [load]);

  if (ld) return <Sk n={5} />;
  if (e) return <Er m={e} r={load} />;
  if (!stats) return null;

  const byCategory = [
    { label: "Performans", value: stats.global_patterns.filter((p: any) => p.type.includes("performance")).length, color: "#3b82f6" },
    { label: "Güvenilirlik", value: stats.global_patterns.filter((p: any) => p.type.includes("reliability")).length, color: "#10b981" },
    { label: "Tekrarlayan", value: stats.global_patterns.filter((p: any) => p.type.includes("sequential")).length, color: "#f59e0b" },
    { label: "Hız", value: stats.global_patterns.filter((p: any) => p.type.includes("slow")).length, color: "#ef4444" },
  ];
  const maxCat = Math.max(...byCategory.map((c) => c.value), 1);

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <StatCard
          label="Analiz Edilen Executions"
          value={stats.total_executions_analyzed}
          accent="text-cyan-400"
        />
        <StatCard
          label="Yavaş Workflows"
          value={stats.slow_workflows}
          accent="text-amber-400"
        />
        <StatCard
          label="Hatalı Workflows"
          value={stats.error_workflows}
          accent="text-red-400"
        />
        <StatCard
          label="Global Pattern"
          value={stats.global_patterns.length}
          accent="text-emerald-400"
        />
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Pattern Kategorileri
        </h4>
        <div className="space-y-2">
          {byCategory.map((cat, i) => (
            <Bar
              key={i}
              v={cat.value}
              mx={maxCat}
              c={cat.color}
              l={`${cat.label}: ${cat.value}`}
            />
          ))}
        </div>
      </div>

      {stats.global_patterns.length > 0 && (
        <div className={crd}>
          <h4 className="text-xs font-medium text-slate-200 mb-3">
            En Yaygın Pattern'ler
          </h4>
          <div className="space-y-2 max-h-[250px] overflow-y-auto">
            {stats.global_patterns.map((p: any, i: number) => (
              <div
                key={i}
                className="bg-slate-900/30 rounded-lg p-3 text-[10px]"
              >
                <div className="flex items-start gap-2">
                  <span className="text-[9px] px-1.5 py-0.5 rounded border border-blue-500/30 text-blue-400 mt-0.5">
                    {i + 1}
                  </span>
                  <div className="space-y-1 flex-1">
                    <div className="flex justify-between">
                      <code className="text-cyan-300">{p.pattern}</code>
                      <span className="text-slate-500">x{p.occurrence_count}</span>
                    </div>
                    <p className="text-slate-400">{p.suggestion}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={optimizeAll}
        disabled={analyzing}
        className="w-full px-3 py-2 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-xs font-medium rounded border border-cyan-500/20 transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {analyzing ? (
          <span className="inline-block w-3 h-3 border border-cyan-400 border-t-transparent rounded-full animate-spin" />
        ) : (
          "🔍"
        )}
        {analyzing ? "Optimize Ediliyor…" : "Tüm Patterns ile Optimize Et"}
      </button>
    </div>
  );
}

/* ── Tab 2: Suggestions ────────────────────────────────────────── */

function SuggestionsTab() {
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [template, setTemplate] = useState("");
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [applied, setApplied] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const { suggestions: s } = await workflowOptimizerApi.getSuggestions(template || undefined);
      setSuggestions(Array.isArray(s) ? s : []);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, [template]);

  useEffect(() => {
    load();
  }, [load]);

  const applySuggestion = async (sid: string) => {
    try {
      setApplied((prev) => new Set(prev).add(sid));
      // For now just simulate application
      // In production, call apply endpoint
      await new Promise((r) => setTimeout(r, 500));
    } catch {
    } finally {
    }
  };

  const templates = Object.keys(WORKFLOW_TEMPLATES || {});
  if (templates.length === 0) {
    templates.push("research-and-report");
  }

  if (ld) return <Sk n={4} />;
  if (e) return <Er m={e} r={load} />;

  if (suggestions.length === 0) {
    return (
      <div className="text-center py-10">
        <div className="text-3xl mb-2">💡</div>
        <p className="text-xs text-slate-500">Öneri Yok</p>
        <p className="text-[10px] text-slate-600 mt-1">
          "Patterns" sekmesinden global pattern'leri seeing
          veya bir template seçin
        </p>
      </div>
    );
  }

  const getImpactColor = (impact: string) => {
    if (impact.includes("30%") || impact.includes("40%") || impact.includes("50%")) return "text-emerald-400";
    if (impact.includes("20%") || impact.includes("25%")) return "text-amber-400";
    return "text-slate-400";
  };

  return (
    <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
      {/* Template selector */}
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-2">
          Template Seçin
        </h4>
        <select
          value={template}
          onChange={(e) => setTemplate(e.target.value)}
          className="w-full bg-slate-900/60 border border-slate-700/50 rounded px-2 py-2 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/50"
        >
          {templates.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {suggestions.map((s) => (
        <div
          key={s.suggestion_id}
          className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2.5 hover:border-slate-600/40 transition-colors"
        >
          <div className="flex items-start gap-2 mb-1.5">
            <span className="text-xs font-medium text-slate-200 flex-1">
              {s.suggested_change}
            </span>
            <span
              className={`text-[9px] px-1.5 py-0.5 rounded border ${
                s.confidence > 70
                  ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                  : "bg-amber-500/15 text-amber-400 border-amber-500/30"
              }`}
            >
              % {s.confidence.toFixed(0)} confidence
            </span>
          </div>
          <div className="space-y-1.5">
            <div className="text-[11px] text-slate-400">
              <span className="text-slate-500">Mevcut: </span>
              <code className="text-slate-300 bg-slate-900/50 px-1 rounded">
                {s.current_state}
              </code>
            </div>
            <div className="text-[10px]">
              <span className="text-slate-500">Etki: </span>
              <span className={getImpactColor(s.estimated_impact)}>
                {s.estimated_impact}
              </span>
            </div>
            <div className="flex justify-end">
              {s.automated ? (
                <button
                  onClick={() => applySuggestion(s.suggestion_id)}
                  disabled={applied.has(s.suggestion_id)}
                  className="px-2 py-1 text-[9px] bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-400 rounded border border-emerald-500/20 transition-colors disabled:opacity-40"
                >
                  {applied.has(s.suggestion_id) ? "✓ Uygulandı" : "Otomatik Uygula"}
                </button>
              ) : (
                <span className="text-[9px] text-slate-500 px-2">
                  Manuel onay gerektirir
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Tab 3: Workflow Detailed ──────────────────────────────────── */

function WorkflowDetailedTab() {
  const [workflowId, setWorkflowId] = useState("");
  const [workflowName, setWorkflowName] = useState("");
  const [stats, setStats] = useState<WorkflowStats | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    if (!workflowId) return;
    try {
      setE("");
      setLd(true);
      const data = await workflowOptimizerApi.getWorkflowStats(workflowId);
      setStats(data);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, [workflowId]);

  useEffect(() => {
    if (workflowId) load();
  }, [workflowId, load]);

  const templates = Object.keys(WORKFLOW_TEMPLATES || {});
  if (templates.length === 0) {
    templates.push("research-and-report");
  }

  return (
    <div className="space-y-4">
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Workflow Seçin
        </h4>
        <select
          value={workflowId}
          onChange={(e) => {
            setWorkflowId(e.target.value);
            setWorkflowName(e.target.options[e.target.selectedIndex].text);
          }}
          className="w-full bg-slate-900/60 border border-slate-700/50 rounded px-2 py-2 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/50"
        >
          {templates.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {ld ? (
        <Sk n={5} />
      ) : e ? (
        <Er m={e} r={load} />
      ) : !stats ? null : (
        <div className="space-y-4">
          {/* Stats grid */}
          <div className="flex gap-3 flex-wrap">
            <StatCard
              label="Toplam Executions"
              value={stats.stats.total_executions}
              accent="text-cyan-400"
            />
            <StatCard
              label="Başarılı"
              value={stats.stats.success_count}
              accent="text-emerald-400"
            />
            <StatCard
              label="Başarısız"
              value={stats.stats.failure_count}
              accent="text-red-400"
            />
            <StatCard
              label="Avg Süre"
              value={`${Math.round(stats.stats.avg_duration_ms)}ms`}
              accent="text-amber-400"
            />
            <StatCard
              label="Hata Oranı"
              value={`${stats.stats.error_rate_pct}%`}
              accent={stats.stats.error_rate_pct > 20 ? "text-red-400" : "text-slate-200"}
            />
          </div>

          {/* Excecution history */}
          <div className={crd}>
            <h4 className="text-xs font-medium text-slate-200 mb-3">
              Execution Geçmişi
            </h4>
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {stats.executions.length === 0 && (
                <p className="text-xs text-slate-600 text-center py-4">Henüz execution yok</p>
              )}
              {stats.executions.map((exec: any, i: number) => (
                <div
                  key={i}
                  className="flex items-center gap-2 text-[10px] p-2 rounded bg-slate-900/30"
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      exec.status === "completed" ? "bg-emerald-500" : "bg-red-500"
                    }`}
                  />
                  <span className="flex-1 text-slate-400 truncate">
                    {exec.workflow_id}
                  </span>
                  <span className="text-slate-500 tabular-nums">
                    {exec.duration_ms}ms
                  </span>
                  <span className="text-slate-500">
                    {exec.step_count} step
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Tab 4: Pattern Library ────────────────────────────────────── */

function PatternLibraryTab() {
  const [stats, setStats] = useState<WorkflowOptimizerStats | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await workflowOptimizerApi.getStats();
      setStats(data);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (ld) return <Sk n={5} />;
  if (e) return <Er m={e} r={load} />;

  const patterns = stats?.global_patterns || [];

  return (
    <div className="space-y-4">
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Pattern Severity Dağılımı
        </h4>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <h5 className="text-[10px] text-blue-400">Performance</h5>
            {patterns.filter((p: any) => p.type.includes("slow") || p.type.includes("performance")).map((p: any, i: number) => (
              <div key={i} className="text-[10px] bg-blue-500/10 px-2 py-1.5 rounded border border-blue-500/20">
                <div className="font-semibold text-blue-300">{p.pattern}</div>
                <div className="text-slate-500 mt-0.5">{p.suggestion}</div>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <h5 className="text-[10px] text-amber-400">Reliability</h5>
            {patterns.filter((p: any) => p.type.includes("reliability") || p.type.includes("error")).map((p: any, i: number) => (
              <div key={i} className="text-[10px] bg-amber-500/10 px-2 py-1.5 rounded border border-amber-500/20">
                <div className="font-semibold text-amber-300">{p.pattern}</div>
                <div className="text-slate-500 mt-0.5">{p.suggestion}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Tekrarlayan Pattern'ler
        </h4>
        <div className="space-y-2">
          {patterns.filter((p: any) => p.type.includes("sequential") || p.type.includes("tool")).map((p: any, i: number) => (
            <div
              key={i}
              className="bg-slate-900/30 border border-slate-700/30 rounded-lg p-3"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[9px] px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded border border-purple-500/30">
                  x{p.occurrence_count}
                </span>
                <code className="text-xs text-cyan-300">{p.pattern}</code>
              </div>
              <p className="text-[10px] text-slate-400">{p.suggestion}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────── */

export default function WorkflowOptimizerPanel() {
  const [tab, setTab] = useState<OptTab>("overview");

  return (
    <div className="space-y-4">
      <nav
        className="flex gap-1 border-b border-slate-700/50"
        aria-label="Workflow optimizer sekmeleri"
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-xs transition-colors border-b-2 ${
              tab === t.key
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
            aria-selected={tab === t.key}
            role="tab"
          >
            {t.icon} {t.label}
          </button>
        ))}
      </nav>

      <div role="tabpanel">
        {tab === "overview" && <OverviewTab />}
        {tab === "suggestions" && <SuggestionsTab />}
        {tab === "workflow" && <WorkflowDetailedTab />}
        {tab === "patterns" && <PatternLibraryTab />}
      </div>
    </div>
  );
}
