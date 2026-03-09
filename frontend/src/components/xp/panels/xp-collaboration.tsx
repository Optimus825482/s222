"use client";

import { useState } from "react";
import { SharedWorkspacePanel } from "@/components/shared-workspace-panel";
import { ContextBoardPanel } from "@/components/context-board-panel";
import { CollaborativeEditorPanel } from "@/components/collaborative-editor-panel";
import { WorktreePanel } from "@/components/worktree-panel";

type TabId = "workspace" | "context" | "editor" | "worktree";

const TABS: { id: TabId; label: string }[] = [
  { id: "workspace", label: "Paylaşımlı Alan" },
  { id: "context", label: "Bağlam Panosu" },
  { id: "editor", label: "Düzenleyici" },
  { id: "worktree", label: "Worktree" },
];

export function XpCollaborationPanel() {
  const [tab, setTab] = useState<TabId>("workspace");

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* XP-style Tab Bar */}
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

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {tab === "workspace" && <SharedWorkspacePanel />}
        {tab === "context" && (
          <div className="h-full overflow-auto p-4">
            <ContextBoardPanel />
          </div>
        )}
        {tab === "editor" && <CollaborativeEditorPanel />}
        {tab === "worktree" && <WorktreePanel />}
      </div>
    </div>
  );
}

export default XpCollaborationPanel;