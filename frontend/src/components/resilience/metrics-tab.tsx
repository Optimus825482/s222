"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { Chart } from "react-google-charts";
import { card } from "./shared";
import { REFRESH_MS } from "./types";

/* ── Prometheus text → structured data ─────────────────────────── */
interface MetricEntry {
  agent: string;
  value: number;
}
interface MetricGroup {
  name: string;
  help: string;
  type: string;
  entries: MetricEntry[];
}

function parsePrometheus(raw: string): MetricGroup[] {
  const groups: MetricGroup[] = [];
  let current: MetricGroup | null = null;

  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    if (trimmed.startsWith("# HELP ")) {
      const rest = trimmed.slice(7);
      const idx = rest.indexOf(" ");
      current = {
        name: idx > 0 ? rest.slice(0, idx) : rest,
        help: idx > 0 ? rest.slice(idx + 1) : "",
        type: "gauge",
        entries: [],
      };
      groups.push(current);
    } else if (trimmed.startsWith("# TYPE ")) {
      if (current) {
        const parts = trimmed.slice(7).split(" ");
        current.type = parts[1] || "gauge";
      }
    } else if (current && !trimmed.startsWith("#")) {
      // agent_response_time_ms{agent="reasoner"} 8472.26
      const m = trimmed.match(/\{agent="([^"]+)"\}\s+([\d.]+)/);
      if (m) {
        current.entries.push({ agent: m[1], value: parseFloat(m[2]) });
      }
    }
  }
  return groups;
}

/* ── Agent color map ───────────────────────────────────────────── */
const AGENT_COLORS: Record<string, string> = {
  reasoner: "#6366f1",
  researcher: "#06b6d4",
  speed: "#f59e0b",
  critic: "#ef4444",
  thinker: "#8b5cf6",
  orchestrator: "#10b981",
  synthesizer: "#ec4899",
};

function agentColor(name: string): string {
  return AGENT_COLORS[name] || "#64748b";
}

const AGENT_LABELS: Record<string, string> = {
  reasoner: "🧠 Reasoner",
  researcher: "🔍 Researcher",
  speed: "⚡ Speed",
  critic: "🎯 Critic",
  thinker: "💭 Thinker",
  orchestrator: "🎼 Orchestrator",
  synthesizer: "🔬 Synthesizer",
};

function agentLabel(name: string): string {
  return AGENT_LABELS[name] || name;
}

/* ── Gauge Card ────────────────────────────────────────────────── */
function GaugeCard({
  label,
  value,
  max,
  unit,
  color,
}: {
  label: string;
  value: number;
  max: number;
  unit: string;
  color: string;
}) {
  return (
    <div
      style={{
        ...card,
        textAlign: "center",
        padding: "8px 6px",
        minWidth: 110,
      }}
    >
      <Chart
        chartType="Gauge"
        width="100%"
        height="100px"
        data={[
          ["Label", "Value"],
          ["", value],
        ]}
        options={{
          redFrom: max * 0.85,
          redTo: max,
          yellowFrom: max * 0.6,
          yellowTo: max * 0.85,
          greenFrom: 0,
          greenTo: max * 0.6,
          max,
          minorTicks: 5,
        }}
      />
      <div style={{ fontSize: 10, fontWeight: 600, color, marginTop: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: 9, color: "#888" }}>
        {value.toLocaleString("tr-TR", { maximumFractionDigits: 1 })}
        {unit}
      </div>
    </div>
  );
}

