"use client";

import { useState, useEffect, useCallback } from "react";
import { toolSelectorApi } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────── */

interface ToolUsageStats {
  tool: string;
  count: number;
  success: number;
  success_rate: number;
}

interface AgentToolStats {
  total_calls: number;
  top_tools: ToolUsageStats[];
  tool_diversity: number;
}

interface ToolPatternAnalysis {
  pattern_matrix: Record<string, AgentToolStats>;
  learned_preferences: Record<string, unknown>;
  context_categories: string[];
}

interface ContextRecommendation {
  input_summary: string;
  context_analysis: {
    primary_type: string;
    key_requirements: string[];
  };
  context_scores: { tool: string; score: number }[];
  user_suggestion: string | null;
  suggested_agent: string;
  confidence: number;
}

/* ── Constants ─────────────────────────────────────────────────── */

type OptTab = "patterns" | "recommendations" | "matrix" | "preferences";
const TABS: { key: OptTab; label: string; icon: string }[] = [
  { key: "patterns", label: "Usage Pattern'leri", icon: "📊" },
  { key: "recommendations", label: "Öneriler", icon: "💡" },
  { key: "matrix", label: "Agent-Tool Matrisi", icon: "🤖" },
  { key: "preferences", label: "Tercihler", icon: "⚙️" },
];

const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";

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

/* ── Tab 1: Usage Patterns ─────────────────────────────────────── */

