"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

// ── Dynamic imports for sub-panels ──
const XpToolsPanel = dynamic(
  () =>
    import("./xp-tools-panel").then((m) => ({
      default: m.XpToolsPanel,
    })),
  { ssr: false },
);

const SkillCreatorPanel = dynamic(
  () =>
    import("@/components/skill-creator-panel").then((m) => ({
      default: m.SkillCreatorPanel,
    })),
  { ssr: false },
);

const AdaptiveToolSelectorPanel = dynamic(
  () =>
    import("@/components/adaptive-tool-selector-panel").then((m) => ({
      default: m.AdaptiveToolSelectorPanel,
    })),
  { ssr: false },
);

// ── Unified Tools Panel with 3 tabs ──
export function XpToolsUnified() {
  const [tab, setTab] = useState<"tools" | "creator" | "adaptive">("tools");

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #d6d2c2",
          background: "#ECE9D8",
          padding: "0 4px",
        }}
      >
        {[
          { id: "tools" as const, label: "Araçlar" },
          { id: "creator" as const, label: "Skill Oluşturucu" },
          { id: "adaptive" as const, label: "Adaptif Araçlar" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "6px 14px",
              fontSize: 11,
              fontFamily: "Tahoma, sans-serif",
              fontWeight: tab === t.id ? 600 : 400,
              background: tab === t.id ? "#fff" : "transparent",
              border:
                tab === t.id ? "1px solid #d6d2c2" : "1px solid transparent",
              borderBottom:
                tab === t.id ? "1px solid #fff" : "1px solid #d6d2c2",
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

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {tab === "tools" ? (
          <XpToolsPanel />
        ) : tab === "creator" ? (
          <SkillCreatorPanel />
        ) : (
          <AdaptiveToolSelectorPanel />
        )}
      </div>
    </div>
  );
}