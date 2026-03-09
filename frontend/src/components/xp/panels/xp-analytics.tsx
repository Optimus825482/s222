"use client";

import { useState } from "react";
import { BenchmarkPanel } from "@/components/benchmark";
import PerformanceDashboard from "@/components/performance-dashboard";
import CostTrackerPanel from "@/components/cost-tracker-panel";
import ErrorPatternsPanel from "@/components/error-patterns-panel";
import AutoOptimizerPanel from "@/components/auto-optimizer-panel";

// ── Tab type ─────────────────────────────────────────────────────
type AnalyticsTab = "benchmark" | "performance" | "cost" | "errors" | "optimizer";

const TABS: { id: AnalyticsTab; label: string }[] = [
  { id: "benchmark", label: "Benchmark" },
  { id: "performance", label: "Performans" },
  { id: "cost", label: "Maliyet" },
  { id: "errors", label: "Hatalar" },
  { id: "optimizer", label: "Optimizasyon" },
];

// ── Main Component ───────────────────────────────────────────────
export function XpAnalyticsPanel() {
  const [tab, setTab] = useState<AnalyticsTab>("benchmark");

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ── XP-style Tab Header ─────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #d6d2c2",
          background: "#ECE9D8",
          padding: "0 4px",
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "6px 14px",
              fontSize: 11,
              fontFamily: "Tahoma, sans-serif",
              fontWeight: tab === t.id ? 600 : 400,
              background: tab === t.id ? "#fff" : "transparent",
              border: tab === t.id ? "1px solid #d6d2c2" : "1px solid transparent",
              borderBottom: tab === t.id ? "1px solid #fff" : "1px solid #d6d2c2",
              borderRadius: "3px 3px 0 0",
              marginBottom: -1,
              cursor: "pointer",
              color: tab === t.id ? "#000" : "#555",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab Content ─────────────────────────────────────────── */}
      <div className="flex-1 overflow-auto p-3">
        {tab === "benchmark" && <BenchmarkPanel />}
        {tab === "performance" && <PerformanceDashboard />}
        {tab === "cost" && <CostTrackerPanel />}
        {tab === "errors" && <ErrorPatternsPanel />}
        {tab === "optimizer" && <AutoOptimizerPanel />}
      </div>
    </div>
  );
}

// Named export alias for xp-apps.tsx compatibility
export { XpAnalyticsPanel as XpAnalytics };
export default XpAnalyticsPanel;