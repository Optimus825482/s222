"use client";

/* Mobile bottom navigation */
interface Props {
  activeTab: "chat" | "activity" | "agents";
  onTabChange: (tab: "chat" | "activity" | "agents") => void;
  isProcessing: boolean;
  liveEventCount: number;
}

export function MobileNav({
  activeTab,
  onTabChange,
  isProcessing,
  liveEventCount,
}: Props) {
  const tabs = [
    { id: "chat" as const, label: "Sohbet", icon: "💬" },
    { id: "activity" as const, label: "Akış", icon: "📡" },
    { id: "agents" as const, label: "Agentlar", icon: "🤖" },
  ];

  return (
    <nav
      className="lg:hidden flex border-t border-border bg-surface-raised safe-bottom"
      role="tablist"
      aria-label="Ana navigasyon"
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            role="tab"
            aria-selected={isActive}
            aria-label={tab.label}
            className={`
              flex-1 flex flex-col items-center justify-center gap-0.5
              min-h-[56px] py-2 text-xs font-medium transition-colors
              ${isActive ? "text-blue-400" : "text-slate-500"}
            `}
          >
            <span className="text-lg relative">
              {tab.icon}
              {tab.id === "activity" && isProcessing && liveEventCount > 0 && (
                <span className="absolute -top-1 -right-2 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              )}
            </span>
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