/* ── Horizontal Bar Chart for a metric group ───────────────────── */
function MetricBarChart({
  title,
  help,
  entries,
  unit,
  formatValue,
}: {
  title: string;
  help: string;
  entries: MetricEntry[];
  unit: string;
  formatValue?: (v: number) => string;
}) {
  const sorted = [...entries].sort((a, b) => b.value - a.value);
  const maxVal = Math.max(...sorted.map((e) => e.value), 1);
  const fmt =
    formatValue ||
    ((v: number) => v.toLocaleString("tr-TR", { maximumFractionDigits: 1 }));

  return (
    <div style={{ ...card, padding: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#1e293b" }}>
            {title}
          </div>
          <div style={{ fontSize: 9, color: "#94a3b8" }}>{help}</div>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {sorted.map((e) => {
          const pct = (e.value / maxVal) * 100;
          const c = agentColor(e.agent);
          return (
            <div
              key={e.agent}
              style={{ display: "flex", alignItems: "center", gap: 8 }}
            >
              <div
                style={{
                  width: 90,
                  fontSize: 10,
                  fontWeight: 600,
                  color: c,
                  textAlign: "right",
                  flexShrink: 0,
                }}
              >
                {agentLabel(e.agent)}
              </div>
              <div
                style={{
                  flex: 1,
                  background: "#f1f5f9",
                  borderRadius: 4,
                  height: 18,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${Math.max(pct, 2)}%`,
                    height: "100%",
                    background: `linear-gradient(90deg, ${c}88, ${c})`,
                    borderRadius: 4,
                    transition: "width 0.6s ease",
                  }}
                />
              </div>
              <div
                style={{
                  width: 70,
                  fontSize: 10,
                  fontWeight: 600,
                  color: "#334155",
                  textAlign: "right",
                  flexShrink: 0,
                }}
              >
                {fmt(e.value)}
                {unit}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Success Rate Donut ────────────────────────────────────────── */
function SuccessDonut({ entries }: { entries: MetricEntry[] }) {
  const avg =
    entries.length > 0
      ? entries.reduce((s, e) => s + e.value, 0) / entries.length
      : 0;

  const data = [
    ["Agent", "Success Rate"],
    ...entries.map((e) => [agentLabel(e.agent), e.value]),
  ];

  return (
    <div style={{ ...card, padding: 12 }}>
      <div
        style={{
          fontSize: 12,
          fontWeight: 700,
          color: "#1e293b",
          marginBottom: 4,
        }}
      >
        Başarı Oranları
      </div>
      <div style={{ fontSize: 9, color: "#94a3b8", marginBottom: 8 }}>
        Agent bazlı başarı yüzdeleri
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div style={{ flex: "0 0 auto" }}>
          <Chart
            chartType="PieChart"
            width="160px"
            height="160px"
            data={data}
            options={{
              pieHole: 0.55,
              pieSliceText: "none",
              legend: "none",
              chartArea: { width: "90%", height: "90%" },
              colors: entries.map((e) => agentColor(e.agent)),
              backgroundColor: "transparent",
              tooltip: { textStyle: { fontSize: 10 } },
            }}
          />
        </div>
        <div style={{ flex: 1, minWidth: 120 }}>
          <div
            style={{
              fontSize: 28,
              fontWeight: 800,
              color: avg >= 90 ? "#22c55e" : avg >= 70 ? "#f59e0b" : "#ef4444",
            }}
          >
            %{avg.toFixed(1)}
          </div>
          <div style={{ fontSize: 9, color: "#94a3b8", marginBottom: 8 }}>
            Ortalama Başarı
          </div>
          {entries.map((e) => (
            <div
              key={e.agent}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginBottom: 3,
              }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: agentColor(e.agent),
                  display: "inline-block",
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: 10, color: "#475569", flex: 1 }}>
                {agentLabel(e.agent)}
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color:
                    e.value >= 90
                      ? "#22c55e"
                      : e.value >= 70
                        ? "#f59e0b"
                        : "#ef4444",
                }}
              >
                %{e.value.toFixed(0)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Task Count Column Chart ───────────────────────────────────── */
function TaskColumnChart({ entries }: { entries: MetricEntry[] }) {
  const sorted = [...entries].sort((a, b) => b.value - a.value);
  const total = sorted.reduce((s, e) => s + e.value, 0);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data: any[][] = [
    ["Agent", "Görev", { role: "style" }, { role: "annotation" }],
    ...sorted.map((e) => [
      agentLabel(e.agent),
      e.value,
      agentColor(e.agent),
      `${e.value}`,
    ]),
  ];

  return (
    <div style={{ ...card, padding: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 4,
        }}
      >
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#1e293b" }}>
            Toplam Görevler
          </div>
          <div style={{ fontSize: 9, color: "#94a3b8" }}>
            Agent bazlı işlenen görev sayısı
          </div>
        </div>
        <div style={{ fontSize: 20, fontWeight: 800, color: "#3b82f6" }}>
          {total}
        </div>
      </div>
      <Chart
        chartType="ColumnChart"
        width="100%"
        height="180px"
        data={data}
        options={{
          legend: "none",
          chartArea: { width: "85%", height: "70%" },
          backgroundColor: "transparent",
          hAxis: { textStyle: { fontSize: 9, color: "#64748b" } },
          vAxis: {
            textStyle: { fontSize: 9, color: "#94a3b8" },
            gridlines: { color: "#f1f5f9" },
          },
          annotations: {
            textStyle: { fontSize: 10, bold: true, color: "#334155" },
          },
          bar: { groupWidth: "60%" },
        }}
      />
    </div>
  );
}

/* ── Main MetricsTab ───────────────────────────────────────────── */
export function MetricsTab() {
  const [raw, setRaw] = useState("");
  const [err, setErr] = useState("");
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const load = useCallback(() => {
    setErr("");
    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL ||
      "https://ykok0ckoocc880w0cwo0w0w0.77.42.68.4.sslip.io";
    fetch(`${apiUrl}/api/metrics`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((t) => {
        setRaw(t);
        setLastUpdate(new Date());
      })
      .catch((e) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, [load]);

  const groups = useMemo(() => parsePrometheus(raw), [raw]);

  // Find specific metric groups
  const responseTime = groups.find((g) => g.name === "agent_response_time_ms");
  const successRate = groups.find(
    (g) => g.name === "agent_success_rate_percent",
  );
  const tasksTotal = groups.find((g) => g.name === "agent_tasks_total");
  const otherGroups = groups.filter(
    (g) =>
      g.name !== "agent_response_time_ms" &&
      g.name !== "agent_success_rate_percent" &&
      g.name !== "agent_tasks_total",
  );

  if (err) {
    return (
      <div style={{ padding: 20, textAlign: "center" }}>
        <div style={{ color: "#ef4444", fontSize: 12, marginBottom: 8 }}>
          ⚠️ {err}
        </div>
        <button
          onClick={load}
          style={{ ...card, cursor: "pointer", padding: "4px 12px" }}
        >
          Tekrar Dene
        </button>
      </div>
    );
  }

  if (!raw) {
    return (
      <div
        style={{
          padding: 20,
          textAlign: "center",
          color: "#888",
          fontSize: 12,
        }}
      >
        Yükleniyor...
      </div>
    );
  }

  return (
    <div style={{ padding: 12 }}>
      {/* Header */}
      <div
        style={{
          ...card,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <span style={{ fontWeight: 700, fontSize: 13 }}>
            📊 Agent Metrikleri
          </span>
          {lastUpdate && (
            <span style={{ fontSize: 9, color: "#94a3b8", marginLeft: 8 }}>
              Son güncelleme: {lastUpdate.toLocaleTimeString("tr-TR")}
            </span>
          )}
        </div>
        <button
          onClick={load}
          style={{
            ...card,
            cursor: "pointer",
            padding: "4px 10px",
            fontSize: 10,
            marginBottom: 0,
          }}
        >
          🔄 Yenile
        </button>
      </div>

      {/* Response Time Gauges */}
      {responseTime && responseTime.entries.length > 0 && (
        <>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: "#475569",
              margin: "8px 0 4px 2px",
            }}
          >
            ⏱️ Yanıt Süreleri (ms)
          </div>
          <div
            style={{
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
              marginBottom: 8,
            }}
          >
            {responseTime.entries.map((e) => (
              <GaugeCard
                key={e.agent}
                label={agentLabel(e.agent)}
                value={Math.round(e.value)}
                max={Math.max(
                  ...responseTime.entries.map((x) => x.value),
                  30000,
                )}
                unit="ms"
                color={agentColor(e.agent)}
              />
            ))}
          </div>
          {/* Also show as bar chart for comparison */}
          <MetricBarChart
            title="Yanıt Süresi Karşılaştırma"
            help="Agent bazlı ortalama yanıt süresi (ms)"
            entries={responseTime.entries}
            unit="ms"
            formatValue={(v) =>
              v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${v.toFixed(0)}`
            }
          />
        </>
      )}

      {/* Success Rate + Tasks side by side */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {successRate && successRate.entries.length > 0 && (
          <div style={{ flex: "1 1 280px", minWidth: 250 }}>
            <SuccessDonut entries={successRate.entries} />
          </div>
        )}
        {tasksTotal && tasksTotal.entries.length > 0 && (
          <div style={{ flex: "1 1 280px", minWidth: 250 }}>
            <TaskColumnChart entries={tasksTotal.entries} />
          </div>
        )}
      </div>

      {/* Other metrics as bar charts */}
      {otherGroups.map((g) =>
        g.entries.length > 0 ? (
          <MetricBarChart
            key={g.name}
            title={g.name.replace(/_/g, " ")}
            help={g.help}
            entries={g.entries}
            unit=""
          />
        ) : null,
      )}
    </div>
  );
}
