"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { fetcher } from "@/lib/api";

/* ── Types ── */
interface ToolStat {
  tool_name: string;
  call_count: number;
  success_count: number;
  total_latency_ms: number;
  total_tokens: number;
}

interface UsageData {
  server_stats: {
    server_id: string;
    server_name: string;
    call_count: number;
    success_count: number;
    total_latency_ms: number;
    total_tokens: number;
  }[];
  all_tools: ToolStat[];
  model_breakdown: Record<string, Record<string, number>>;
  timeline: Record<string, Record<string, number>>;
}

/* ── Styles ── */
const crd = "bg-[#ECE9D8] rounded border border-[#ACA899] p-2";

/* ── Mini line chart (pure SVG) ── */
function MiniLineChart({
  data,
  width = 520,
  height = 160,
}: {
  data: { day: string; value: number }[];
  width?: number;
  height?: number;
}) {
  if (data.length < 2) {
    return (
      <div
        className="flex items-center justify-center text-[10px] text-[#808080]"
        style={{ width, height }}
      >
        Yeterli veri yok
      </div>
    );
  }

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const padX = 40;
  const padY = 20;
  const chartW = width - padX * 2;
  const chartH = height - padY * 2;

  const points = data.map((d, i) => {
    const x = padX + (i / (data.length - 1)) * chartW;
    const y = padY + chartH - (d.value / maxVal) * chartH;
    return { x, y, ...d };
  });

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`)
    .join(" ");
  const areaPath = `${linePath} L${points[points.length - 1].x},${padY + chartH} L${points[0].x},${padY + chartH} Z`;

  // Y-axis labels
  const yTicks = [0, Math.round(maxVal / 2), maxVal];

  return (
    <svg width={width} height={height} className="block">
      {/* Grid lines */}
      {yTicks.map((t) => {
        const y = padY + chartH - (t / maxVal) * chartH;
        return (
          <g key={t}>
            <line
              x1={padX}
              y1={y}
              x2={width - padX}
              y2={y}
              stroke="#ACA899"
              strokeWidth={0.5}
              strokeDasharray="3,3"
            />
            <text
              x={padX - 4}
              y={y + 3}
              textAnchor="end"
              fontSize={9}
              fill="#808080"
            >
              {t}
            </text>
          </g>
        );
      })}
      {/* Area fill */}
      <path d={areaPath} fill="url(#mcpGrad)" opacity={0.3} />
      {/* Line */}
      <path
        d={linePath}
        fill="none"
        stroke="#0078D4"
        strokeWidth={2}
        strokeLinejoin="round"
      />
      {/* Dots */}
      {points.map((p, i) => (
        <g key={i}>
          <circle
            cx={p.x}
            cy={p.y}
            r={3}
            fill="#fff"
            stroke="#0078D4"
            strokeWidth={1.5}
          />
          <title>{`${p.day}: ${p.value} çağrı`}</title>
        </g>
      ))}
      {/* X-axis labels (show every few) */}
      {points
        .filter(
          (_, i) =>
            i % Math.max(1, Math.floor(points.length / 6)) === 0 ||
            i === points.length - 1,
        )
        .map((p) => (
          <text
            key={p.day}
            x={p.x}
            y={height - 2}
            textAnchor="middle"
            fontSize={8}
            fill="#808080"
          >
            {p.day.slice(5)}
          </text>
        ))}
      <defs>
        <linearGradient id="mcpGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0078D4" stopOpacity={0.4} />
          <stop offset="100%" stopColor="#0078D4" stopOpacity={0.05} />
        </linearGradient>
      </defs>
    </svg>
  );
}

/* ── Main Panel ── */
export function McpUsagePanel() {
  const [data, setData] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedTool, setSelectedTool] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const d = await fetcher<UsageData>("/api/mcp/usage-stats");
      setData(d);
    } catch (e: any) {
      setError(e?.message ?? "API hatası");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Aggregate timeline for chart
  const chartData = useMemo(() => {
    if (!data?.timeline) return [];
    const days = Object.keys(data.timeline).sort();
    if (selectedTool) {
      return days.map((d) => ({
        day: d,
        value: data.timeline[d]?.[selectedTool] ?? 0,
      }));
    }
    return days.map((d) => ({
      day: d,
      value: Object.values(data.timeline[d] || {}).reduce((a, b) => a + b, 0),
    }));
  }, [data, selectedTool]);

  if (loading) {
    return (
      <div className="p-3 space-y-2 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-[#D4D0C8] rounded" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 text-center">
        <p className="text-[11px] text-red-600 mb-2">{error}</p>
        <button
          onClick={load}
          className="px-3 py-1 text-[11px] bg-[#ECE9D8] border border-[#ACA899] rounded hover:bg-[#D4D0C8]"
        >
          Tekrar Dene
        </button>
      </div>
    );
  }

  if (!data) return null;

  const tools = data.all_tools;
  const modelBreakdown = selectedTool
    ? data.model_breakdown[selectedTool]
    : null;

  return (
    <div
      className="h-full flex flex-col gap-2 p-3 overflow-auto"
      style={{ fontFamily: "Tahoma, sans-serif" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span style={{ fontSize: 14 }}>📊</span>
          <span className="text-[12px] font-semibold text-[#000]">
            MCP Kullanım İstatistikleri
          </span>
        </div>
        <button
          onClick={load}
          className="px-2 py-1 text-[10px] bg-[#ECE9D8] border border-[#ACA899] rounded hover:bg-[#D4D0C8]"
        >
          ↻ Yenile
        </button>
      </div>

      {/* Tool list */}
      <div className={crd}>
        <div className="text-[10px] font-semibold text-[#000] mb-1.5">
          Araç Kullanımları
        </div>
        {tools.length === 0 ? (
          <div className="text-[10px] text-[#808080] py-4 text-center">
            Henüz kullanım verisi yok
          </div>
        ) : (
          <div className="space-y-0.5 max-h-[200px] overflow-auto">
            {tools.map((t) => {
              const isSelected = selectedTool === t.tool_name;
              const successRate =
                t.call_count > 0
                  ? Math.round((t.success_count / t.call_count) * 100)
                  : 0;
              return (
                <button
                  key={t.tool_name}
                  onClick={() =>
                    setSelectedTool(isSelected ? null : t.tool_name)
                  }
                  className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-left transition-colors ${
                    isSelected
                      ? "bg-[#316AC5] text-white"
                      : "hover:bg-[#D4D0C8]"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${successRate >= 90 ? "bg-green-500" : successRate >= 50 ? "bg-yellow-500" : "bg-red-500"}`}
                  />
                  <span className="text-[11px] flex-1 truncate">
                    {t.tool_name}
                  </span>
                  <span
                    className={`text-[11px] font-bold tabular-nums ${isSelected ? "text-white" : "text-[#000]"}`}
                  >
                    {t.call_count}
                  </span>
                  <span
                    className={`text-[9px] ${isSelected ? "text-blue-100" : "text-[#808080]"}`}
                  >
                    çağrı
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Model breakdown (when a tool is selected) */}
      {selectedTool && modelBreakdown && (
        <div className={crd}>
          <div className="text-[10px] font-semibold text-[#000] mb-1.5">
            "{selectedTool}" — Model/Agent Dağılımı
          </div>
          <div className="space-y-1">
            {Object.entries(modelBreakdown)
              .sort((a, b) => b[1] - a[1])
              .map(([role, cnt]) => {
                const total = Object.values(modelBreakdown).reduce(
                  (a, b) => a + b,
                  0,
                );
                const pct = total > 0 ? Math.round((cnt / total) * 100) : 0;
                return (
                  <div key={role} className="flex items-center gap-2">
                    <span className="text-[10px] w-24 truncate text-[#000]">
                      {role}
                    </span>
                    <div className="flex-1 h-3 bg-[#D4D0C8] rounded overflow-hidden">
                      <div
                        className="h-full rounded"
                        style={{
                          width: `${pct}%`,
                          background:
                            "linear-gradient(90deg, #0078D4, #00BCF2)",
                        }}
                      />
                    </div>
                    <span className="text-[10px] tabular-nums text-[#000] w-12 text-right">
                      {cnt} ({pct}%)
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Timeline chart */}
      <div className={crd}>
        <div className="text-[10px] font-semibold text-[#000] mb-1.5">
          Kullanım Grafiği (Son 30 Gün)
          {selectedTool && (
            <span className="font-normal text-[#808080]">
              {" "}
              — {selectedTool}
            </span>
          )}
        </div>
        <MiniLineChart data={chartData} width={520} height={160} />
      </div>
    </div>
  );
}

export default McpUsagePanel;
