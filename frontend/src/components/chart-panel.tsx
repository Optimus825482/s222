"use client";

import { useState, useCallback } from "react";
import {
  BarChart3,
  LineChart,
  PieChart,
  Activity,
  Image,
  Download,
  Trash2,
  Plus,
  Loader2,
  HelpCircle,
  LayoutGrid,
  Layers,
  Grid3X3,
  AreaChart,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ChartResult, ChartListItem } from "@/lib/types";

type Tab = "create" | "gallery" | "guide";

const CHART_TYPES = [
  { key: "bar", label: "Bar", icon: BarChart3 },
  { key: "line", label: "Çizgi", icon: LineChart },
  { key: "pie", label: "Pasta", icon: PieChart },
  { key: "scatter", label: "Dağılım", icon: Activity },
  { key: "histogram", label: "Histogram", icon: Layers },
  { key: "area", label: "Alan", icon: AreaChart },
  { key: "heatmap", label: "Isı Haritası", icon: Grid3X3 },
];

const TABS: { key: Tab; label: string; icon: typeof BarChart3 }[] = [
  { key: "create", label: "Oluştur", icon: Plus },
  { key: "gallery", label: "Galeri", icon: LayoutGrid },
  { key: "guide", label: "Nasıl Kullanılır", icon: HelpCircle },
];

const SAMPLE_DATA: Record<string, string> = {
  bar: JSON.stringify(
    {
      labels: ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs"],
      values: [120, 190, 150, 210, 180],
      xlabel: "Aylar",
      ylabel: "Satış",
    },
    null,
    2,
  ),
  line: JSON.stringify(
    {
      labels: ["Pzt", "Sal", "Çar", "Per", "Cum"],
      datasets: [
        { label: "Ziyaretçi", values: [100, 200, 150, 300, 250] },
        { label: "Kayıt", values: [30, 50, 40, 80, 60] },
      ],
      xlabel: "Gün",
      ylabel: "Sayı",
    },
    null,
    2,
  ),
  pie: JSON.stringify(
    {
      labels: ["Chrome", "Firefox", "Safari", "Edge", "Diğer"],
      values: [65, 15, 10, 7, 3],
    },
    null,
    2,
  ),
  scatter: JSON.stringify(
    {
      x: [1, 2, 3, 4, 5, 6, 7, 8],
      y: [2, 4, 3, 6, 5, 8, 7, 9],
      sizes: [50, 80, 60, 120, 90, 150, 100, 130],
    },
    null,
    2,
  ),
  histogram: JSON.stringify(
    {
      values: [1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 6, 6, 7],
      bins: 10,
    },
    null,
    2,
  ),
  area: JSON.stringify(
    {
      labels: ["Q1", "Q2", "Q3", "Q4"],
      datasets: [
        { label: "Gelir", values: [100, 150, 200, 250] },
        { label: "Gider", values: [80, 100, 130, 160] },
      ],
    },
    null,
    2,
  ),
  heatmap: JSON.stringify(
    {
      matrix: [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
      ],
      xlabels: ["A", "B", "C"],
      ylabels: ["X", "Y", "Z"],
    },
    null,
    2,
  ),
};

