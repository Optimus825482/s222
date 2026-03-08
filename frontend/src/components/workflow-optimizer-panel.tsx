"use client";

import { useCallback, useEffect, useState } from "react";
import { fetcher } from "@/lib/api";
import { Zap, TrendingUp, FileText, BookOpen } from "lucide-react";

interface WorkflowStats {
  total_workflows: number;
  avg_execution_time: number;
  success_rate: number;
  optimization_potential: number;
}

interface OptimizationSuggestion {
  workflow_id: string;
  suggestion: string;
  impact: "high" | "medium" | "low";
  estimated_improvement: string;
}

interface WorkflowDetail {
  id: string;
  name: string;
  execution_count: number;
  avg_time: number;
  success_rate: number;
  last_run: string;
}

interface PatternLibrary {
  pattern_name: string;
  description: string;
  use_cases: string[];
  performance_impact: string;
}

type Tab = "overview" | "suggestions" | "details" | "patterns";

export function WorkflowOptimizerPanel() {
  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<WorkflowStats | null>(null);
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [details, setDetails] = useState<WorkflowDetail[]>([]);
  const [patterns, setPatterns] = useState<PatternLibrary[]>([]);
  const [loading, setLoading] = useState(false);

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetcher<WorkflowStats>(
        "/api/workflow-optimizer/stats",
      );
      setStats(data);
    } catch (err) {
      console.error("[WorkflowOptimizer] stats error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSuggestions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetcher<OptimizationSuggestion[]>(
        "/api/workflow-optimizer/suggestions",
      );
      setSuggestions(data);
    } catch (err) {
      console.error("[WorkflowOptimizer] suggestions error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDetails = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetcher<WorkflowDetail[]>(
        "/api/workflow-optimizer/details",
      );
      setDetails(data);
    } catch (err) {
      console.error("[WorkflowOptimizer] details error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPatterns = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetcher<PatternLibrary[]>(
        "/api/workflow-optimizer/patterns",
      );
      setPatterns(data);
    } catch (err) {
      console.error("[WorkflowOptimizer] patterns error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "overview") loadStats();
    else if (tab === "suggestions") loadSuggestions();
    else if (tab === "details") loadDetails();
    else if (tab === "patterns") loadPatterns();
  }, [tab, loadStats, loadSuggestions, loadDetails, loadPatterns]);

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case "high":
        return "text-red-400 bg-red-400/10";
      case "medium":
        return "text-yellow-400 bg-yellow-400/10";
      case "low":
        return "text-emerald-400 bg-emerald-400/10";
      default:
        return "text-slate-400 bg-slate-400/10";
    }
  };

  return (
    <div className="bg-surface rounded-lg border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface-raised">
        <Zap className="w-5 h-5 text-orange-400" />
        <h2 className="text-base font-semibold text-slate-200">
          Workflow Optimizasyonu
        </h2>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border bg-surface-raised/50">
        <button
          onClick={() => setTab("overview")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "overview"
              ? "text-orange-400 border-orange-400 bg-orange-400/5"
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          <Zap className="w-4 h-4" />
          Genel Bakış
        </button>
        <button
          onClick={() => setTab("suggestions")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "suggestions"
              ? "text-orange-400 border-orange-400 bg-orange-400/5"
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Öneriler
        </button>
        <button
          onClick={() => setTab("details")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "details"
              ? "text-orange-400 border-orange-400 bg-orange-400/5"
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          <FileText className="w-4 h-4" />
          Detay
        </button>
        <button
          onClick={() => setTab("patterns")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "patterns"
              ? "text-orange-400 border-orange-400 bg-orange-400/5"
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          <BookOpen className="w-4 h-4" />
          Pattern Kütüphanesi
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {loading ? (
          <div className="text-center py-8 text-slate-500">Yükleniyor...</div>
        ) : tab === "overview" ? (
          stats ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-surface-raised border border-border">
                <div className="text-xs text-slate-500 mb-1">
                  Toplam Workflow
                </div>
                <div className="text-2xl font-bold text-slate-200">
                  {stats.total_workflows}
                </div>
              </div>
              <div className="p-4 rounded-lg bg-surface-raised border border-border">
                <div className="text-xs text-slate-500 mb-1">Ort. Süre</div>
                <div className="text-2xl font-bold text-cyan-400">
                  {(stats.avg_execution_time ?? 0).toFixed(1)}s
                </div>
              </div>
              <div className="p-4 rounded-lg bg-surface-raised border border-border">
                <div className="text-xs text-slate-500 mb-1">Başarı Oranı</div>
                <div className="text-2xl font-bold text-emerald-400">
                  {((stats.success_rate ?? 0) * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-4 rounded-lg bg-surface-raised border border-border">
                <div className="text-xs text-slate-500 mb-1">
                  Optimizasyon Potansiyeli
                </div>
                <div className="text-2xl font-bold text-orange-400">
                  {((stats.optimization_potential ?? 0) * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">Veri yok</div>
          )
        ) : tab === "suggestions" ? (
          <div className="space-y-2">
            {suggestions.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                Henüz öneri yok
              </div>
            ) : (
              suggestions.map((s, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-surface-raised border border-border"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-200">
                      {s.workflow_id}
                    </span>
                    <span
                      className={`text-xs px-2 py-1 rounded ${getImpactColor(s.impact)}`}
                    >
                      {s.impact}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-1">{s.suggestion}</p>
                  <p className="text-xs text-emerald-400">
                    Tahmini iyileştirme: {s.estimated_improvement}
                  </p>
                </div>
              ))
            )}
          </div>
        ) : tab === "details" ? (
          <div className="space-y-2">
            {details.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                Henüz workflow detayı yok
              </div>
            ) : (
              details.map((d) => (
                <div
                  key={d.id}
                  className="p-3 rounded-lg bg-surface-raised border border-border"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-200">
                      {d.name}
                    </span>
                    <span className="text-xs text-slate-500">
                      {d.execution_count} çalıştırma
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <span className="text-slate-500">Ort. Süre: </span>
                      <span className="text-cyan-400">
                        {(d.avg_time ?? 0).toFixed(1)}s
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Başarı: </span>
                      <span className="text-emerald-400">
                        {((d.success_rate ?? 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Son: </span>
                      <span className="text-slate-400">
                        {new Date(d.last_run).toLocaleDateString("tr-TR")}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {patterns.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                Henüz pattern yok
              </div>
            ) : (
              patterns.map((p, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-surface-raised border border-border"
                >
                  <div className="text-sm font-medium text-slate-200 mb-2">
                    {p.pattern_name}
                  </div>
                  <p className="text-xs text-slate-400 mb-2">{p.description}</p>
                  <div className="text-xs text-slate-500 mb-1">
                    Kullanım Alanları:
                  </div>
                  <ul className="text-xs text-slate-400 list-disc list-inside mb-2">
                    {p.use_cases.map((uc, j) => (
                      <li key={j}>{uc}</li>
                    ))}
                  </ul>
                  <div className="text-xs text-emerald-400">
                    Performans Etkisi: {p.performance_impact}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
