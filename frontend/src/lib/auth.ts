"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export interface AuthUser {
  user_id: string;
  full_name: string;
  token: string;
}

interface AuthStore {
  user: AuthUser | null;
  hasHydrated: boolean;
  markHydrated: () => void;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuth = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      hasHydrated: false,

      markHydrated: () => {
        set({ hasHydrated: true });
      },

      login: async (username: string, password: string) => {
        const res = await fetch(`${BASE}/api/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        if (!res.ok) {
          const err = await res
            .json()
            .catch(() => ({ detail: "Giriş başarısız" }));
          throw new Error(err.detail || "Giriş başarısız");
        }
        const data = await res.json();
        sessionStorage.removeItem("auth:validated-token");
        set({
          user: {
            user_id: data.user_id,
            full_name: data.full_name,
            token: data.token,
          },
        });
      },

      logout: async () => {
        const token = get().user?.token;
        if (token) {
          await fetch(`${BASE}/api/auth/logout`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
          }).catch(() => {});
        }
        sessionStorage.removeItem("auth:validated-token");
        set({ user: null });
      },
    }),
    {
      name: "ops-center-auth",
      partialize: (state) => ({ user: state.user }),
      onRehydrateStorage: () => (state) => {
        state?.markHydrated();
      },
    },
  ),
);
