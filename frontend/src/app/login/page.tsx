"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useXpSounds } from "@/lib/use-xp-sounds";

const USERS = [
  { name: "Erkan Erdem", avatar: "👨‍💻", username: "erkan" },
  { name: "Yiğit Avcı", avatar: "🧑‍💻", username: "yigit" },
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const { play } = useXpSounds();
  const [picked, setPicked] = useState<string | null>(null);
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const who = USERS.find((x) => x.username === picked);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!picked) return;
    setErr("");
    setBusy(true);
    try {
      await login(picked, pw);
      play("startup");
      router.push("/desktop");
    } catch (x: unknown) {
      play("error");
      setErr(x instanceof Error ? x.message : "Giriş başarısız");
    } finally {
      setBusy(false);
    }
  };

  const pick = (u: string) => {
    setPicked(u);
    setPw("");
    setErr("");
  };
  const back = () => {
    setPicked(null);
    setPw("");
    setErr("");
  };

  return (
    <div
      className="min-h-dvh flex flex-col overflow-hidden"
      style={{
        background:
          "linear-gradient(180deg,#0058e6 0%,#0052d6 30%,#3a7bd5 60%,#5b9ee0 80%,#7ab8eb 100%)",
        fontFamily: "Tahoma,Segoe UI,sans-serif",
      }}
    >
      <div
        className="h-7 sm:h-8 flex items-center justify-end px-3 sm:px-4 shrink-0"
        style={{ background: "linear-gradient(180deg,#0a3a8a,#0052d6)" }}
      >
        <span className="text-[9px] sm:text-[10px] text-blue-200/60">
          Multi-Agent Ops Center
        </span>
      </div>
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-6 sm:py-8 min-h-0">
        <div className="mb-5 sm:mb-8 text-center shrink-0">
          <div
            className="text-4xl sm:text-6xl mb-2 sm:mb-3"
            style={{ filter: "drop-shadow(0 2px 8px rgba(0,0,0,.3))" }}
          >
            🖥️
          </div>
          <h1
            className="text-xl sm:text-3xl font-bold text-white tracking-wide"
            style={{ textShadow: "0 2px 4px rgba(0,0,0,.3)" }}
          >
            Ops Center
          </h1>
          <p
            className="text-xs sm:text-sm text-blue-100/80 mt-1"
            style={{ textShadow: "0 1px 2px rgba(0,0,0,.2)" }}
          >
            Multi-Agent Intelligence Platform
          </p>
        </div>
        <div
          className="w-full max-w-[92vw] sm:max-w-lg rounded-2xl overflow-hidden shrink-0"
          style={{
            background:
              "linear-gradient(180deg,rgba(255,255,255,.15),rgba(255,255,255,.05))",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(255,255,255,.2)",
            boxShadow: "0 8px 32px rgba(0,0,0,.3)",
          }}
        >
          <div
            className="px-4 sm:px-5 py-2.5 sm:py-3"
            style={{
              background:
                "linear-gradient(180deg,rgba(255,255,255,.12),rgba(255,255,255,.04))",
              borderBottom: "1px solid rgba(255,255,255,.1)",
            }}
          >
            <span
              className="text-white text-xs sm:text-sm font-semibold"
              style={{ textShadow: "0 1px 2px rgba(0,0,0,.3)" }}
            >
              {picked ? "Şifrenizi girin" : "Bir kullanıcı seçin"}
            </span>
          </div>
          <div className="p-4 sm:p-6">
            {!picked ? (
              <div className="flex flex-col items-center gap-3 sm:gap-4">
                <p className="text-blue-100/70 text-[11px] sm:text-xs mb-1">
                  Başlamak için hesabınıza tıklayın
                </p>
                <div className="flex gap-4 sm:gap-6 justify-center">
                  {USERS.map((u) => (
                    <button
                      key={u.username}
                      onClick={() => pick(u.username)}
                      className="flex flex-col items-center gap-1.5 sm:gap-2 p-3 sm:p-4 rounded-xl transition-all active:scale-95 sm:hover:scale-105 focus:outline-none focus:ring-2 focus:ring-white/40"
                      style={{
                        background: "rgba(255,255,255,.05)",
                        border: "1px solid rgba(255,255,255,.1)",
                      }}
                    >
                      <div
                        className="w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center text-2xl sm:text-3xl"
                        style={{
                          background: "linear-gradient(135deg,#3a7bd5,#00a2e8)",
                          border: "3px solid rgba(255,255,255,.4)",
                          boxShadow: "0 4px 12px rgba(0,0,0,.3)",
                        }}
                      >
                        {u.avatar}
                      </div>
                      <span
                        className="text-white text-xs sm:text-sm font-medium whitespace-nowrap"
                        style={{ textShadow: "0 1px 2px rgba(0,0,0,.3)" }}
                      >
                        {u.name}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <form
                onSubmit={submit}
                className="flex flex-col items-center gap-3 sm:gap-4"
              >
                <button
                  type="button"
                  onClick={back}
                  className="self-start text-blue-200/70 hover:text-white text-xs flex items-center gap-1 transition-colors"
                >
                  ← Geri
                </button>
                <div className="flex flex-col items-center gap-1.5 sm:gap-2">
                  <div
                    className="w-16 h-16 sm:w-20 sm:h-20 rounded-full flex items-center justify-center text-3xl sm:text-4xl"
                    style={{
                      background: "linear-gradient(135deg,#3a7bd5,#00a2e8)",
                      border: "3px solid rgba(255,255,255,.5)",
                      boxShadow: "0 4px 16px rgba(0,0,0,.3)",
                    }}
                  >
                    {who?.avatar}
                  </div>
                  <span
                    className="text-white text-sm sm:text-base font-semibold"
                    style={{ textShadow: "0 1px 2px rgba(0,0,0,.3)" }}
                  >
                    {who?.name}
                  </span>
                </div>
                <div className="w-full max-w-[80vw] sm:max-w-xs">
                  <label
                    htmlFor="xp-pw"
                    className="block text-[11px] sm:text-xs text-blue-100/60 mb-1.5"
                  >
                    Şifre
                  </label>
                  <div className="flex gap-2">
                    <input
                      id="xp-pw"
                      type="password"
                      value={pw}
                      onChange={(e) => setPw(e.target.value)}
                      autoComplete="current-password"
                      autoFocus
                      required
                      className="flex-1 min-w-0 rounded-lg px-3 py-2.5 text-sm text-black placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-white/40"
                      style={{
                        background: "rgba(255,255,255,.9)",
                        border: "1px solid rgba(255,255,255,.5)",
                      }}
                    />
                    <button
                      type="submit"
                      disabled={busy}
                      className="px-4 py-2.5 rounded-lg text-sm font-medium text-white disabled:opacity-50 shrink-0"
                      style={{
                        background:
                          "linear-gradient(180deg,#3c9a3c,#2d8a2d 50%,#1e7a1e)",
                        border: "1px solid rgba(255,255,255,.2)",
                        boxShadow: "0 2px 4px rgba(0,0,0,.2)",
                        textShadow: "0 1px 1px rgba(0,0,0,.3)",
                      }}
                      aria-busy={busy}
                    >
                      {busy ? "..." : "→"}
                    </button>
                  </div>
                </div>
                {err && (
                  <div
                    role="alert"
                    className="w-full max-w-[80vw] sm:max-w-xs px-3 py-2 rounded-lg text-xs text-red-100"
                    style={{
                      background: "rgba(220,38,38,.3)",
                      border: "1px solid rgba(220,38,38,.4)",
                    }}
                  >
                    {err}
                  </div>
                )}
              </form>
            )}
          </div>
        </div>
      </div>
      <div
        className="h-8 sm:h-10 flex items-center justify-center px-4 sm:px-6 shrink-0"
        style={{
          background: "linear-gradient(180deg,#0a3a8a,#0052d6)",
          borderTop: "1px solid rgba(255,255,255,.1)",
        }}
      >
        <span className="text-[9px] sm:text-[10px] text-blue-200/50">
          © {new Date().getFullYear()} Code by Erkan Erdem & Yiğit Avcı
        </span>
      </div>
    </div>
  );
}
