"use client";

import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const BrainIcon = () => (
  <svg
    width="28"
    height="28"
    viewBox="0 0 24 24"
    fill="none"
    stroke="white"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.46 2.5 2.5 0 0 1-1.07-4.73A3 3 0 0 1 3.5 11a3 3 0 0 1 2.5-2.96V7.5A2.5 2.5 0 0 1 9.5 2Z" />
    <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.46 2.5 2.5 0 0 0 1.07-4.73A3 3 0 0 0 20.5 11a3 3 0 0 0-2.5-2.96V7.5A2.5 2.5 0 0 0 14.5 2Z" />
  </svg>
);

const CloseIcon = () => (
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
    <path d="M18 6L6 18M6 6l12 12" />
  </svg>
);

export default function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Already installed as standalone
    if (window.matchMedia("(display-mode: standalone)").matches) return;
    if (
      (window.navigator as Navigator & { standalone?: boolean }).standalone ===
      true
    )
      return;

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setShow(true);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") setShow(false);
    setDeferredPrompt(null);
  };

  if (!show) return null;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 p-4 md:hidden"
      role="dialog"
      aria-label="Uygulamayı yükle"
    >
      <div className="rounded-2xl border border-white/10 bg-[#0f1629]/95 p-4 shadow-2xl backdrop-blur-md">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-pink-500 to-violet-600">
            <BrainIcon />
          </div>

          {/* Text */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white">Uygulamayı Yükle</p>
            <p className="mt-0.5 text-xs text-white/50">
              Ana ekrana ekle, daha hızlı aç
            </p>
          </div>

          {/* Dismiss */}
          <button
            onClick={() => setShow(false)}
            className="shrink-0 text-white/30 hover:text-white/60 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center cursor-pointer"
            aria-label="Kapat"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Install button */}
        <button
          onClick={handleInstall}
          className="mt-3 w-full rounded-xl bg-gradient-to-r from-pink-500 to-violet-600 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 active:opacity-75 min-h-[44px] cursor-pointer"
        >
          Uygulama Olarak Yükle
        </button>
      </div>
    </div>
  );
}
