"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Giriş başarısız");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex items-center justify-center bg-[#0a0a0f] px-4">
      <div className="w-full max-w-sm">
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3" aria-hidden="true">
            🧠
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Ops Center</h1>
          <p className="text-sm text-slate-500 mt-1">
            Multi-Agent Intelligence Platform
          </p>
        </div>

        {/* Login Card */}
        <form
          onSubmit={handleSubmit}
          className="bg-[#13131a] border border-[#1e1e2e] rounded-2xl p-6 shadow-2xl"
        >
          <h2 className="text-base font-semibold text-slate-300 mb-5">
            Giriş Yap
          </h2>

          <div className="space-y-4">
            <div>
              <label
                htmlFor="username"
                className="block text-xs text-slate-400 mb-1.5"
              >
                Kullanıcı Adı
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder=""
                autoComplete="username"
                required
                className="w-full bg-[#0a0a0f] border border-[#2a2a3e] rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 transition-colors"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs text-slate-400 mb-1.5"
              >
                Şifre
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••"
                autoComplete="current-password"
                required
                className="w-full bg-[#0a0a0f] border border-[#2a2a3e] rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30 transition-colors"
              />
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="mt-4 px-3 py-2 bg-red-950/50 border border-red-900/50 rounded-lg text-red-300 text-xs"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-5 w-full min-h-[44px] bg-violet-600 hover:bg-violet-500 disabled:bg-violet-800 disabled:cursor-not-allowed text-white font-medium text-sm rounded-lg py-2.5 transition-colors focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            aria-busy={loading}
          >
            {loading ? "Giriş yapılıyor..." : "Giriş Yap"}
          </button>
        </form>

        {/* Users hint */}
        <div className="mt-4 text-center">
          <p className="text-xs text-slate-600">Erkan Erdem · Yiğit Avcı</p>
        </div>

        {/* Copyright */}
        <div className="mt-3 text-center">
          <p className="text-xs text-slate-700">
            © {new Date().getFullYear()} Code by Erkan Erdem &amp; Yiğit Avcı
          </p>
        </div>
      </div>
    </div>
  );
}
