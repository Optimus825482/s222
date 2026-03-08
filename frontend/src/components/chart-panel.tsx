"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BarChart3, Download, RefreshCw } from "lucide-react";
import Image from "next/image";

interface ChartData {
  id: string;
  title: string;
  chart_type: string;
  image_base64: string;
  created_at: string;
}

type ChartType =
  | "line"
  | "bar"
  | "scatter"
  | "pie"
  | "heatmap"
  | "histogram"
  | "box";

export function ChartPanel() {
  const [charts, setCharts] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [selectedType, setSelectedType] = useState<ChartType>("line");

  const loadCharts = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listCharts(30);
      const mapped: ChartData[] = list.map((c) => ({
        id: c.chart_id,
        title: c.chart_id,
        chart_type: "",
        image_base64: "",
        created_at: c.created_at,
      }));
      setCharts(mapped);
      // Load images in background
      for (let i = 0; i < mapped.length; i++) {
        try {
          const detail = await api.getChart(mapped[i].id);
          setCharts((prev) => {
            const next = [...prev];
            const idx = next.findIndex((x) => x.id === mapped[i].id);
            if (idx !== -1 && detail?.image_base64)
              next[idx] = { ...next[idx], image_base64: detail.image_base64, title: detail.chart_id || next[idx].title };
            return next;
          });
        } catch {
          // 404 or auth for single chart; skip
        }
      }
    } catch {
      setCharts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCharts();
  }, [loadCharts]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const sampleData = { x: [1, 2, 3, 4, 5], y: [10, 15, 13, 17, 20] };
      const title = `${selectedType.toUpperCase()} Grafik - ${new Date().toLocaleString("tr-TR")}`;
      await api.generateChart(selectedType, sampleData, title, 800, 450);
      loadCharts();
    } catch {
      // Error already surfaced by api
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = (chart: ChartData) => {
    if (!chart.image_base64) return;
    const link = document.createElement("a");
    link.href = `data:image/png;base64,${chart.image_base64}`;
    link.download = `${chart.title.replace(/\s+/g, "_")}.png`;
    link.click();
  };

  return (
    <div className="bg-surface rounded-lg border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface-raised">
        <BarChart3 className="w-5 h-5 text-purple-400" />
        <h2 className="text-base font-semibold text-slate-200">
          Grafik Üretici
        </h2>
        <button
          onClick={loadCharts}
          disabled={loading}
          className="ml-auto p-2 rounded-lg hover:bg-surface-overlay transition-colors disabled:opacity-50"
          aria-label="Yenile"
        >
          <RefreshCw
            className={`w-4 h-4 text-slate-400 ${loading ? "animate-spin" : ""}`}
          />
        </button>
      </div>

      {/* Chart Type Selector */}
      <div className="p-4 border-b border-border bg-surface-raised/50">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs text-slate-500">Grafik Tipi:</span>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as ChartType)}
            className="px-3 py-1 text-sm bg-surface border border-border rounded-lg text-slate-200"
          >
            <option value="line">Çizgi</option>
            <option value="bar">Çubuk</option>
            <option value="scatter">Dağılım</option>
            <option value="pie">Pasta</option>
            <option value="heatmap">Isı Haritası</option>
            <option value="histogram">Histogram</option>
            <option value="box">Kutu</option>
          </select>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-4 py-1 text-sm bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {generating ? "Oluşturuluyor..." : "Örnek Oluştur"}
          </button>
        </div>
        <p className="text-xs text-slate-500">
          7 farklı grafik tipi • Dark theme • Base64 encoding
        </p>
      </div>

      {/* Charts Grid */}
      <div className="p-4">
        {loading ? (
          <div className="text-center py-8 text-slate-500">Yükleniyor...</div>
        ) : charts.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            Henüz grafik yok. Yukarıdan örnek oluşturabilirsiniz.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {charts.map((chart) => (
              <div
                key={chart.id}
                className="p-3 rounded-lg bg-surface-raised border border-border"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-slate-200">
                    {chart.title}
                  </span>
                  <button
                    onClick={() => handleDownload(chart)}
                    className="p-1 rounded hover:bg-surface-overlay transition-colors"
                    aria-label="İndir"
                  >
                    <Download className="w-4 h-4 text-slate-400" />
                  </button>
                </div>
                <div className="relative w-full aspect-video bg-slate-900 rounded overflow-hidden">
                  {chart.image_base64 ? (
                    <Image
                      src={`data:image/png;base64,${chart.image_base64}`}
                      alt={chart.title}
                      fill
                      className="object-contain"
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">
                      Yükleniyor…
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
                  <span className="px-2 py-1 rounded bg-purple-400/10 text-purple-400">
                    {chart.chart_type}
                  </span>
                  <span>
                    {new Date(chart.created_at).toLocaleDateString("tr-TR")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
