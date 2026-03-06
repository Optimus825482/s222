"use client";

/* Mobile bottom navigation — SVG icons, 44px touch targets */
interface Props {
  activeTab: "chat" | "monitor";
  onTabChange: (tab: "chat" | "monitor") => void;
  isProcessing: boolean;
  liveEventCount: number;
}

const ChatIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

const MonitorIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <circle cx="12" cy="8" r="4" />
    <path d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
  </svg>
);

const TABS = [
  { id: "chat" as const, label: "Sohbet", Icon: ChatIcon },
  { id: "monitor" as const, label: "Akış", Icon: MonitorIcon },
];

export function MobileNav({
  activeTab,
  onTabChange,
  isProcessing,
  liveEventCount,
}: Props) {
  return (
    <nav
      className="lg:hidden flex border-t border-border bg-surface-raised safe-bottom"
      aria-label="Ana navigasyon"
    >
      {TABS.map(({ id, label, Icon }) => {
        const isActive = activeTab === id;
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            aria-current={isActive ? "page" : undefined}
            aria-label={label}
            className={`
              flex-1 flex flex-col items-center justify-center gap-1
              min-h-[56px] py-2 text-xs font-medium transition-colors cursor-pointer
              ${isActive ? "text-blue-400" : "text-slate-500 hover:text-slate-300"}
            `}
          >
            <span className="relative">
              <Icon />
              {id === "monitor" && isProcessing && liveEventCount > 0 && (
                <span
                  className="absolute -top-1 -right-2 w-2 h-2 bg-blue-500 rounded-full animate-pulse"
                  aria-label="Aktif"
                />
              )}
            </span>
            <span>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
