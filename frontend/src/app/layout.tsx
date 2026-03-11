import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import PWAInstallPrompt from "@/components/pwa-install-prompt";
import { ToastProvider } from "@/components/toast";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: "#0a0e1a",
};

export const metadata: Metadata = {
  title: "Nexus AI Team",
  description: "Nexus AI Team — Multi-Agent Intelligence Platform",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Nexus",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
    shortcut: "/favicon.ico",
  },
  other: {
    "mobile-web-app-capable": "yes",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="tr"
      className={`dark ${inter.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        <meta charSet="UTF-8" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                  fetch('/sw.js', { cache: 'no-store' }).then((resp) => {
                    if (!resp.ok) return null;
                    return navigator.serviceWorker.register('/sw.js');
                  }).then((reg) => {
                    if (!reg) return;
                    // Check for updates every 60 seconds
                    setInterval(() => reg.update(), 60000);
                    // When a new SW is waiting, reload to activate
                    reg.addEventListener('updatefound', () => {
                      const newWorker = reg.installing;
                      if (!newWorker) return;
                      newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                          newWorker.postMessage({ type: 'SKIP_WAITING' });
                          window.location.reload();
                        }
                      });
                    });
                  }).catch(() => {});
                });
              }
            `,
          }}
        />
      </head>
      <body className="min-h-dvh bg-surface antialiased font-sans safe-bottom">
        <a href="#main-content" className="skip-link">
          İçeriğe atla
        </a>
        <ToastProvider>{children}</ToastProvider>
        <PWAInstallPrompt />
      </body>
    </html>
  );
}