function PatternsTab() {
  const [data, setData] = useState<ToolPatternAnalysis | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const patternData = await toolSelectorApi.getToolPatterns();
      setData(patternData);
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
  if (!data) return null;

  const matrix = data.pattern_matrix || {};
  const categories = data.context_categories || [];

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <StatCard
          label="Toplam Agent"
          value={Object.keys(matrix).length}
          accent="text-cyan-400"
        />
        <StatCard
          label="Kategori Sayısı"
          value={categories.length}
          accent="text-emerald-400"
        />
        <StatCard
          label="Öğrenilen Tercih"
          value={Object.keys(data.learned_preferences || {}).length}
          accent="text-amber-400"
        />
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Agent Tool Kullanım Dağılımı
        </h4>
        <div className="space-y-2">
          {Object.entries(matrix).length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">
              Yeterli kullanım verisi yok
            </p>
          )}
          {Object.entries(matrix).map(([agent, stats], i) => (
            <div
              key={agent}
              className="bg-slate-900/30 rounded-lg p-3 space-y-2"
            >
              <div className="flex justify-between items-center">
                <span className="text-xs font-semibold text-cyan-400">
                  {agent}
                </span>
                <span className="text-[10px] text-slate-500">
                  {stats.total_calls} toplam call
                </span>
              </div>
              <div className="space-y-1.5">
                {stats.top_tools.map((t, ti) => (
                  <Bar
                    key={ti}
                    v={t.count}
                    mx={stats.total_calls}
                    c={["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"][ti % 5]}
                    l={`${t.tool} (${t.success_rate}%)`}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Kategori Dağılımı
        </h4>
        <div className="flex flex-wrap gap-2">
          {categories.length === 0 && (
            <span className="text-xs text-slate-600">Henüz kategori yok</span>
          )}
          {categories.map((cat, i) => (
            <span
              key={i}
              className="px-2 py-1 bg-slate-700/60 text-slate-300 rounded text-xs"
            >
              {cat}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Tab 2: Recommendations ─────────────────────────────────────── */

function RecommendationsTab() {
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [taskInput, setTaskInput] = useState("");
  const [ld, setLd] = useState(false);
  const [e, setE] = useState("");

  const analyze = useCallback(async () => {
    if (!taskInput.trim()) return;
    try {
      setE("");
      setLd(true);
      const data = await toolSelectorApi.getSuggestedTools(taskInput);
      setSuggestion(JSON.stringify(data, null, 2));
    } catch (x) {
      setE(x instanceof Error ? x.message : "Analiz başarısız");
    } finally {
      setLd(false);
    }
  }, [taskInput]);

  const applySuggestion = async (
    tool: string,
    agent: string,
    success: boolean,
  ) => {
    if (!taskInput.trim() || !tool || !agent) return;
    try {
      await toolSelectorApi.applyToolSuggestion(taskInput, tool, agent, success);
      // Refresh suggestion
      const data = await toolSelectorApi.getSuggestedTools(taskInput);
      setSuggestion(JSON.stringify(data, null, 2));
    } catch (x) {
      setE(x instanceof Error ? x.message : "Öneri uygulanamadı");
    }
  };

  if (ld) return <Sk n={4} />;
  if (e) return <Er m={e} r={analyze} />;

  return (
    <div className="space-y-4">
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Görev Kontekstini Girin
        </h4>
        <textarea
          value={taskInput}
          onChange={(e) => setTaskInput(e.target.value)}
          placeholder="Örnek: 'Python ile bir web scraper yaz ve veriyi CSV'ye dönüştür'"
          className="w-full bg-slate-900/50 border border-slate-700/50 rounded px-3 py-2 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/50 min-h-[80px]"
        />
        <button
          onClick={analyze}
          disabled={!taskInput.trim() || ld}
          className="w-full mt-2 px-3 py-2 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-xs font-medium rounded border border-cyan-500/20 transition-colors disabled:opacity-40"
        >
          🔍 Öneri Oluştur
        </button>
      </div>

      {suggestion && taskInput && (
        <div className={crd}>
          <div className="flex justify-between items-center mb-3">
            <h4 className="text-xs font-medium text-slate-200">
              Kontekst ve Tool Önerisi
            </h4>
            <span className="text-[10px] text-slate-500">JSON Formatı</span>
          </div>
          <pre className="bg-slate-900/80 p-3 rounded text-[9px] text-slate-300 overflow-auto max-h-[300px]">
            {suggestion}
          </pre>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => applySuggestion("code_execute", "speed", true)}
              className="px-2 py-1 text-[9px] bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-400 rounded border border-emerald-500/20"
            >
              ✓ Code Execute (Speed)
            </button>
            <button
              onClick={() => applySuggestion("web_search", "researcher", true)}
              className="px-2 py-1 text-[9px] bg-cyan-600/15 hover:bg-cyan-600/25 text-cyan-400 rounded border border-cyan-500/20"
            >
              ✓ Web Search (Researcher)
            </button>
          </div>
        </div>
      )}

      {!suggestion && (
        <div className="text-center py-10 text-slate-600">
          <p className="text-xs">Bir görev girin ve örneği görün</p>
        </div>
      )}
    </div>
  );
}

/* ── Tab 3: Agent-Tool Matrix ───────────────────────────────────── */

function AgentToolMatrixTab() {
  const [data, setData] = useState<Record<string, any>>({});
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const matrixData = await toolSelectorApi.getAgentToolMatrix();
      setData(matrixData);
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

  const matrix = data.matrix || {};
  const categories = data.categories || [];

  return (
    <div className="space-y-4">
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Agent-Tool Etkileşim Matrisi
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="px-2 py-2 text-left text-slate-400">Agent</th>
                <th className="px-2 py-2 text-left text-slate-400">Toplam Call</th>
                <th className="px-2 py-2 text-left text-slate-400">Çeşitlilik</th>
                <th className="px-2 py-2 text-left text-slate-400">En İyi Tools</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {Object.entries(matrix).map(([agent, stats]: [string, any]) => (
                <tr key={agent} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-2 py-2 text-cyan-400">{agent}</td>
                  <td className="px-2 py-2 text-slate-300">{stats.total_calls}</td>
                  <td className="px-2 py-2 text-slate-300">
                    {stats.tool_diversity} tool
                  </td>
                  <td className="px-2 py-2">
                    <div className="flex flex-wrap gap-1">
                      {stats.top_tools?.slice(0, 3).map((t: any, i: number) => (
                        <span
                          key={i}
                          className="px-1.5 py-0.5 bg-slate-700/60 text-slate-400 rounded text-[8px]"
                        >
                          {t.tool} ({t.success_rate}%)
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
              {Object.keys(matrix).length === 0 && (
                <tr>
                  <td colSpan={4} className="px-2 py-4 text-center text-slate-500">
                    Veri yok - ilk task'ınızdyı tamamladıktan sonra burada veriler göreceksiniz
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {categories.length > 0 && (
        <div className={crd}>
          <h4 className="text-xs font-medium text-slate-200 mb-3">
            Context Categories
          </h4>
          <div className="flex flex-wrap gap-2">
            {categories.map((cat: string, i: number) => (
              <span
                key={i}
                className="px-2 py-1 bg-slate-700/60 text-slate-300 rounded text-xs"
              >
                {cat}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Tab 4: Preferences ────────────────────────────────────────── */

function PreferencesTab() {
  const [data, setData] = useState<Record<string, any>>({});
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const patternData = await toolSelectorApi.getToolPatterns();
      setData(patternData.learned_preferences || {});
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

  const preferences = Object.entries(data);

  return (
    <div className="space-y-3">
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Öğrenilen Tercihler
        </h4>
        {preferences.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-slate-600">
              Kullanıcı tercihleri burada görünecek
            </p>
            <p className="text-[10px] text-slate-500 mt-1">
              ÖğrenilenكافالارBu alan, necessity_fixed_task patterns'leri otomatik olarak öğrenilecektir
            </p>
          </div>
        ) : (
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {preferences.map(([key, value]: [string, any], i: number) => (
              <div
                key={i}
                className="bg-slate-900/30 border border-slate-700/30 rounded-lg p-3"
              >
                <div className="flex items-start gap-2">
                  <span className="text-[9px] px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 rounded border border-emerald-500/30 mt-0.5">
                    {"🟢"}
                  </span>
                  <div className="space-y-1">
                    <code className="text-[10px] text-cyan-300">{key}</code>
                    <pre className="text-[10px] text-slate-400 font-mono leading-relaxed">
                      {typeof value === "object"
                        ? JSON.stringify(value, null, 2)
                        : String(value)}
                    </pre>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────── */

export default function ToolOptimizerPanel() {
  const [tab, setTab] = useState<OptTab>("patterns");

  return (
    <div className="space-y-4">
      <nav
        className="flex gap-1 border-b border-slate-700/50"
        aria-label="Tool optimizer sekmeleri"
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
        {tab === "patterns" && <PatternsTab />}
        {tab === "recommendations" && <RecommendationsTab />}
        {tab === "matrix" && <AgentToolMatrixTab />}
        {tab === "preferences" && <PreferencesTab />}
      </div>
    </div>
  );
}
