"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

/**
 * Ana giriş: Giriş yapmış kullanıcıyı XP masaüstüne (/desktop), değilse /login'e yönlendirir.
 * Cockpit layout kaldırıldı — tek arayüz XP teması (desktop).
 */
export default function Home() {
  const router = useRouter();
  const { user } = useAuth();

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    router.replace("/desktop");
  }, [router, user]);

  return (
    <div
      className="flex h-dvh items-center justify-center bg-background"
      aria-busy="true"
    >
      <p className="text-sm text-slate-500">
        {user ? "Yönlendiriliyor…" : "Giriş sayfasına yönlendiriliyor…"}
      </p>
    </div>
  );
}
