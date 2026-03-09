"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { XpSkillsList } from "./xp-skills-list";

// Dynamic imports for heavy panels
const DomainMarketplacePanel = dynamic(
  () =>
    import("@/components/domain-marketplace-panel").then((m) => ({
      default: m.DomainMarketplacePanel,
    })),
  { ssr: false },
);

const XpMarketplacePanel = dynamic(
  () =>
    import("./xp-marketplace-panel").then((m) => ({
      default: m.XpMarketplacePanel,
    })),
  { ssr: false },
);

// ── Styles (matching XpWorkflowsWrapper pattern) ──
const TAB_BUTTON_STYLE = (isActive: boolean): React.CSSProperties => ({
  padding: "6px 14px",
  fontSize: 11,
  fontFamily: "Tahoma, sans-serif",
  fontWeight: isActive ? 600 : 400,
  background: isActive ? "#fff" : "transparent",
  border: isActive ? "1px solid #d6d2c2" : "1px solid transparent",
  borderBottom: isActive ? "1px solid #fff" : "1px solid #d6d2c2",
  borderRadius: "3px 3px 0 0",
  marginBottom: -1,
  cursor: "pointer",
  color: isActive ? "#000" : "#555",
});

// ── Main Unified Marketplace Panel ──
export function XpUnifiedMarketplace() {
  const [tab, setTab] = useState<"domain" | "marketplace" | "skills">("domain");

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tab bar - matching XpWorkflowsWrapper pattern exactly */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #d6d2c2",
          background: "#ECE9D8",
          padding: "0 4px",
        }}
      >
        {[
          { id: "domain" as const, label: "Domain Uzmanlığı" },
          { id: "marketplace" as const, label: "Skill Mağazası" },
          { id: "skills" as const, label: "Yeteneklerim" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={TAB_BUTTON_STYLE(tab === t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-hidden">
        {tab === "domain" ? (
          <DomainMarketplacePanel />
        ) : tab === "marketplace" ? (
          <XpMarketplacePanel />
        ) : (
          <XpSkillsList />
        )}
      </div>
    </div>
  );
}

export default XpUnifiedMarketplace;