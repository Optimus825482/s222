"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { XpDesktop } from "@/components/xp-desktop";
import "./xp-theme.css";

export default function DesktopPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [ready, setReady] = useState(false);
  const lastValidatedTokenRef = useRef<string | null>(null);

  useEffect(() => {
    if (!user) {
      // Wait a tick for zustand persist hydration before redirecting
      const timeout = setTimeout(() => {
        const stored = localStorage.getItem("ops-center-auth");
        if (!stored) {
          router.replace("/login");
        }
      }, 150);
      return () => clearTimeout(timeout);
    }

    const token = user.token?.trim();
    if (!token) {
      router.replace("/login");
      return;
    }

    // Skip re-validation if already validated this session
    if (lastValidatedTokenRef.current === token) {
      setReady(true);
      return;
    }

    const sessionKey = "auth:validated-token";
    if (
      typeof window !== "undefined" &&
      sessionStorage.getItem(sessionKey) === token
    ) {
      lastValidatedTokenRef.current = token;
      setReady(true);
      return;
    }

    // Validate token with retry
    let cancelled = false;
    const validate = async () => {
      try {
        await api.me();
      } catch {
        // Retry once after a short delay
        await new Promise((r) => setTimeout(r, 350));
        await api.me();
      }
      if (cancelled) return;
      lastValidatedTokenRef.current = token;
      if (typeof window !== "undefined") {
        sessionStorage.setItem(sessionKey, token);
      }
      setReady(true);
    };

    validate().catch(() => {
      if (!cancelled) router.replace("/login");
    });

    return () => {
      cancelled = true;
    };
  }, [router, user]);

  if (!user || !ready) {
    return (
      <div className="flex h-dvh items-center justify-center bg-[#245edb]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 border-4 border-white/30 border-t-white rounded-full animate-spin" />
          <p
            className="text-white text-sm font-medium"
            style={{ fontFamily: "Tahoma, sans-serif" }}
          >
            Windows yükleniyor...
          </p>
        </div>
      </div>
    );
  }

  return <XpDesktop />;
}
