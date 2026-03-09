"use client";

import { useState } from "react";
import { xpBtn } from "./shared";
import { HealthTab } from "./health-tab";
import { MetricsTab } from "./metrics-tab";
import { ThresholdsTab } from "./thresholds-tab";
import { ChaosTab } from "./chaos-tab";
import { ModerationTab } from "./moderation-tab";
import { FederatedTab } from "./federated-tab";

type Tab =
  | "health"
  | "metrics"
  | "thresholds"
  | "chaos"
  | "moderation"
  | "federated";

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "health", label: "Sistem Sağlığı", icon: "💚" },
  { key: "metrics", label: "Metrikler", icon: "📈" },
  { key: "thresholds", label: "Eşikler", icon: "📊" },
  { key: "chaos", label: "Chaos", icon: "🔥" },
  { key: "moderation", label: "Moderasyon", icon: "🛡️" },
  { key: "federated", label: "Federated", icon: "🌐" },
];

export function ResiliencePanel() {
  const [tab, setTab] = useState<Tab>("health");

  return (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{ fontFamily: "Tahoma, sans-serif" }}
    >
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #d6d2c2",
          background: "#ECE9D8",
          padding: "0 4px",
          flexWrap: "wrap",
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={xpBtn(tab === t.key)}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto" style={{ background: "#fff" }}>
        {tab === "health" && <HealthTab />}
        {tab === "metrics" && <MetricsTab />}
        {tab === "thresholds" && <ThresholdsTab />}
        {tab === "chaos" && <ChaosTab />}
        {tab === "moderation" && <ModerationTab />}
        {tab === "federated" && <FederatedTab />}
      </div>
    </div>
  );
}

export default ResiliencePanel;
