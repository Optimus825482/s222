"use client";
import { useState } from "react";
import { type BenchTab, BENCH_TABS } from "./shared";
import { LeaderboardTab } from "./leaderboard-tab";
import { RunTab } from "./run-tab";
import { ResultsTab } from "./results-tab";
import { TrendTab } from "./trend-tab";
import { CompareTab } from "./compare-tab";

export function BenchmarkPanel() {
  const [tab, setTab] = useState<BenchTab>("leaderboard");

  return (
    <div className="h-full flex flex-col bg-slate-900/50">
      <div className="flex border-b border-slate-700/50 bg-slate-800/30 px-1">
        {BENCH_TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-xs transition-colors whitespace-nowrap ${
              tab === t.key
                ? "text-cyan-400 border-b-2 border-cyan-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {tab === "leaderboard" && <LeaderboardTab />}
        {tab === "run" && <RunTab />}
        {tab === "results" && <ResultsTab />}
        {tab === "trend" && <TrendTab />}
        {tab === "compare" && <CompareTab />}
      </div>
    </div>
  );
}
