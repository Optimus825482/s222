"use client";

import { useState, useEffect, useCallback } from "react";
import { Brain, ToggleLeft, ToggleRight, Sliders, History, RefreshCw } from "lucide-react";
import { fetcher } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────
interface ReflexionConfig {
  enabled: boolean;
  auto_improve: boolean;
  score_threshold: number;
  max_iterations: number;
}

interface ReflexionResult {
  agent_role: string;
  score: number;
  issues: string[];
  improvements: string[];
  timestamp: string;
}

// ── Panel ─────────────────────────────────────────────────────
export function ReflexionSettingsPanel() {
  const [config, setConfig] = useState<ReflexionConfig>({
    enabled: true,
    auto_improve: true,
    score_threshold: 0.7,
    max_iterations: 3,
  });
  const [results, setResults] = useState<ReflexionResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  // Load config and results
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [configData, resultsData] = await Promise.all([
        fetcher<ReflexionConfig>("/api/reflexion/config").catch(() => null),
        fetcher<ReflexionResult[]>("/api/reflexion/results").catch(() => []),
      ]);
      if (configData) setConfig(configData);
      if (resultsData) setResults(resultsData);
    } catch (e) {
      console.error("Load error:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Save config
  const save = async () => {
    setSaving(true);
    setMsg("");
    try {
      await fetcher("/api/reflexion/config", {
        method: "POST",
        body: JSON.stringify(config),
      });
      setMsg("✓ Ayarlar kaydedildi");
      setTimeout(() => setMsg(""), 2000);
    } catch (e) {
      setMsg("✗ Kaydetme hatası");
    } finally {
      setSaving(false);
    }
  };

  // Toggle handlers
  const toggleEnabled = () => setConfig((c) => ({ ...c, enabled: !c.enabled }));
  const toggleAutoImprove = () => setConfig((c) => ({ ...c, auto_improve: !c.auto_improve }));

  // Score badge color
  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  if (loading) {
    return (
      <div className="p-4 text-center text-slate-500">
        <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
        Yükleniyor...
      </div>
    );
  }

  return (
    <div className="p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2 border-b pb-3">
        <Brain className="w-5 h-5 text-purple-500" />
        <h2 className="text-sm font-semibold">Reflexion Ayarları</h2>
      </div>

      {/* Settings */}
      <div className="space-y-4">
        {/* Enabled Toggle */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded border">
          <div>
            <div className="text-xs font-medium">Reflexion Aktif</div>
            <div className="text-[10px] text-slate-500">
              Agent yanıtlarını otomatik değerlendir
            </div>
          </div>
          <button
            onClick={toggleEnabled}
            className="flex items-center gap-1"
          >
            {config.enabled ? (
              <ToggleRight className="w-8 h-8 text-green-500" />
            ) : (
              <ToggleLeft className="w-8 h-8 text-slate-400" />
            )}
          </button>
        </div>

        {/* Auto-Improve Toggle */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded border">
          <div>
            <div className="text-xs font-medium">Otomatik İyileştirme</div>
            <div className="text-[10px] text-slate-500">
              Düşük skorlu yanıtları otomatik iyileştir
            </div>
          </div>
          <button
            onClick={toggleAutoImprove}
            disabled={!config.enabled}
            className="flex items-center gap-1 disabled:opacity-50"
          >
            {config.auto_improve ? (
              <ToggleRight className="w-8 h-8 text-green-500" />
            ) : (
              <ToggleLeft className="w-8 h-8 text-slate-400" />
            )}
          </button>
        </div>

        {/* Score Threshold Slider */}
        <div className="p-3 bg-slate-50 rounded border space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-xs font-medium">Skor Eşiği</div>
            <div className="text-xs font-mono bg-white px-2 py-0.5 rounded border">
              {config.score_threshold.toFixed(2)}
            </div>
          </div>
          <input
            type="range"
            min="0.5"
            max="0.95"
            step="0.05"
            value={config.score_threshold}
            onChange={(e) =>
              setConfig((c) => ({
                ...c,
                score_threshold: parseFloat(e.target.value),
              }))
            }
            disabled={!config.enabled}
            className="w-full disabled:opacity-50"
          />
          <div className="flex justify-between text-[9px] text-slate-400">
            <span>0.50 (Geçişken)</span>
            <span>0.95 (Katı)</span>
          </div>
        </div>

        {/* Max Iterations */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded border">
          <div>
            <div className="text-xs font-medium">Maks. İterasyon</div>
            <div className="text-[10px] text-slate-500">
              İyileştirme deneme sayısı
            </div>
          </div>
          <input
            type="number"
            min="1"
            max="5"
            value={config.max_iterations}
            onChange={(e) =>
              setConfig((c) => ({
                ...c,
                max_iterations: parseInt(e.target.value) || 3,
              }))
            }
            disabled={!config.enabled}
            className="w-16 text-center text-xs border rounded p-1 disabled:opacity-50"
          />
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-2">
        <button
          onClick={save}
          disabled={saving}
          className="flex-1 bg-purple-500 text-white text-xs py-2 rounded hover:bg-purple-600 disabled:opacity-50"
        >
          {saving ? "Kaydediliyor..." : "Kaydet"}
        </button>
        <button
          onClick={load}
          className="px-3 py-2 text-xs border rounded hover:bg-slate-50"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {msg && (
        <div className="text-xs text-center py-1">{msg}</div>
      )}

      {/* Recent Results */}
      <div className="border-t pt-4">
        <div className="flex items-center gap-2 mb-3">
          <History className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-medium">Son Değerlendirmeler</span>
        </div>

        {results.length === 0 ? (
          <div className="text-center text-slate-400 text-xs py-4">
            Henüz değerlendirme yok
          </div>
        ) : (
          <div className="space-y-2 max-h-60 overflow-auto">
            {results.map((r, i) => (
              <div
                key={i}
                className="p-2 bg-slate-50 rounded border text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium">{r.agent_role}</span>
                  <span className={`font-mono ${getScoreColor(r.score)}`}>
                    {r.score.toFixed(2)} {r.score >= 0.7 ? "✓" : "⚠"}
                  </span>
                </div>
                {r.issues.length > 0 && (
                  <div className="text-[10px] text-red-600">
                    Sorunlar: {r.issues.join(", ")}
                  </div>
                )}
                {r.improvements.length > 0 && (
                  <div className="text-[10px] text-green-600">
                    İyileştirmeler: {r.improvements.join(", ")}
                  </div>
                )}
                <div className="text-[9px] text-slate-400 mt-1">
                  {new Date(r.timestamp).toLocaleString("tr-TR")}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default ReflexionSettingsPanel;