"use client";

import { LogOut, Menu } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";

interface Props {
  onMenuToggle: () => void;
}

export function CockpitHeader({ onMenuToggle }: Props) {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <header className="flex items-center gap-2 px-3 md:px-6 py-3 border-b border-border bg-surface-raised safe-top">
      <button
        onClick={onMenuToggle}
        className="lg:hidden p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-surface-overlay transition-colors"
        aria-label="Menüyü aç"
      >
        <Menu className="w-5 h-5 text-slate-400" />
      </button>
      <span className="text-xl md:text-2xl" aria-hidden="true">
        🧠
      </span>
      <span className="text-base md:text-lg font-bold text-slate-200 truncate">
        Ops Center
      </span>
      <span className="hidden sm:inline text-xs text-slate-500 ml-2 truncate">
        Qwen3 80B • 4 Agents • 7 Pipelines
      </span>

      {/* Spacer */}
      <div className="flex-1" />

      {/* User info + logout */}
      {user && (
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline text-xs text-slate-400 truncate max-w-[120px]">
            {user.full_name}
          </span>
          <button
            onClick={handleLogout}
            className="p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg hover:bg-surface-overlay text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="Çıkış yap"
            title="Çıkış yap"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      )}
    </header>
  );
}