export function ChartPanel() {
  const [tab, setTab] = useState<Tab>("create");
  const [chartType, setChartType] = useState("bar");
  const [title, setTitle] = useState("Grafik Başlığı");
  const [dataJson, setDataJson] = useState(SAMPLE_DATA.bar);
  const [width, setWidth] = useState(800);
  const [height, setHeight] = useState(450);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ChartResult | null>(null);
  const [error, setError] = useState("");

  // Gallery state
  const [charts, setCharts] = useState<ChartListItem[]>([]);
  const [galleryLoading, setGalleryLoading] = useState(false);
  const [selectedChart, setSelectedChart] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const handleTypeChange = useCallback((type: string) => {
    setChartType(type);
    setDataJson(SAMPLE_DATA[type] || SAMPLE_DATA.bar);
    setResult(null);
    setError("");
  }, []);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const parsed = JSON.parse(dataJson);
      const res = await api.generateChart(
        chartType,
        parsed,
        title,
        width,
        height,
      );
      if (res.error) {
        setError(res.error);
      } else {
        setResult(res);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Grafik oluşturulamadı");
    } finally {
      setLoading(false);
    }
  }, [chartType, dataJson, title, width, height]);

  const handleDownload = useCallback(() => {
    if (!result?.image_base64) return;
    const link = document.createElement("a");
    link.href = `data:image/png;base64,${result.image_base64}`;
    link.download = `${result.chart_id || "chart"}.png`;
    link.click();
  }, [result]);

  const loadGallery = useCallback(async () => {
    setGalleryLoading(true);
    try {
      const list = await api.listCharts(30);
      setCharts(list);
    } catch {
      setCharts([]);
    } finally {
      setGalleryLoading(false);
    }
  }, []);

  const viewChart = useCallback(async (chartId: string) => {
    setSelectedChart(chartId);
    setSelectedImage(null);
    try {
      const res = await api.getChart(chartId);
      setSelectedImage(res.image_base64);
    } catch {
      setSelectedImage(null);
    }
  }, []);

  const deleteChart = useCallback(
    async (chartId: string) => {
      try {
        await api.deleteChart(chartId);
        setCharts((prev) => prev.filter((c) => c.chart_id !== chartId));
        if (selectedChart === chartId) {
          setSelectedChart(null);
          setSelectedImage(null);
        }
      } catch {
        /* ignore */
      }
    },
    [selectedChart],
  );

  return (
    <div className="flex flex-col h-full bg-black text-white">
      {/* Tabs */}
      <div className="flex gap-1 p-2 border-b border-zinc-800 bg-zinc-900/50">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => {
                setTab(t.key);
                if (t.key === "gallery") loadGallery();
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                tab === t.key
                  ? "bg-blue-600 text-white"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      <div className="flex-1 overflow-auto p-3">
        {/* ── Create Tab ── */}
        {tab === "create" && (
          <div className="space-y-4">
            {/* Chart type selector */}
            <div>
              <label className="text-xs text-zinc-400 mb-1.5 block">
                Grafik Tipi
              </label>
              <div className="grid grid-cols-4 gap-2">
                {CHART_TYPES.map((ct) => {
                  const Icon = ct.icon;
                  return (
                    <button
                      key={ct.key}
                      onClick={() => handleTypeChange(ct.key)}
                      className={`flex flex-col items-center gap-1 p-2.5 rounded-lg border text-xs transition-all ${
                        chartType === ct.key
                          ? "border-blue-500 bg-blue-500/10 text-blue-400"
                          : "border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-500"
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      {ct.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Title */}
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Başlık</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
                placeholder="Grafik başlığı..."
              />
            </div>

            {/* Data JSON */}
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">
                Veri (JSON)
              </label>
              <textarea
                value={dataJson}
                onChange={(e) => setDataJson(e.target.value)}
                rows={8}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-xs font-mono text-green-400 focus:border-blue-500 focus:outline-none resize-y"
                spellCheck={false}
              />
            </div>

            {/* Size */}
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-xs text-zinc-400 mb-1 block">
                  Genişlik (px)
                </label>
                <input
                  type="number"
                  value={width}
                  onChange={(e) => setWidth(Number(e.target.value))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="flex-1">
                <label className="text-xs text-zinc-400 mb-1 block">
                  Yükseklik (px)
                </label>
                <input
                  type="number"
                  value={height}
                  onChange={(e) => setHeight(Number(e.target.value))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Generate button */}
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg py-2.5 text-sm font-medium transition-colors"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <BarChart3 className="w-4 h-4" />
              )}
              {loading ? "Oluşturuluyor..." : "Grafik Oluştur"}
            </button>

            {/* Error */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-xs">
                {error}
              </div>
            )}

            {/* Result */}
            {result && result.image_base64 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-400">
                    {result.chart_type} — {result.width}×{result.height}
                  </span>
                  <button
                    onClick={handleDownload}
                    className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
                  >
                    <Download className="w-3.5 h-3.5" />
                    İndir
                  </button>
                </div>
                <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-2 flex items-center justify-center">
                  {/* eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text */}
                  <img
                    src={`data:image/png;base64,${result.image_base64}`}
                    alt={result.title}
                    className="max-w-full rounded-lg"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Gallery Tab ── */}
        {tab === "gallery" && (
          <div className="space-y-3">
            {galleryLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
              </div>
            ) : charts.length === 0 ? (
              <div className="text-center py-12 text-zinc-500 text-sm">
                <Image className="w-10 h-10 mx-auto mb-2 opacity-30" aria-hidden="true" />
                Henüz grafik oluşturulmamış
              </div>
            ) : (
              <>
                {/* Selected chart preview */}
                {selectedChart && selectedImage && (
                  <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-zinc-400 font-mono">
                        {selectedChart}
                      </span>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            const link = document.createElement("a");
                            link.href = `data:image/png;base64,${selectedImage}`;
                            link.download = `${selectedChart}.png`;
                            link.click();
                          }}
                          className="text-blue-400 hover:text-blue-300"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedChart(null);
                            setSelectedImage(null);
                          }}
                          className="text-zinc-500 hover:text-zinc-300"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`data:image/png;base64,${selectedImage}`}
                      alt={selectedChart}
                      className="max-w-full rounded-lg"
                    />
                  </div>
                )}

                {/* Grid */}
                <div className="grid grid-cols-2 gap-2">
                  {charts.map((c) => (
                    <div
                      key={c.chart_id}
                      className={`bg-zinc-900 border rounded-lg p-2 cursor-pointer transition-all hover:border-blue-500/50 ${
                        selectedChart === c.chart_id
                          ? "border-blue-500"
                          : "border-zinc-700"
                      }`}
                      onClick={() => viewChart(c.chart_id)}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] text-zinc-500 font-mono truncate max-w-[70%]">
                          {c.chart_id}
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteChart(c.chart_id);
                          }}
                          className="text-zinc-600 hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                      <div className="text-[10px] text-zinc-600">
                        {new Date(c.created_at).toLocaleString("tr-TR")} ·{" "}
                        {(c.size_bytes / 1024).toFixed(1)} KB
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* ── Guide Tab ── */}
        {tab === "guide" && (
          <div className="space-y-4 text-sm text-zinc-300">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-blue-400" />
                Grafik Oluşturma
              </h3>
              <p className="text-zinc-400 text-xs leading-relaxed">
                7 farklı grafik tipi desteklenir: Bar, Çizgi, Pasta, Dağılım,
                Histogram, Alan ve Isı Haritası. Her tip için örnek veri
                otomatik yüklenir.
              </p>
            </div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <Activity className="w-4 h-4 text-green-400" />
                Veri Formatı
              </h3>
              <div className="text-xs text-zinc-400 space-y-2">
                <p>
                  <span className="text-blue-400">Bar/Çizgi/Alan:</span>{" "}
                  {`{ labels: [...], values: [...] }`} veya çoklu seri için{" "}
                  {`{ labels: [...], datasets: [{ label, values }] }`}
                </p>
                <p>
                  <span className="text-blue-400">Pasta:</span>{" "}
                  {`{ labels: [...], values: [...] }`}
                </p>
                <p>
                  <span className="text-blue-400">Dağılım:</span>{" "}
                  {`{ x: [...], y: [...], sizes?: [...] }`}
                </p>
                <p>
                  <span className="text-blue-400">Histogram:</span>{" "}
                  {`{ values: [...], bins?: 20 }`}
                </p>
                <p>
                  <span className="text-blue-400">Isı Haritası:</span>{" "}
                  {`{ matrix: [[...]], xlabels: [...], ylabels: [...] }`}
                </p>
              </div>
            </div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <Image className="w-4 h-4 text-purple-400" aria-hidden="true" />
                Galeri
              </h3>
              <p className="text-zinc-400 text-xs leading-relaxed">
                Oluşturulan tüm grafikler otomatik kaydedilir. Galeri
                sekmesinden geçmiş grafikleri görüntüleyebilir, indirebilir veya
                silebilirsiniz.
              </p>
            </div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3">
              <h3 className="text-white font-semibold flex items-center gap-2">
                💡 İpucu
              </h3>
              <p className="text-zinc-400 text-xs leading-relaxed">
                Agent&apos;lara &quot;bana bir bar grafik oluştur&quot; diyerek
                sohbet üzerinden de grafik ürettirebilirsiniz. Agent
                generate_chart tool&apos;unu kullanarak otomatik grafik
                oluşturur.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
