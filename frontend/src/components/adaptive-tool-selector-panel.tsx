"use client";

import { useCallback, useEffect, useState } from "react";
import { fetcher } from "@/lib/api";
import { Wrench, TrendingUp, Grid3x3, Settings } from "lucide-react";

interface ToolUsage {
  tool_name: string;
  usage_count: number;
  success_rate: number;
  avg_latency_ms: number;
  last_used: string;
}

interface ToolRecommendation {
  tool_name: string;
  score: number;
  reason: string;
  context: string;
}

interface ToolPreference {
  tool_name: string;
  preference_score: number;
  user_id: string;
}

type Tab = "usage" | "recommendations" | "matrix" | "preferences";

export function AdaptiveToolSelectorPanel() {
  const [tab, setTab] = useState<Tab>("usage");
  const [usage, setUsage] = useState<ToolUsage[]>([]);
  const [recommendations, setRecommendations] = useState<ToolRecommendation[]>(
    [],
  );
  const [preferences, setPreferences] = useState<ToolPreference[]>([]);
  const [loading, setLoading] = useState(false);

  const loadUsage = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetcher<ToolUsage[]>("/api/adaptive-tools/usage");
      setUsage(data);
    } catch (err) {
      console.error("[AdaptiveTools] usage error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadRecommendations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetcher<ToolRecommendation[]>(
        "/api/adaptive-tools/recommendations",
      );
      setRecommendations(data);
    } catch (err) {
      console.error("[AdaptiveTools] recommendations error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPreferences = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetcher<ToolPreference[]>(
        "/api/adaptive-tools/preferences",
      );
      setPreferences(data);
    } catch (err) {
      console.error("[AdaptiveTools] preferences error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "usage") loadUsage();
    else if (tab === "recommendations") loadRecommendations();
    else if (tab === "preferences") loadPreferences();
  }, [tab, loadUsage, loadRecommendations, loadPreferences]);

  return (
    <div className="bg-surface rounded-lg border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface-raised">
        <Wrench className="w-5 h-5 text-cyan-400" />
        <h2 className="text-base font-semibold text-slate-200">
          Adaptif Araç Seçimi
        </h2>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border bg-surface-raised/50">
        <button
          onClick={() => setTab("usage")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "usage"
              ? "text-cyan-400 border-cyan-400 bg-cyan-400/5"
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          <Wrench className="w-4 h-4" />
          Kullanım
        </button>
        <button
          onClick={() => setTab("recommendations")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "recommendations"
              ? "text-cyan-400 border-cyan-400 bg-cyan-400/5"
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Öneriler
        </button>
        <button
          onClick={() => setTab("matrix")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "matrix"
              ? "text-cyan-400 border-cyan-400 bg-cyan-400/5"
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          <Grid3x3 className="w-4 h-4" />
          Matris
        </button>
        <button
          onClick={() => setTab("preferences")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "preferences"
              ? "text-cyan-400 border-cyan-400 bg-cyan-400/5"
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          <Settings className="w-4 h-4" />
          Tercihler
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {loading ? (
          <div className="text-center py-8 text-slate-500">Yükleniyor...</div>
        ) : tab === "usage" ? (
          <div className="space-y-2">
            {usage.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                Henüz araç kullanımı yok
              </div>
            ) : (
              usage.map((u) => (
                <div
                  key={u.tool_name}
                  className="p-3 rounded-lg bg-surface-raised border border-border"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-200">
                      {u.tool_name}
                    </span>
                    <span className="text-xs text-slate-500">
                      {u.usage_count} kullanım
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <span className="text-slate-500">Başarı: </span>
                      <span className="text-emerald-400">
                        {(u.success_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Gecikme: </span>
                      <span className="text-cyan-400">
                        {u.avg_latency_ms.toFixed(0)}ms
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Son: </span>
                      <span className="text-slate-400">
                        {new Date(u.last_used).toLocaleDateString("tr-TR")}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : tab === "recommendations" ? (
          <div className="space-y-2">
            {recommendations.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                Henüz öneri yok
              </div>
            ) : (
              recommendations.map((r, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-surface-raised border border-border"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-200">
                      {r.tool_name}
                    </span>
                    <span className="text-xs px-2 py-1 rounded bg-cyan-400/10 text-cyan-400">
                      Skor: {r.score.toFixed(2)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-1">{r.reason}</p>
                  <p className="text-xs text-slate-500">{r.context}</p>
                </div>
              ))
            )}
          </div>
        ) : tab === "matrix" ? (
          <div className="text-center py-8 text-slate-500">
            Araç matris görünümü yakında eklenecek
          </div>
        ) : (
          <div className="space-y-2">
            {preferences.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                Henüz tercih yok
              </div>
            ) : (
              preferences.map((p) => (
                <div
                  key={p.tool_name}
                  className="p-3 rounded-lg bg-surface-raised border border-border"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-200">
                      {p.tool_name}
                    </span>
                    <span className="text-xs text-slate-400">
                      Tercih: {p.preference_score.toFixed(2)}
                    </span>
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
